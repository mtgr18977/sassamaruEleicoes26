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
