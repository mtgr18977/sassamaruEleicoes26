// Monte Carlo da eleição presidencial (porta de montecarlo.py). Parâmetros vêm de parametros.json.
// swing uniforme + choque regional + ruído por UF; capital = estado + gap + choque comum + ruído.
(function (root) {
  const logit = (p) => Math.log(p / (1 - p));
  const inv = (y) => 1 / (1 + Math.exp(-y));

  function rng(seed) { // mulberry32 + Box-Muller
    let a = seed >>> 0;
    const u = () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    return () => Math.sqrt(-2 * Math.log(1 - u())) * Math.cos(2 * Math.PI * u());
  }

  const quantil = (v, q) => { const s = Float64Array.from(v).sort(); return s[Math.min(s.length - 1, Math.floor(q * s.length))]; };

  // par: parametros.json; turno: 1|2; opts: {p, sd, n, seed} (p/sd opcionais = pesquisas)
  function simular(par, turno, opts = {}) {
    const t = par["turno" + turno], mc = par.mc["turno" + turno];
    const p = opts.p ?? t.p_pesquisas, sd = opts.sd ?? t.sd_logit, N = opts.n ?? 20000;
    const z = rng(opts.seed ?? 2026), U = mc.unidades, k = U.length;
    const wTot = U.reduce((s, u) => s + u.validos, 0), w = U.map((u) => u.validos / wTot);
    const regs = [...new Set(U.map((u) => u.regiao))];
    const ps = U.map(() => new Float64Array(N)), pcs = U.map(() => new Float64Array(N)), nac = new Float64Array(N);
    const y = new Float64Array(k);
    for (let s = 0; s < N; s++) {
      const alvo = inv(logit(p) + sd * z());
      const reg = Object.fromEntries(regs.map((r) => [r, mc.sd_reg * z()]));
      for (let i = 0; i < k; i++) y[i] = logit(U[i].p2022) + reg[U[i].regiao] + mc.sd_uf * z();
      let lo = -3, hi = 3;
      for (let it = 0; it < 50; it++) {
        const m = (lo + hi) / 2; let tot = 0;
        for (let i = 0; i < k; i++) tot += w[i] * inv(y[i] + m);
        tot < alvo ? (lo = m) : (hi = m);
      }
      const m = (lo + hi) / 2, comum = mc.sd_com * z();
      nac[s] = alvo;
      for (let i = 0; i < k; i++) {
        const pe = inv(y[i] + m); ps[i][s] = pe;
        const g = U[i].gap;
        pcs[i][s] = g === null ? pe : inv(logit(pe) + g + comum + mc.sd_id * z());
      }
    }
    const resumo = (v, u, extra) => ({ uf: u.uf, ...extra, p5: quantil(v, 0.05), mediana: quantil(v, 0.5),
      p95: quantil(v, 0.95), pvit: v.reduce((s, x) => s + (x > 0.5), 0) / N });
    return {
      p_nac_gt50: nac.reduce((s, x) => s + (x > 0.5), 0) / N,
      margem_mediana_pp: 100 * (2 * quantil(nac, 0.5) - 1),
      ufs: U.map((u, i) => resumo(ps[i], u, { p2022: u.p2022 })),
      capitais: U.filter((u) => u.capital).map((u) => resumo(pcs[U.indexOf(u)], u, { capital: u.capital, p2022: u.cap2022 })),
    };
  }

  const api = { simular };
  if (typeof module !== "undefined") module.exports = api; else root.EleicoesModel = api;
})(this);
