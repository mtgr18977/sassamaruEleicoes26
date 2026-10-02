// Agregador de pesquisas (index.html e rs.html). Dados de agregador.py em D.agg; usa chart(), eixo(), seg(), tabela(), f1 e state de site.js.
const AGG_FORMAS = { Datafolha:"circle", Quaest:"triangle", AtlasIntel:"rect", RealTimeBigData:"rectRot", ParanaPesquisas:"star", Neokemp:"crossRot" };
const AGG_SVG = { circle:'<circle cx="6" cy="6" r="4"/>', triangle:'<path d="M6 1.5 11 10.5H1Z"/>', rect:'<rect x="2" y="2" width="8" height="8"/>', rectRot:'<path d="M6 1 11 6 6 11 1 6Z"/>',
  star:'<path d="M6 1l1.4 3.4 3.6.3-2.7 2.4.8 3.5L6 8.7 2.9 10.6l.8-3.5L1 4.7l3.6-.3Z"/>', crossRot:'<path d="M2 2l8 8M10 2l-8 8"/>' };
const AGG_NOME = { RealTimeBigData:"Real Time Big Data", ParanaPesquisas:"Paraná Pesquisas" };
const aggData = (iso) => Date.parse(iso + "T12:00:00");
const aggBR = (ms) => new Date(ms).toLocaleDateString("pt-BR", { day:"2-digit", month:"short" });
const aggCor = (c, a) => { const m = c.match(/^#([0-9a-f]{6})$/i); return m ? c + Math.round(a * 255).toString(16).padStart(2, "0") : c; };

const fimLinha = { id:"fimLinha", afterDatasetsDraw(c, _, o) {   // valor atual no fim de cada linha (afasta rótulos que se sobrepõem)
  if (!o || !o.on) return; const ctx = c.ctx; ctx.save(); ctx.font = "700 12px system-ui"; ctx.textBaseline = "middle";
  const L = []; c.data.datasets.forEach((ds, i) => { if (!ds.fim) return; const pt = c.getDatasetMeta(i).data.slice(-1)[0]; if (pt) L.push({ x:pt.x, y:pt.y, t:f1(ds.data.slice(-1)[0].y) + "%", cor:ds.borderColor }); });
  L.sort((a, b) => a.y - b.y); for (let k = 1; k < L.length; k++) L[k].y = Math.max(L[k].y, L[k - 1].y + 14);
  L.forEach(l => { ctx.fillStyle = l.cor; ctx.fillText(l.t, l.x + 7, l.y); });
  ctx.restore(); } };
Chart.register(fimLinha);

function agregador() {
  const A = D.agg, T = A.turnos[state.aggT], modo = state.aggAj ? "aj" : "bruta", datas = A.datas.map(aggData);
  const insts = [...new Set(T.series.flatMap(s => s.pontos.map(p => p.inst)))];
  // ---- cartões: média atual, variação em 14 dias, faixa de 90% ----
  $("aggKpis").innerHTML = T.series.map(s => { const m = s[modo].m, k = m.length - 1, dl = m[k] - m[Math.max(0, k - 14)], cls = Math.abs(dl) < 0.3 ? "eq" : dl > 0 ? "up" : "dn";
    return `<div class="agg-k" style="--c:${css(s.cor)}"><div class="nome"><i></i>${s.nome}</div><b>${f1(m[k])}%</b>
      <span class="dl ${cls}">${Math.abs(dl) < 0.3 ? "● estável" : (dl > 0 ? "▲ +" : "▼ −") + f1(Math.abs(dl)) + " p.p."} <small>em 14 dias</small></span>
      <small>faixa de 90%: ${f1(s[modo].lo[k])}–${f1(s[modo].hi[k])}</small></div>`; }).join("");
  // ---- gráfico: faixa + linha + pontos por instituto ----
  const ds = [];
  T.series.forEach(s => { const cor = css(s.cor), a = s[modo], xy = (v) => v.map((y, i) => ({ x:datas[i], y }));
    ds.push({ label:s.nome + " (faixa)", data:xy(a.hi), borderWidth:0, pointRadius:0, fill:"+1", backgroundColor:aggCor(cor, .16), order:3, aux:true, hover:false });
    ds.push({ label:s.nome + " (faixa inf.)", data:xy(a.lo), borderWidth:0, pointRadius:0, fill:false, order:3, aux:true, hover:false });
    ds.push({ label:s.nome, data:xy(a.m), borderColor:cor, backgroundColor:cor, borderWidth:3, pointRadius:0, pointHoverRadius:4, tension:.25, order:1, fim:true });
    ds.push({ type:"scatter", label:s.nome + " (pesquisas)", data:s.pontos.map(p => ({ x:aggData(p.x), y:p.y, p })), showLine:false, order:2, aux:true, pointBackgroundColor:aggCor(cor, .35), pointBorderColor:cor, pointBorderWidth:1.3,
      pointStyle:s.pontos.map(p => AGG_FORMAS[p.inst] || "circle"), pointRadius:s.pontos.map(p => 3 + 3 * Math.sqrt(p.n / 2000)) }); });
  if (T.ref != null) ds.push({ label:"ref", data:[{ x:datas[0], y:T.ref }, { x:datas[datas.length - 1], y:T.ref }], borderColor:css("--muted"), borderDash:[3, 4], borderWidth:1, pointRadius:0, aux:true, order:4 });
  chart("cAgg", { type:"line", data:{ datasets:ds }, options:{ parsing:false, layout:{ padding:{ right:58, top:6 } }, interaction:{ mode:"nearest", axis:"x", intersect:false },
    scales:{ x:{ type:"linear", min:datas[0], max:datas[datas.length - 1], ...eixo({ grid:{ display:false } }), ticks:{ color:css("--ink2"), maxTicksLimit:7, callback:(v) => aggBR(v) } },
      y:eixo({ min:T.ymin, max:T.ymax, ticks:{ color:css("--ink2"), callback:(v) => v + "%" } }) },
    plugins:{ fimLinha:{ on:true }, legend:{ position:"bottom", labels:{ color:css("--ink2"), usePointStyle:true, filter:(l, d) => !d.datasets[l.datasetIndex].aux } },
      tooltip:{ filter:(i) => i.dataset.hover !== false && (i.dataset.type !== "scatter" || i.raw.p), callbacks:{ title:(i) => aggBR(i[0].parsed.x),
        label:(i) => i.raw && i.raw.p ? `${i.dataset.label.replace(" (pesquisas)", "")} · ${AGG_NOME[i.raw.p.inst] || i.raw.p.inst}: ${f1(i.raw.p.y)}% (campo até ${i.raw.p.campo.split("-").reverse().join("/")}, n=${i.raw.p.n})` : i.dataset.aux ? null : `${i.dataset.label}: ${f1(i.parsed.y)}%` } } } } });
  $("aggLeg").innerHTML = "<b>Pontos:</b> " + insts.map(i => `<span><svg viewBox="0 0 12 12">${AGG_SVG[AGG_FORMAS[i] || "circle"]}</svg>${AGG_NOME[i] || i}</span>`).join("") + "<span>tamanho = amostra</span>";
  // ---- tabelas ----
  const semanal = A.datas.map((d, i) => i).filter(i => (A.datas.length - 1 - i) % 7 === 0);
  tabela("tAggTend", ["Data", ...T.series.map(s => s.nome + " %"), ...T.series.map(s => s.nome.split(" ")[0] + " (90%)")],
    semanal.slice().reverse().map(i => [A.datas[i].split("-").reverse().join("/"), ...T.series.map(s => s[modo].m[i]), ...T.series.map(s => `${f1(s[modo].lo[i])}–${f1(s[modo].hi[i])}`)]));
  const vies = insts.map(i => [AGG_NOME[i] || i, ...T.series.map(s => s.vies[i] ?? null)]);
  $("tAggVies").innerHTML = ""; tabela("tAggVies", ["Instituto (viés estimado, p.p.)", ...T.series.map(s => s.nome)], vies);
  const linhas = {}; T.series.forEach(s => s.pontos.forEach(p => { const k = p.inst + p.x; (linhas[k] = linhas[k] || [AGG_NOME[p.inst] || p.inst, p.campo.split("-").reverse().join("/"), p.n, ...T.series.map(() => null)])[3 + T.series.indexOf(s)] = p.y; }));
  tabela("tAggPesq", ["Instituto", "Campo até", "Amostra", ...T.series.map(s => s.nome + " %")], Object.values(linhas).sort((a, b) => b[1].split("/").reverse().join().localeCompare(a[1].split("/").reverse().join())));
  $("aggNota").innerHTML = `<b>Como é calculado:</b> média móvel com núcleo gaussiano (desvio de ~9 dias), peso pela amostra e pela proximidade da data. ${state.aggAj ? "O <b>viés de instituto</b> é estimado como a distância média de cada instituto à tendência e removido (encolhido para zero quando há poucas pesquisas; o nível geral é a média dos institutos)." : "Sem ajuste de instituto: cada pesquisa entra como divulgada."}
    A faixa de 90% soma o erro amostral (com efeito de desenho 1,5), um ruído residual de 1,5 p.p. entre pesquisas e uma incerteza que cresce com os dias sem pesquisa; os dois últimos números são <b>assumidos</b>, não medidos. ${A.nota}`;
}
function aggLigar() {
  seg($("segAggT"), "aggT", agregador);
  $("aggAj").onchange = (e) => { state.aggAj = e.target.checked; agregador(); };
}
