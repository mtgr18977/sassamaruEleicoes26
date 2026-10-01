// Governo do RS 2026 (porta de rs_modelo.py): chances de ser eleito e distribuição regional.
// par: {mu:[ln b/z, ln s/z], cov:[[..],[..]], rbar, pares:{ZB,ZS,BS:{mu,sd}}}; índices 0=Zucco(D) 1=Brizola(E) 2=Souza(C)
(function (root) {
  const EM = typeof module !== "undefined" ? require("./eleicoes-model.js") : root.EleicoesModel;
  const logit = (p) => Math.log(p / (1 - p)), inv = (y) => 1 / (1 + Math.exp(-y));
  const chol = (c) => { const a = Math.sqrt(c[0][0]), b = c[0][1] / a; return [[a, 0], [b, Math.sqrt(c[1][1] - b * b)]]; };
  const quant = (v, q) => EM.quantil(v, q);

  function chances(par, o = {}) {
    const N = o.n ?? 20000, rho = o.rho ?? 0.5, z = EM.rng(o.seed ?? 1), L = chol(par.cov), c = par.cov;
    const sdp = { ZB: Math.sqrt(c[0][0]), ZS: Math.sqrt(c[1][1]), BS: Math.sqrt(c[0][0] + c[1][1] - 2 * c[0][1]) };
    const eleito = [0, 0, 0], v1t = [0, 0, 0], pf = { ZB: 0, ZS: 0, BS: 0 };
    let seg = 0;
    for (let t = 0; t < N; t++) {
      const n1 = z(), n2 = z(), d0 = L[0][0] * n1, d1 = L[1][0] * n1 + L[1][1] * n2;
      const e = [1, Math.exp(par.mu[0] + d0), Math.exp(par.mu[1] + d1)], tot = e[0] + e[1] + e[2];
      const sh = e.map((x) => (x / tot) * (1 - par.rbar)), ord = [0, 1, 2].sort((a, b) => sh[b] - sh[a]);
      if (sh[ord[0]] > 0.5) { eleito[ord[0]]++; v1t[ord[0]]++; z(); continue; }
      seg++;
      const [i, j] = [ord[0], ord[1]].sort((a, b) => a - b), eps = z();
      const nome = i === 0 && j === 1 ? "ZB" : i === 0 ? "ZS" : "BS", dev = { ZB: -d0, ZS: -d1, BS: d0 - d1 }[nome];
      const p = par.pares[nome], tt = p.mu + p.sd * (rho * (dev / sdp[nome]) + Math.sqrt(1 - rho * rho) * eps);
      pf[nome]++; eleito[tt > 0 ? i : j]++;
    }
    return { eleito: eleito.map((x) => x / N), vence_1t: v1t.map((x) => x / N), segundo_turno: seg / N, par_final: { ZB: pf.ZB / N, ZS: pf.ZS / N, BS: pf.BS / N } };
  }

  // u: [{unidade_nome,E,C,D,validos}]
  function regioes(par, u, sigma, o = {}) {
    const N = o.n ?? 4000, rho = o.rho ?? 0.5, z = EM.rng(o.seed ?? 2), L = chol(par.cov), k = u.length;
    const tot = u.reduce((a, x) => a + x.validos, 0), w = u.map((x) => x.validos / tot);
    const lE = u.map((x) => Math.log(x.E / x.D)), lC = u.map((x) => Math.log(x.C / x.D));
    const D = u.map(() => new Float32Array(N)), E = u.map(() => new Float32Array(N)), C = u.map(() => new Float32Array(N)), Q = u.map(() => new Float32Array(N));
    const aE = new Float64Array(k), aC = new Float64Array(k), d = new Float64Array(k), e_ = new Float64Array(k), c_ = new Float64Array(k), q = new Float64Array(k);
    for (let t = 0; t < N; t++) {
      const n1 = z(), n2 = z(), d0 = L[0][0] * n1, d1 = L[1][0] * n1 + L[1][1] * n2;
      const e = [1, Math.exp(par.mu[0] + d0), Math.exp(par.mu[1] + d1)], s = e[0] + e[1] + e[2];
      const alvo = [(e[0] / s) * (1 - par.rbar), (e[1] / s) * (1 - par.rbar), (e[2] / s) * (1 - par.rbar) + par.rbar];
      for (let i = 0; i < k; i++) { aE[i] = lE[i] + sigma * z(); aC[i] = lC[i] + sigma * z(); }
      let dE = 0, dC = 0;
      for (let it = 0; it < 60; it++) {
        let mD = 0, mE = 0, mC = 0;
        for (let i = 0; i < k; i++) { const ee = Math.exp(aE[i] + dE), cc = Math.exp(aC[i] + dC), den = 1 + ee + cc; d[i] = 1 / den; e_[i] = ee / den; c_[i] = cc / den; mD += w[i] * d[i]; mE += w[i] * e_[i]; mC += w[i] * c_[i]; }
        dE += Math.log(alvo[1] / mE) - Math.log(alvo[0] / mD); dC += Math.log(alvo[2] / mC) - Math.log(alvo[0] / mD);
      }
      const p = par.pares.ZB, sd = Math.sqrt(par.cov[0][0]), eps = z();
      const p2 = inv(p.mu + p.sd * (rho * (-d0 / sd) + Math.sqrt(1 - rho * rho) * eps));
      let om = 0; for (let i = 0; i < k; i++) { q[i] = d[i] / (d[i] + e_[i]); om += w[i] * (d[i] + e_[i]); }
      let lo = -3, hi = 3;
      for (let it = 0; it < 40; it++) { const m = (lo + hi) / 2; let a = 0; for (let i = 0; i < k; i++) a += (w[i] * (d[i] + e_[i]) / om) * inv(logit(q[i]) + m); a < p2 ? (lo = m) : (hi = m); }
      const m = (lo + hi) / 2;
      for (let i = 0; i < k; i++) { D[i][t] = d[i]; E[i][t] = e_[i]; C[i][t] = c_[i]; Q[i][t] = inv(logit(q[i]) + m); }
    }
    const cont = (v, f) => { let a = 0; for (let t = 0; t < N; t++) a += f(v[t]); return a / N; };
    return u.map((x, i) => { const marg = Float32Array.from(D[i], (dv, t) => dv - E[i][t]);
      return { unidade: x.unidade_nome, zucco: 100 * quant(D[i], 0.5), brizola: 100 * quant(E[i], 0.5), centro: 100 * quant(C[i], 0.5), margem_zb: 100 * quant(marg, 0.5), margem_p5: 100 * quant(marg, 0.05), margem_p95: 100 * quant(marg, 0.95),
        p_zucco_a_frente_1t: 100 * cont(marg, (m) => m > 0), zb2t: 100 * quant(Q[i], 0.5), zb2t_p5: 100 * quant(Q[i], 0.05), zb2t_p95: 100 * quant(Q[i], 0.95), p_zucco_vence_2t: 100 * cont(Q[i], (m) => m > 0.5) }; });
  }
  const api = { chances, regioes };
  if (typeof module !== "undefined") module.exports = api; else root.RSModel = api;
})(this);
