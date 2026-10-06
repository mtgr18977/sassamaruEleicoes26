// Mapa de calor por estado (mesma grade e mesma escala do dashboard principal). valores: { UF: p.p. | null }.
// Positivo = vermelho (Lula na frente / ganho de Lula); com invert, positivo = azul. Cinza = sem número com fonte.
const TILES = { RR:[0,2],AP:[0,4], AC:[1,0],AM:[1,1],PA:[1,3],MA:[1,4],CE:[1,5],RN:[1,6], RO:[2,1],MT:[2,2],TO:[2,3],PI:[2,4],PB:[2,6],
  MS:[3,2],GO:[3,3],DF:[3,4],BA:[3,5],PE:[3,6], SP:[4,3],MG:[4,4],ES:[4,5],AL:[4,6], PR:[5,3],RJ:[5,4],SE:[5,6], SC:[6,3], RS:[7,3] };
function mapaTiles(id, valores, { escala = 40, invert = false, destaque = [] } = {}) {
  const mix = (a, b, w) => a.map((x, i) => Math.round(x + (b[i] - x) * w)), rgb = (h) => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const [az, meio, vm] = ["--div-blue", "--div-mid", "--div-red"].map(v => rgb(css(v)));
  $(id).innerHTML = Object.entries(TILES).map(([uf, [row, col]]) => {
    const v = valores[uf], pos = `grid-row:${row + 1};grid-column:${col + 1}`;
    if (v == null) return `<div class="tl" style="${pos};background:var(--grid);color:var(--muted)" title="${uf}: sem número com fonte"><b>${uf}</b>–</div>`;
    const c = mix(meio, (invert ? v > 0 : v < 0) ? az : vm, Math.min(1, Math.abs(v) / escala)), lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2];
    return `<div class="tl" style="${pos};background:rgb(${c});color:${lum > 140 ? "#0b0b0b" : "#fff"}${destaque.includes(uf) ? ";outline:2px solid var(--ink);outline-offset:-2px" : ""}" title="${uf}: ${v > 0 ? "+" : ""}${f1(v)} p.p."><b>${uf}</b>${v > 0 ? "+" : ""}${v.toFixed(0)}</div>`;
  }).join("");
}
