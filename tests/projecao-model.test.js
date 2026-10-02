// Compara o simulador JS do 1º turno com a projeção em Python (modelos/projecao-1turno-uf-pesquisas.csv).
// Entrada: parâmetros embutidos em index.html. Rodar: node tests/projecao-model.test.js
const fs = require("fs"), assert = require("assert");
const { simular } = require("../modelos/projecao-model.js");
const html = fs.readFileSync("index.html", "utf8");
const par = JSON.parse(html.match(/const D = (.*?);\nconst ANOS/s)[1]).projmodel;
const r = simular(par, { s: par.s, q: par.q, n: 20000 });
const ref = Object.fromEntries(fs.readFileSync("modelos/projecao-1turno-uf-pesquisas.csv", "utf8").trim().split("\n").slice(1).map((l) => l.split(",")).map((c) => [c[0], c]));
for (const u of r.ufs) {
  const m = parseFloat(ref[u.uf][8]);                       // coluna "margem"
  assert(Math.abs(u.margem - m) < 1.5, `${u.uf}: JS margem ${u.margem.toFixed(1)} vs Python ${m}`);
}
const pj = JSON.parse(fs.readFileSync("modelos/projecao-1turno.json", "utf8")).pesquisas;
assert(Math.abs(r.L[1] - pj.L[1]) < 0.6 && Math.abs(r.F[1] - pj.F[1]) < 0.6, `nacional L=${r.L[1]} F=${r.F[1]} vs Python L=${pj.L[1]} F=${pj.F[1]}`);
console.log(`OK  Lula ${r.L[1].toFixed(1)} Flávio ${r.F[1].toFixed(1)} demais ${r.O[1].toFixed(1)} | P(Lula à frente) ${(100 * r.p_lula_a_frente).toFixed(1)}% | P(2º turno) ${(100 * r.p_2turno).toFixed(1)}%`);
let t = Date.now(); simular(par, { s: par.s, q: par.q, n: 5000 }); console.log("5000 sims:", Date.now() - t, "ms");
