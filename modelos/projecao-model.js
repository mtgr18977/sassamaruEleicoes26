// Projeção do 1º turno (porta de projecao.py): Lula × Flávio × demais, base 2022 por UF.
// Dois eixos em logit — s = Lula/(Lula+Flávio), q = (Lula+Flávio)/válidos — cada um com swing uniforme
// + choque regional + ruído por UF. Totais nacionais (s, q) são entradas; calibração por bisseção.
(function (root) {
  const EM = typeof module !== "undefined" ? require("./eleicoes-model.js") : root.EleicoesModel;
  const logit = (p) => Math.log(p / (1 - p)), inv = (y) => 1 / (1 + Math.exp(-y));

  // par: {ufs:[{uf,regiao,s0,q0,w}], ruido:{s:[reg,uf], q:[reg,uf]}, sd_s, sd_q}; o: {s, q, n, seed}
  function simular(par, o) {
    const U = par.ufs, k = U.length, N = o.n ?? 5000, z = EM.rng(o.seed ?? 2026);
    const wt = U.reduce((a, u) => a + u.w, 0), w = U.map((u) => u.w / wt);
    const regs = [...new Set(U.map((u) => u.regiao))], ri = U.map((u) => regs.indexOf(u.regiao));
    const L = U.map(() => new Float32Array(N)), F = U.map(() => new Float32Array(N)), M = U.map(() => new Float32Array(N));
    const nL = new Float64Array(N), nF = new Float64Array(N), nO = new Float64Array(N);
    const yq = new Float64Array(k), ys = new Float64Array(k), qi = new Float64Array(k);
    const ruido = (y, base, sd) => { const r = regs.map(() => sd[0] * z()); for (let i = 0; i < k; i++) y[i] = logit(base[i]) + r[ri[i]] + sd[1] * z(); };
    const q0 = U.map((u) => u.q0), s0 = U.map((u) => u.s0);
    for (let t = 0; t < N; t++) {
      const sn = inv(logit(o.s) + par.sd_s * z()), qn = inv(logit(o.q) + par.sd_q * z());
      ruido(yq, q0, par.ruido.q); ruido(ys, s0, par.ruido.s);
      let lo = -4, hi = 4;
      for (let it = 0; it < 40; it++) { const m = (lo + hi) / 2; let a = 0; for (let i = 0; i < k; i++) a += w[i] * inv(yq[i] + m); a < qn ? (lo = m) : (hi = m); }
      const mq = (lo + hi) / 2; for (let i = 0; i < k; i++) qi[i] = inv(yq[i] + mq);
      let qw = 0; for (let i = 0; i < k; i++) qw += qi[i] * w[i];
      lo = -4; hi = 4;
      for (let it = 0; it < 40; it++) { const m = (lo + hi) / 2; let a = 0; for (let i = 0; i < k; i++) a += qi[i] * inv(ys[i] + m) * w[i]; a / qw < sn ? (lo = m) : (hi = m); }
      const ms = (lo + hi) / 2; let l = 0, f = 0;
      for (let i = 0; i < k; i++) { const s = inv(ys[i] + ms); L[i][t] = qi[i] * s; F[i][t] = qi[i] * (1 - s); M[i][t] = L[i][t] - F[i][t]; l += w[i] * L[i][t]; f += w[i] * F[i][t]; }
      nL[t] = l; nF[t] = f; nO[t] = 1 - l - f;
    }
    const Q = EM.quantil, med = (v) => 100 * Q(v, 0.5), cont = (v, f) => v.reduce((a, x) => a + f(x), 0) / N;
    let ufsAFrente = 0;
    const ufs = U.map((u, i) => { const pf = cont(M[i], (x) => x > 0); ufsAFrente += pf;
      return { uf: u.uf, lula: med(L[i]), flavio: med(F[i]), outros: 100 - med(L[i]) - med(F[i]), margem: med(M[i]), m5: 100 * Q(M[i], 0.05), m95: 100 * Q(M[i], 0.95), pfrente: 100 * pf }; });
    const iv = (v) => [100 * Q(v, 0.05), med(v), 100 * Q(v, 0.95)], d = Float64Array.from(nL, (x, t) => x - nF[t]);
    return { L: iv(nL), F: iv(nF), O: iv(nO), margem: iv(d), p_lula_a_frente: cont(d, (x) => x > 0), p_2turno: cont(nL.map((x, t) => Math.max(x, nF[t])), (x) => x <= 0.5),
      p_lf_2turno: cont(nL.map((x, t) => Math.min(x, nF[t]) - nO[t]), (x) => x > 0), /* cota: todos os demais como UM candidato */ ufs_lula_a_frente: ufsAFrente, ufs };
  }
  // Chances nacionais de ser eleito (1º turno + 2º turno), simulação conjunta dos dois turnos.
  // o: {s, q, sd_s, sd_q, s2, sd2, rho, n, seed}. rho = correlação (ASSUMIDA, não medida) entre os erros de s (1º turno) e s2 (2º turno).
  function chances(o) {
    const N = o.n ?? 20000, z = EM.rng(o.seed ?? 2026), rho = o.rho ?? 0.5;
    let lOut = 0, fOut = 0, lWin = 0, fWin = 0, run = 0, outro = 0;
    for (let t = 0; t < N; t++) {
      const zc = z(), e1 = zc, e2 = rho * zc + Math.sqrt(1 - rho * rho) * z();
      const s1 = inv(logit(o.s) + o.sd_s * e1), q = inv(logit(o.q) + o.sd_q * z()), s2 = inv(logit(o.s2) + o.sd2 * e2);
      const L = q * s1, F = q * (1 - s1);
      if (L > 0.5) { lOut++; lWin++; } else if (F > 0.5) { fOut++; fWin++; }
      else { run++; if (Math.min(L, F) <= 1 - q) outro++; else if (s2 > 0.5) lWin++; else fWin++; }
    }
    return { lula: lWin / N, flavio: fWin / N, lula_1t: lOut / N, flavio_1t: fOut / N, lula_2t: (lWin - lOut) / N, flavio_2t: (fWin - fOut) / N,
             segundo_turno: run / N, outro: outro / N };
  }
  // Chance de Lula vencer o 2º turno (popular, já que o 1º foi realizado): P(s2 > 50%) com logit(s2) ~ N(logit(s2̂), sd2²).
  // o: {s2, sd2} (s2 = Lula/(Lula+Flávio); sd2 já inclui tendência, viés histórico e o piso assumido). Fórmula fechada (Φ via erfc de Numerical Recipes).
  const erfc = (x) => { const z = Math.abs(x), t = 1 / (1 + 0.5 * z),
    r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277))))))))); return x >= 0 ? r : 2 - r; };
  const Phi = (x) => 0.5 * erfc(-x / Math.SQRT2);
  function chances2t(o) { const lula = Phi(logit(o.s2) / o.sd2); return { lula, flavio: 1 - lula }; }
  const api = { simular, chances, chances2t };
  if (typeof module !== "undefined") module.exports = api; else root.ProjecaoModel = api;
})(this);
