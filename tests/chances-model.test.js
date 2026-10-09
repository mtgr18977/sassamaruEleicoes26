// Chance de Lula vencer o 2º turno (fórmula fechada): invariantes e referência independente (numpy, 2 milhões de sorteios).
// Rodar: node tests/chances-model.test.js
const fs = require("fs"), assert = require("assert");
const { chances2t } = require("../modelos/projecao-model.js");
const D = JSON.parse(fs.readFileSync("index.html", "utf8").match(/const D = (.*?);\nconst ANOS/s)[1]);
const t2 = D.modelo.turno2, v = D.projmodel.vies_medio[2];
const r = chances2t({ s2: t2.p_pesquisas, sd2: t2.sd_logit });
assert(Math.abs(r.lula + r.flavio - 1) < 1e-12, "as chances devem somar 1");
assert(Math.abs(chances2t({ s2: 0.5, sd2: 0.1 }).lula - 0.5) < 1e-6, "s2 = 50% deve dar 50%");
assert(Math.abs(chances2t({ s2: 0.4814, sd2: 0.1001 }).lula - 0.2286) < 0.002, "referência numpy: Φ(logit(0,4814)/0,1001) = 0,2286");
assert(chances2t({ s2: t2.p_pesquisas + 0.01, sd2: t2.sd_logit }).lula > r.lula, "mais Lula no 2º turno deve aumentar a chance");
assert(chances2t({ s2: t2.p_pesquisas - v / 100, sd2: t2.sd_logit }).lula < r.lula, "descontar o viés a favor do PT deve reduzir a chance de Lula");
assert(r.lula > 0.1 && r.lula < 0.4, `Lula ${r.lula}: fora da faixa esperada para as pesquisas de 9/10`);
console.log(`OK  Lula vence o 2º turno ${(100 * r.lula).toFixed(1)}% | Flávio ${(100 * r.flavio).toFixed(1)}% | s2 ${(100 * t2.p_pesquisas).toFixed(1)}% sd ${t2.sd_logit}`);
