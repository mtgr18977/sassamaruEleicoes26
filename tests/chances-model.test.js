// Chances de ser eleito: invariantes e faixas de referência (calculadas em Python com os mesmos parâmetros, rho 0..1).
// Rodar: node tests/chances-model.test.js
const fs = require("fs"), assert = require("assert");
const { chances } = require("../modelos/projecao-model.js");
const D = JSON.parse(fs.readFileSync("index.html", "utf8").match(/const D = (.*?);\nconst ANOS/s)[1]);
const m = D.projmodel, t2 = D.modelo.turno2;
const base = { s: m.s, q: m.q, sd_s: m.sd_s, sd_q: m.sd_q, s2: t2.p_pesquisas, sd2: t2.sd_logit, n: 40000 };
const r = chances({ ...base, rho: 0.5 });
assert(Math.abs(r.lula + r.flavio + r.outro - 1) < 1e-9, "probabilidades de vitória devem somar 1");
assert(Math.abs(r.lula_1t + r.flavio_1t + r.segundo_turno - 1) < 1e-9, "1T + 2º turno devem somar 1");
assert(Math.abs(r.lula_1t + r.lula_2t - r.lula) < 1e-9);
assert(r.flavio_1t < 0.03 && r.lula_1t > 0.03 && r.lula_1t < 0.15, `1º turno: Lula ${r.lula_1t}, Flávio ${r.flavio_1t}`);
assert(r.segundo_turno > 0.85 && r.outro < 0.005, `2º turno ${r.segundo_turno}, outro cenário ${r.outro}`);
const lo = chances({ ...base, rho: 0 }).lula, hi = chances({ ...base, rho: 1 }).lula;
assert(Math.abs(r.lula - 0.43) < 0.05 && Math.abs(lo - 0.455) < 0.05 && Math.abs(hi - 0.414) < 0.05, `Lula eleito: ρ=0 ${lo}, ρ=.5 ${r.lula}, ρ=1 ${hi}`);
assert(chances({ ...base, s2: base.s2 + 0.02, rho: 0.5 }).lula > r.lula, "mais Lula no 2º turno deve aumentar a chance");
console.log(`OK  Lula ${(100 * r.lula).toFixed(1)}% (1T ${(100 * r.lula_1t).toFixed(1)}%) | Flávio ${(100 * r.flavio).toFixed(1)}% (1T ${(100 * r.flavio_1t).toFixed(1)}%) | faixa Lula ${(100 * hi).toFixed(0)}–${(100 * lo).toFixed(0)}%`);
