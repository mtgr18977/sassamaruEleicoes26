// Compara o JS com a referência em Python (modelos/rs-parametros.json, gerado por rs_modelo.py). Rodar: node tests/rs-model.test.js
const fs = require("fs"), assert = require("assert");
const { chances, regioes } = require("../modelos/rs-model.js");
const J = JSON.parse(fs.readFileSync("modelos/rs-parametros.json"));
const c = chances(J.par, { n: 60000 }), ref = J.ref.chances;
for (let i = 0; i < 3; i++) {
  assert(Math.abs(c.eleito[i] - ref.eleito[i]) < 0.015, `eleito[${i}] JS ${c.eleito[i]} vs Python ${ref.eleito[i]}`);
  assert(Math.abs(c.vence_1t[i] - ref.vence_1t[i]) < 0.01, `vence_1t[${i}]`);
}
assert(Math.abs(c.eleito.reduce((a, b) => a + b, 0) - 1) < 1e-9, "probabilidades de eleito somam 1");
assert(Math.abs(c.segundo_turno - ref.segundo_turno) < 0.01);
const r = regioes(J.par, J.unidades, J.sigma, { n: 4000 });
J.ref.regioes.forEach((x, i) => {
  for (const k of ["zucco", "brizola", "centro", "zb2t"]) assert(Math.abs(r[i][k] - x[k]) < 1.5, `${x.unidade} ${k}: JS ${r[i][k].toFixed(1)} vs Python ${x[k]}`);
});
console.log(`OK  Zucco ${(100 * c.eleito[0]).toFixed(1)}% · Brizola ${(100 * c.eleito[1]).toFixed(1)}% · Souza ${(100 * c.eleito[2]).toFixed(2)}% | 2º turno ${(100 * c.segundo_turno).toFixed(1)}%`);
let t = Date.now(); regioes(J.par, J.unidades, J.sigma, { n: 4000 }); console.log("regiões 4000 sims:", Date.now() - t, "ms");
