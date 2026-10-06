// Utilidades das páginas de análise (analise-*.html, segundo-turno.html). Usa site.js (css, f1, $, tabela, chart, eixo, tema) e o global D.
const state = {};
const pp = (x) => (x > 0 ? "+" : x < 0 ? "−" : "") + f1(Math.abs(x)), f2 = (x) => x.toFixed(2).replace(".", ","), pc = (x) => x.toLocaleString("pt-BR");
const mi = (x) => (x / 1e6).toFixed(2).replace(".", ","), dentro = (v, lo, hi) => v >= lo && v <= hi ? `<span class="ok">dentro</span>` : `<span class="ruim">fora</span>`;
const BNOME = { E: "Esquerda", C: "Centro", D: "Direita" }, BCOR = { E: "--pt", C: "--s7", D: "--anti" };
const cor = (v) => css(v);
// tabela() do site.js formata números com 1 casa decimal; inteiros (cadeiras) viram texto.
const tab = (id, cab, linhas) => tabela(id, cab, linhas.map(l => l.map(c => (typeof c === "number" && Number.isInteger(c) ? String(c) : c))));
