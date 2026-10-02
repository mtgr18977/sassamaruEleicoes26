// Utilidades compartilhadas pelas abas (index.html e rs.html). Usa os globais da página: state, tudo().
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const f1 = (x) => x == null ? "–" : x.toFixed(1).replace(".", ","), $ = (id) => document.getElementById(id);
let charts = {};

// ---------- utilidades ----------
function seg(el, key, redraw) {
  el.innerHTML = [1,2].map(t => `<button data-t="${t}" aria-pressed="${state[key]==t}">${t}º</button>`).join("");
  el.onclick = (e) => { const t = e.target.dataset.t; if (!t) return; state[key] = +t; seg(el, key, redraw); redraw(); };
}
function tabela(id, cab, linhas) {
  $(id).innerHTML = `<table class="t"><tr>${cab.map(c => `<th>${c}</th>`).join("")}</tr>` +
    linhas.map(l => `<tr>${l.map(c => `<td>${typeof c === "number" ? f1(c) : (c ?? "–")}</td>`).join("")}</tr>`).join("") + "</table>";
}
function chart(id, cfg) {
  if (charts[id]) charts[id].destroy();
  cfg.options = Object.assign({ responsive:true, maintainAspectRatio:false, animation:{duration:250} }, cfg.options);
  const o = cfg.options; o.plugins = Object.assign({ legend:{ position:"bottom", labels:{ color:css("--ink2"), boxWidth:12, boxHeight:12, usePointStyle:true } } }, o.plugins);
  charts[id] = new Chart($(id), cfg);
}
const eixo = (extra = {}) => ({ grid:{ color:css("--grid") }, border:{ display:false }, ticks:{ color:css("--ink2") }, ...extra });
const rotulos = { id:"rotulos", afterDatasetsDraw(c, _, o) {   // rótulos diretos só nos pontos plotados (≤ 12)
  if (!o || !o.on) return; const ctx = c.ctx; ctx.save(); ctx.font = "600 11px system-ui"; ctx.fillStyle = css("--ink"); ctx.textAlign = "center";
  c.data.datasets.forEach((ds, i) => { if (ds.aux || c.getDatasetMeta(i).hidden) return;
    c.getDatasetMeta(i).data.forEach((pt, k) => { const v = ds.data[k]; if (v == null) return; ctx.fillText(f1(v), pt.x, pt.y + (ds.rotPos === "baixo" ? 16 : -9)); }); });
  ctx.restore(); } };
Chart.register(rotulos);

// ---------- tema (auto / claro / escuro) ----------
const TEMAS = ["auto", "claro", "escuro"];
function temaAtual() { try { return localStorage.getItem("tema") || "auto"; } catch (e) { return "auto"; } }
function aplicarTema(tm) {
  const r = document.documentElement;
  if (tm === "claro") r.setAttribute("data-theme", "light"); else if (tm === "escuro") r.setAttribute("data-theme", "dark"); else r.removeAttribute("data-theme");
  const b = $("tema"); if (b) b.textContent = { auto: "◐ Tema: auto", claro: "☀ Tema: claro", escuro: "☾ Tema: escuro" }[tm];
}
let temaEscolhido = temaAtual();   // em memória: funciona mesmo se o localStorage estiver bloqueado
function alternarTema() { temaEscolhido = TEMAS[(TEMAS.indexOf(temaEscolhido) + 1) % TEMAS.length]; try { localStorage.setItem("tema", temaEscolhido); } catch (e) {} aplicarTema(temaEscolhido); tudo(); }

function nota(id, itens) { $(id).innerHTML = `<h4>Em resumo</h4><ul>${itens.map(i => `<li>${i}</li>`).join("")}</ul>`; }
const sg = (x) => (x > 0 ? "+" : "−") + f1(Math.abs(x));

// ---------- agregador de pesquisas (tendência + intervalo de 90% por candidato) ----------
// A = {series:{nome:[{data,m,lo,hi}]}, pontos:{nome:[{data,inst,v}]}}; cores = {nome: "--var"}
const dia = (s) => Date.parse(s) / 864e5, dm = (x) => { const d = new Date(x * 864e5); return String(d.getUTCDate()).padStart(2, "0") + "/" + String(d.getUTCMonth() + 1).padStart(2, "0"); };
function agregador(canvas, tab, A, cores, ymax) {
  const nomes = Object.keys(A.series), ds = [];
  nomes.forEach(n => {
    const c = css(cores[n]), s = A.series[n], xy = (k) => s.map(r => ({ x: dia(r.data), y: r[k] }));
    ds.push({ label: n + " (mín.)", data: xy("lo"), borderWidth: 0, pointRadius: 0, fill: false, aux: true, order: 3 });
    ds.push({ label: n + " (intervalo)", data: xy("hi"), borderWidth: 0, pointRadius: 0, backgroundColor: c + "30", fill: "-1", aux: true, order: 3 });
    ds.push({ label: n, data: xy("m"), borderColor: c, backgroundColor: c, borderWidth: 2.5, pointRadius: 0, tension: 0.25, order: 1 });
    ds.push({ label: n + " (pesquisas)", data: A.pontos[n].map(p => ({ x: dia(p.data), y: p.v, inst: p.inst })), type: "scatter", showLine: false, pointRadius: 3, pointHoverRadius: 5,
      borderColor: c, backgroundColor: c + "99", aux: true, order: 2 });
  });
  const x0 = dia(A.series[nomes[0]][0].data), x1 = dia(A.series[nomes[0]].at(-1).data);
  chart(canvas, { type: "line", data: { datasets: ds }, options: { parsing: false, interaction: { mode: "x", intersect: false },
    scales: { x: eixo({ type: "linear", min: x0, max: x1, grid: { display: false }, ticks: { color: css("--ink2"), maxTicksLimit: 8, callback: v => dm(v) } }),
      y: eixo({ min: 0, max: ymax, ticks: { color: css("--ink2"), callback: v => v + "%" } }) },
    plugins: { rotulos: { on: false }, legend: { position: "bottom", labels: { color: css("--ink2"), boxWidth: 18, boxHeight: 3, filter: l => !/\((mín\.|intervalo|pesquisas)\)$/.test(l.text) } },
      tooltip: { filter: i => !i.dataset.aux, callbacks: { title: i => dm(i[0].parsed.x) + "/2026",
        label: i => { const r = A.series[i.dataset.label].find(q => dia(q.data) === i.parsed.x); return r ? `${i.dataset.label}: ${f1(r.m)}% (${f1(r.lo)}–${f1(r.hi)})` : null; } } } } } });
  const u = nomes.map(n => { const r = A.series[n].at(-1); return [n, r.m, r.lo, r.hi, A.pontos[n].length]; });
  tabela(tab, ["Candidato", "Tendência %", "Mínimo 90% %", "Máximo 90% %", "Pesquisas"], u.map(l => [l[0], l[1], l[2], l[3], String(l[4])]));
}
