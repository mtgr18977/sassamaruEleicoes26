// Compara o JS com o Monte Carlo em Python (modelos/previsao-*.csv). Rodar: node tests/eleicoes-model.test.js
const fs = require("fs"), assert = require("assert");
const { simular } = require("../modelos/eleicoes-model.js");
const par = JSON.parse(fs.readFileSync("modelos/parametros.json"));
const csv = (f) => fs.readFileSync(f, "utf8").trim().split("\n").slice(1).map((l) => l.split(","));
for (const turno of [1, 2]) {
  const r = simular(par, turno, { n: 20000 });
  for (const [arq, lista, col] of [["uf", r.ufs, 0], ["capitais", r.capitais, 0]]) {
    const ref = Object.fromEntries(csv(`modelos/previsao-${arq}-turno${turno}.csv`).map((c) => [c[0], c]));
    const i = arq === "uf" ? 3 : 4; // coluna "mediana"
    for (const x of lista) {
      const d = Math.abs(100 * x.mediana - parseFloat(ref[x.uf][i]));
      assert(d < 1.0, `${arq} ${x.uf} turno ${turno}: JS ${100 * x.mediana} vs Python ${ref[x.uf][i]}`);
    }
  }
  console.log(`turno ${turno} OK  P(Lula>50%)=${(100 * r.p_nac_gt50).toFixed(1)}%`);
}
