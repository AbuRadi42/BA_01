/* ============================================================
   app.js — Morphological Efficiency Dashboard
   Reads JSON/JSONL logs from ../../logs/ and renders all charts.
   Uses D3 v7. No build step required — open index.html in browser.
   ============================================================ */

"use strict";

// ── Model registry ────────────────────────────────────────────────────────────
const MODELS = [
  { id: "en_base",  lang: "en", regime: "baseline", label: "en_base",  color: "#394195" },
  { id: "en_morph", lang: "en", regime: "morph",    label: "en_morph", color: "#a74d79" },
  { id: "ar_base",  lang: "ar", regime: "baseline", label: "ar_base",  color: "#59a150" },
  { id: "ar_morph", lang: "ar", regime: "morph",    label: "ar_morph", color: "#1d5619" },
  { id: "tr_base",  lang: "tr", regime: "baseline", label: "tr_base",  color: "#769bb9" },
  { id: "tr_morph", lang: "tr", regime: "morph",    label: "tr_morph", color: "#df3e29" },
];

const LANGS = ["en", "ar", "tr"];
const LANG_NAMES = { en: "English", ar: "Arabic", tr: "Turkish" };
const LOG_BASE = "../../logs";

// ── Data store ────────────────────────────────────────────────────────────────
const DATA = {
  timeseries: {},   // { modelId: [{step,tokens,loss,ppl,...}] }
  lm:         {},   // { modelId: {val_ppl, test_ppl, ...} }
  morph:      {},   // { modelId: {tokens_per_meaning_unit, agreement_accuracy, ...} }
  compute:    {},   // { modelId: {flops_per_token, inference_latency_ms, ...} }
  tasks:      {},   // { modelId: { taskName: {...} } }
};

// ── Fetch helpers ─────────────────────────────────────────────────────────────
async function fetchJSON(path) {
  try {
    const r = await fetch(path);
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

async function fetchJSONL(path) {
  try {
    const r = await fetch(path);
    if (!r.ok) return [];
    const text = await r.text();
    return text.trim().split("\n").filter(Boolean).map(l => JSON.parse(l));
  } catch { return []; }
}

// ── Load all data ─────────────────────────────────────────────────────────────
async function loadAll() {
  const promises = MODELS.map(async m => {
    const base = `${LOG_BASE}`;
    const [ts, lm, morph, compute] = await Promise.all([
      fetchJSONL(`${base}/training/${m.id}_timeseries.jsonl`),
      fetchJSON(`${base}/evaluation/${m.id}_lm.json`),
      fetchJSON(`${base}/evaluation/${m.id}_morph.json`),
      fetchJSON(`${base}/evaluation/${m.id}_compute.json`),
    ]);
    DATA.timeseries[m.id] = ts;
    DATA.lm[m.id]         = lm;
    DATA.morph[m.id]      = morph;
    DATA.compute[m.id]    = compute;

    // Downstream tasks
    DATA.tasks[m.id] = {};
    const taskNames = m.lang === "en" ? ["sentiment","qa"]
                    : m.lang === "ar" ? ["sentiment","qa"]
                    : ["classification","qa"];
    await Promise.all(taskNames.map(async t => {
      const d = await fetchJSON(`${base}/evaluation/${m.id}_task_${t}.json`);
      if (d) DATA.tasks[m.id][t] = d;
    }));
  });
  await Promise.all(promises);
}

// ── Tooltip ───────────────────────────────────────────────────────────────────
const tip = d3.select("#tooltip");
function showTip(html, event) {
  tip.html(html).style("opacity", 1)
     .style("left", (event.clientX + 14) + "px")
     .style("top",  (event.clientY - 28) + "px");
}
function hideTip() { tip.style("opacity", 0); }

// ── Nav dots ──────────────────────────────────────────────────────────────────
function buildNav() {
  const container = document.getElementById("slides-container");
  const slides = document.querySelectorAll(".slide");
  const nav    = document.getElementById("nav-dots");
  slides.forEach((s, i) => {
    const dot = document.createElement("div");
    dot.className = "dot" + (i === 0 ? " active" : "");
    dot.title = s.querySelector("h1,h2")?.textContent || `Slide ${i}`;
    dot.addEventListener("click", () => {
      container.scrollTo({ top: s.offsetTop, behavior: "smooth" });
    });
    nav.appendChild(dot);
  });
  const dots = nav.querySelectorAll(".dot");
  const obs  = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const idx = [...slides].indexOf(e.target);
        dots.forEach((d, i) => d.classList.toggle("active", i === idx));
      }
    });
  }, { root: container, threshold: 0.5 });
  slides.forEach(s => obs.observe(s));
}

// ── Fade-in on scroll ─────────────────────────────────────────────────────────
function initFadeIn() {
  const container = document.getElementById("slides-container");
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add("visible"); });
  }, { root: container, threshold: 0.15 });
  document.querySelectorAll(".fade-in").forEach(el => obs.observe(el));
}

// ── D3 helpers ────────────────────────────────────────────────────────────────
function svgOf(containerId, margin, fullW, fullH) {
  const el = document.getElementById(containerId);
  if (!el) return null;
  el.innerHTML = "";
  const w = fullW  - margin.left - margin.right;
  const h = fullH  - margin.top  - margin.bottom;
  const svg = d3.select(el).append("svg")
    .attr("width", "100%").attr("height", fullH)
    .attr("viewBox", `0 0 ${fullW} ${fullH}`)
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  return { svg, w, h };
}

function addGrid(svg, scale, dir, size) {
  const axis = dir === "y"
    ? d3.axisLeft(scale).tickSize(-size).tickFormat("")
    : d3.axisBottom(scale).tickSize(-size).tickFormat("");
  svg.append("g").attr("class","grid")
     .call(axis).select(".domain").remove();
}

// ── SLIDE 2 — Learning curves ─────────────────────────────────────────────────
let activeCurveLang = "en";

function drawLearningCurves(lang) {
  const margin = { top: 20, right: 20, bottom: 50, left: 55 };
  const fullW = 900, fullH = 360;
  const r = svgOf("learning-curve-chart", margin, fullW, fullH);
  if (!r) return;
  const { svg, w, h } = r;

  const langModels = MODELS.filter(m => m.lang === lang);
  const allSeries  = langModels.map(m => ({
    model: m,
    data:  (DATA.timeseries[m.id] || []).filter(d => d.loss != null),
  })).filter(s => s.data.length > 0);

  if (allSeries.length === 0) {
    svg.append("text").attr("x", w/2).attr("y", h/2)
       .attr("text-anchor","middle").attr("fill","#475569")
       .text("No training data yet — run train_lm.py to populate logs.");
    return;
  }

  const xMax = d3.max(allSeries, s => d3.max(s.data, d => d.tokens));
  const yMax = d3.max(allSeries, s => d3.max(s.data, d => d.loss));
  const yMin = d3.min(allSeries, s => d3.min(s.data, d => d.loss));

  const x = d3.scaleLinear().domain([0, xMax]).range([0, w]);
  const y = d3.scaleLinear().domain([yMin * 0.95, yMax * 1.02]).range([h, 0]);

  addGrid(svg, y, "y", w);

  svg.append("g").attr("class","axis").attr("transform",`translate(0,${h})`).call(
    d3.axisBottom(x).ticks(6).tickFormat(d => `${(d/1e9).toFixed(1)}B`));
  svg.append("g").attr("class","axis").call(d3.axisLeft(y).ticks(6));

  svg.append("text").attr("x", w/2).attr("y", h+40)
     .attr("text-anchor","middle").attr("fill","#64748b").attr("font-size",11)
     .text("Tokens processed");
  svg.append("text").attr("transform","rotate(-90)")
     .attr("x",-h/2).attr("y",-42).attr("text-anchor","middle")
     .attr("fill","#64748b").attr("font-size",11).text("Loss");

  const line = d3.line().x(d => x(d.tokens)).y(d => y(d.loss)).curve(d3.curveMonotoneX);

  allSeries.forEach(({ model, data }) => {
    const path = svg.append("path").datum(data)
      .attr("fill","none").attr("stroke", model.color)
      .attr("stroke-width", 2).attr("d", line);
    const len = path.node().getTotalLength();
    path.attr("stroke-dasharray", len).attr("stroke-dashoffset", len)
      .transition().duration(1200).ease(d3.easeLinear).attr("stroke-dashoffset", 0);

    // Hover dots
    svg.selectAll(`.dot-${model.id}`).data(data.filter((_,i) => i % 5 === 0))
      .enter().append("circle")
      .attr("cx", d => x(d.tokens)).attr("cy", d => y(d.loss))
      .attr("r", 3).attr("fill", model.color).attr("opacity", 0.7)
      .on("mouseover", (event, d) =>
        showTip(`<b>${model.label}</b><br/>tokens: ${(d.tokens/1e6).toFixed(0)}M<br/>loss: ${d.loss}<br/>ppl: ${d.ppl}`, event))
      .on("mouseout", hideTip);
  });

  // Legend
  const leg = document.getElementById("curve-legend");
  leg.innerHTML = allSeries.map(({ model }) =>
    `<span style="display:inline-flex;align-items:center;gap:6px;">
       <span style="width:20px;height:3px;background:${model.color};display:inline-block;border-radius:2px;"></span>
       ${model.label}
     </span>`).join("");
}

function initLearningCurves() {
  document.querySelectorAll(".curve-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".curve-tab").forEach(b => {
        b.className = "curve-tab px-4 py-1.5 rounded-full text-sm font-medium bg-slate-700 text-slate-300";
      });
      btn.className = "curve-tab px-4 py-1.5 rounded-full text-sm font-medium bg-blue-600 text-white";
      activeCurveLang = btn.dataset.lang;
      drawLearningCurves(activeCurveLang);
    });
  });
  drawLearningCurves("en");
}

// ── SLIDE 3 — Perplexity cards + bar chart ────────────────────────────────────
function drawPerplexity() {
  const container = document.getElementById("ppl-cards");
  if (!container) return;

  container.innerHTML = LANGS.map(lang => {
    const base  = DATA.lm[`${lang}_base`];
    const morph = DATA.lm[`${lang}_morph`];
    const bPpl  = base?.test_ppl  ?? "—";
    const mPpl  = morph?.test_ppl ?? "—";
    const delta = (base && morph)
      ? ((morph.test_ppl - base.test_ppl) / base.test_ppl * 100).toFixed(1)
      : null;
    const flag  = { en: "🇬🇧", ar: "🇸🇦", tr: "🇹🇷" }[lang];
    const deltaHtml = delta !== null
      ? `<span class="text-xs mt-1 ${parseFloat(delta) <= 0 ? 'text-green-400' : 'text-red-400'}">
           morph ${parseFloat(delta) <= 0 ? "▼" : "▲"} ${Math.abs(delta)}% vs baseline
         </span>`
      : "";
    return `<div class="card text-center">
      <div class="text-2xl mb-2">${flag} ${LANG_NAMES[lang]}</div>
      <div class="flex justify-around mt-3">
        <div>
          <div class="stat-num" style="color:var(--${lang}-base)">${typeof bPpl === "number" ? bPpl.toFixed(1) : bPpl}</div>
          <div class="stat-label">baseline PPL</div>
        </div>
        <div>
          <div class="stat-num" style="color:var(--${lang}-morph)">${typeof mPpl === "number" ? mPpl.toFixed(1) : mPpl}</div>
          <div class="stat-label">morph PPL</div>
        </div>
      </div>
      <div class="flex justify-center mt-2">${deltaHtml}</div>
    </div>`;
  }).join("");

  // Bar chart
  const margin = { top: 20, right: 20, bottom: 40, left: 55 };
  const fullW = 860, fullH = 260;
  const r = svgOf("ppl-bar-chart", margin, fullW, fullH);
  if (!r) return;
  const { svg, w, h } = r;

  const items = MODELS.map(m => ({
    label: m.label, color: m.color,
    value: DATA.lm[m.id]?.test_ppl ?? null,
  })).filter(d => d.value !== null);

  if (items.length === 0) {
    svg.append("text").attr("x",w/2).attr("y",h/2).attr("text-anchor","middle")
       .attr("fill","#475569").text("No evaluation data yet.");
    return;
  }

  const x = d3.scaleBand().domain(items.map(d => d.label)).range([0, w]).padding(0.3);
  const y = d3.scaleLinear().domain([0, d3.max(items, d => d.value) * 1.1]).range([h, 0]);

  addGrid(svg, y, "y", w);
  svg.append("g").attr("class","axis").attr("transform",`translate(0,${h})`).call(d3.axisBottom(x));
  svg.append("g").attr("class","axis").call(d3.axisLeft(y).ticks(5));
  svg.append("text").attr("transform","rotate(-90)").attr("x",-h/2).attr("y",-42)
     .attr("text-anchor","middle").attr("fill","#64748b").attr("font-size",11).text("Test Perplexity");

  svg.selectAll(".bar").data(items).enter().append("rect")
    .attr("x", d => x(d.label)).attr("width", x.bandwidth())
    .attr("y", h).attr("height", 0).attr("fill", d => d.color).attr("rx", 4)
    .on("mouseover", (event, d) => showTip(`<b>${d.label}</b><br/>Test PPL: ${d.value.toFixed(2)}`, event))
    .on("mouseout", hideTip)
    .transition().duration(800).delay((_, i) => i * 80)
    .attr("y", d => y(d.value)).attr("height", d => h - y(d.value));
}

// ── SLIDE 4 — Tokens per meaning unit ────────────────────────────────────────
function drawTPU() {
  const margin = { top: 20, right: 20, bottom: 40, left: 55 };
  const fullW = 860, fullH = 280;
  const r = svgOf("tpu-chart", margin, fullW, fullH);
  if (!r) return;
  const { svg, w, h } = r;

  const items = MODELS.map(m => ({
    label: m.label, color: m.color, lang: m.lang, regime: m.regime,
    value: DATA.morph[m.id]?.tokens_per_meaning_unit ?? null,
  })).filter(d => d.value !== null);

  if (items.length === 0) {
    svg.append("text").attr("x",w/2).attr("y",h/2).attr("text-anchor","middle")
       .attr("fill","#475569").text("No morphology evaluation data yet.");
    return;
  }

  const x = d3.scaleBand().domain(items.map(d => d.label)).range([0, w]).padding(0.3);
  const y = d3.scaleLinear().domain([0, d3.max(items, d => d.value) * 1.1]).range([h, 0]);

  addGrid(svg, y, "y", w);
  svg.append("g").attr("class","axis").attr("transform",`translate(0,${h})`).call(d3.axisBottom(x));
  svg.append("g").attr("class","axis").call(d3.axisLeft(y).ticks(5));
  svg.append("text").attr("transform","rotate(-90)").attr("x",-h/2).attr("y",-42)
     .attr("text-anchor","middle").attr("fill","#64748b").attr("font-size",11)
     .text("Tokens per meaning unit");

  svg.selectAll(".bar").data(items).enter().append("rect")
    .attr("x", d => x(d.label)).attr("width", x.bandwidth())
    .attr("y", h).attr("height", 0).attr("fill", d => d.color).attr("rx", 4)
    .on("mouseover", (event, d) => showTip(`<b>${d.label}</b><br/>Tokens/unit: ${d.value.toFixed(3)}`, event))
    .on("mouseout", hideTip)
    .transition().duration(800).delay((_, i) => i * 80)
    .attr("y", d => y(d.value)).attr("height", d => h - y(d.value));

  // Delta cards
  const deltaContainer = document.getElementById("tpu-delta-cards");
  if (deltaContainer) {
    deltaContainer.innerHTML = LANGS.map(lang => {
      const b = DATA.morph[`${lang}_base`]?.tokens_per_meaning_unit;
      const m = DATA.morph[`${lang}_morph`]?.tokens_per_meaning_unit;
      if (!b || !m) return `<div class="card text-center text-slate-500 text-sm">${LANG_NAMES[lang]}<br/>no data</div>`;
      const pct = ((m - b) / b * 100).toFixed(1);
      const better = parseFloat(pct) < 0;
      return `<div class="card text-center">
        <div class="text-sm text-slate-400 mb-1">${LANG_NAMES[lang]}</div>
        <div class="stat-num ${better ? 'text-green-400' : 'text-red-400'}">${better ? "▼" : "▲"} ${Math.abs(pct)}%</div>
        <div class="stat-label">morph vs baseline</div>
      </div>`;
    }).join("");
  }
}

// ── SLIDE 5 — Agreement accuracy ──────────────────────────────────────────────
function drawAgreement() {
  const margin = { top: 20, right: 20, bottom: 40, left: 55 };
  const fullW = 860, fullH = 280;
  const r = svgOf("agreement-chart", margin, fullW, fullH);
  if (!r) return;
  const { svg, w, h } = r;

  const items = MODELS.map(m => ({
    label: m.label, color: m.color,
    value: DATA.morph[m.id]?.agreement_accuracy ?? null,
  })).filter(d => d.value !== null);

  if (items.length === 0) {
    svg.append("text").attr("x",w/2).attr("y",h/2).attr("text-anchor","middle")
       .attr("fill","#475569").text("No morphology evaluation data yet.");
    return;
  }

  const x = d3.scaleBand().domain(items.map(d => d.label)).range([0, w]).padding(0.3);
  const y = d3.scaleLinear().domain([0, 1]).range([h, 0]);

  addGrid(svg, y, "y", w);
  svg.append("g").attr("class","axis").attr("transform",`translate(0,${h})`).call(d3.axisBottom(x));
  svg.append("g").attr("class","axis").call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".0%")));
  svg.append("text").attr("transform","rotate(-90)").attr("x",-h/2).attr("y",-42)
     .attr("text-anchor","middle").attr("fill","#64748b").attr("font-size",11)
     .text("Agreement accuracy");

  svg.selectAll(".bar").data(items).enter().append("rect")
    .attr("x", d => x(d.label)).attr("width", x.bandwidth())
    .attr("y", h).attr("height", 0).attr("fill", d => d.color).attr("rx", 4)
    .on("mouseover", (event, d) => showTip(`<b>${d.label}</b><br/>Agreement: ${(d.value*100).toFixed(1)}%`, event))
    .on("mouseout", hideTip)
    .transition().duration(800).delay((_, i) => i * 80)
    .attr("y", d => y(d.value)).attr("height", d => h - y(d.value));
}

// ── SLIDE 6 — Learning efficiency (steps to threshold) ────────────────────────
function drawEfficiency() {
  const container = document.getElementById("efficiency-chart");
  const noteEl    = document.getElementById("efficiency-note");
  if (!container) return;

  // Find threshold: 10% above the best final loss across all models
  const finalLosses = MODELS.map(m => {
    const ts = DATA.timeseries[m.id] || [];
    return ts.length ? ts[ts.length - 1].loss : null;
  }).filter(Boolean);

  if (finalLosses.length === 0) {
    container.innerHTML = `<p class="text-slate-500 text-sm p-6">No training data yet.</p>`;
    return;
  }

  const threshold = d3.min(finalLosses) * 1.15;
  if (noteEl) noteEl.textContent = `Threshold loss: ${threshold.toFixed(3)} (15% above best final loss)`;

  const items = MODELS.map(m => {
    const ts = DATA.timeseries[m.id] || [];
    const hit = ts.find(d => d.loss <= threshold);
    return { label: m.label, color: m.color, tokens: hit ? hit.tokens : null };
  }).filter(d => d.tokens !== null);

  if (items.length === 0) {
    container.innerHTML = `<p class="text-slate-500 text-sm p-6">No model has reached the threshold yet.</p>`;
    return;
  }

  const margin = { top: 20, right: 20, bottom: 40, left: 55 };
  const fullW = 860, fullH = 300;
  const r = svgOf("efficiency-chart", margin, fullW, fullH);
  if (!r) return;
  const { svg, w, h } = r;

  const x = d3.scaleLinear().domain([0, d3.max(items, d => d.tokens) * 1.05]).range([0, w]);
  const y = d3.scaleBand().domain(items.map(d => d.label)).range([0, h]).padding(0.35);

  svg.append("g").attr("class","axis").attr("transform",`translate(0,${h})`).call(
    d3.axisBottom(x).ticks(5).tickFormat(d => `${(d/1e9).toFixed(2)}B`));
  svg.append("g").attr("class","axis").call(d3.axisLeft(y));
  svg.append("text").attr("x",w/2).attr("y",h+36).attr("text-anchor","middle")
     .attr("fill","#64748b").attr("font-size",11).text("Tokens to reach threshold");

  svg.selectAll(".bar").data(items).enter().append("rect")
    .attr("y", d => y(d.label)).attr("height", y.bandwidth())
    .attr("x", 0).attr("width", 0).attr("fill", d => d.color).attr("rx", 4)
    .on("mouseover", (event, d) => showTip(`<b>${d.label}</b><br/>${(d.tokens/1e6).toFixed(0)}M tokens to threshold`, event))
    .on("mouseout", hideTip)
    .transition().duration(900).delay((_, i) => i * 100)
    .attr("width", d => x(d.tokens));

  svg.selectAll(".bar-label").data(items).enter().append("text")
    .attr("y", d => y(d.label) + y.bandwidth()/2 + 4)
    .attr("x", d => x(d.tokens) + 6).attr("font-size", 10).attr("fill","#94a3b8")
    .text(d => `${(d.tokens/1e6).toFixed(0)}M`);
}

// ── SLIDE 7 — Downstream tasks table ─────────────────────────────────────────
function drawDownstream() {
  const tbody = document.getElementById("downstream-tbody");
  if (!tbody) return;

  const rows = [];
  MODELS.forEach(m => {
    const tasks = DATA.tasks[m.id] || {};
    Object.entries(tasks).forEach(([task, d]) => {
      rows.push({
        model: m.label, color: m.color, task,
        accuracy: d.accuracy ?? null,
        f1:       d.f1       ?? null,
        em:       d.exact_match ?? null,
        latency:  d.inference_latency_ms ?? null,
      });
    });
  });

  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-slate-500 text-center py-6">No downstream evaluation data yet.</td></tr>`;
    return;
  }

  const fmt = v => v !== null ? (v * 100).toFixed(1) + "%" : "—";
  const fmtN = v => v !== null ? v.toFixed(1) : "—";

  tbody.innerHTML = rows.map(r => `
    <tr>
      <td><span style="color:${r.color};font-weight:600">${r.model}</span></td>
      <td>${r.task}</td>
      <td>${fmt(r.accuracy)}</td>
      <td>${fmt(r.f1)}</td>
      <td>${fmtN(r.em)}</td>
      <td>${r.latency !== null ? r.latency.toFixed(1) + " ms" : "—"}</td>
    </tr>`).join("");
}

// ── SLIDE 8 — Pareto chart (FLOPs vs PPL) ────────────────────────────────────
function drawPareto() {
  const margin = { top: 20, right: 30, bottom: 50, left: 70 };
  const fullW = 860, fullH = 340;
  const r = svgOf("pareto-chart", margin, fullW, fullH);
  if (!r) return;
  const { svg, w, h } = r;

  const items = MODELS.map(m => ({
    label: m.label, color: m.color,
    flops: DATA.compute[m.id]?.flops_per_token ?? null,
    ppl:   DATA.lm[m.id]?.test_ppl ?? null,
  })).filter(d => d.flops !== null && d.ppl !== null);

  if (items.length === 0) {
    svg.append("text").attr("x",w/2).attr("y",h/2).attr("text-anchor","middle")
       .attr("fill","#475569").text("No compute + evaluation data yet.");
    return;
  }

  const x = d3.scaleLinear().domain([0, d3.max(items, d => d.flops) * 1.1]).range([0, w]);
  const y = d3.scaleLinear().domain([0, d3.max(items, d => d.ppl) * 1.1]).range([h, 0]);

  addGrid(svg, y, "y", w);
  svg.append("g").attr("class","axis").attr("transform",`translate(0,${h})`).call(
    d3.axisBottom(x).ticks(5).tickFormat(d => `${(d/1e9).toFixed(1)}G`));
  svg.append("g").attr("class","axis").call(d3.axisLeft(y).ticks(6));

  svg.append("text").attr("x",w/2).attr("y",h+42).attr("text-anchor","middle")
     .attr("fill","#64748b").attr("font-size",11).text("FLOPs per token");
  svg.append("text").attr("transform","rotate(-90)").attr("x",-h/2).attr("y",-55)
     .attr("text-anchor","middle").attr("fill","#64748b").attr("font-size",11)
     .text("Test Perplexity");

  svg.selectAll(".point").data(items).enter().append("circle")
    .attr("cx", d => x(d.flops)).attr("cy", d => y(d.ppl))
    .attr("r", 0).attr("fill", d => d.color).attr("opacity", 0.85)
    .on("mouseover", (event, d) =>
      showTip(`<b>${d.label}</b><br/>FLOPs/token: ${(d.flops/1e9).toFixed(2)}G<br/>Test PPL: ${d.ppl.toFixed(2)}`, event))
    .on("mouseout", hideTip)
    .transition().duration(600).delay((_, i) => i * 100).attr("r", 10);

  svg.selectAll(".point-label").data(items).enter().append("text")
    .attr("x", d => x(d.flops) + 13).attr("y", d => y(d.ppl) + 4)
    .attr("font-size", 10).attr("fill", d => d.color).text(d => d.label);
}

// ── SLIDE 9 — Summary table ───────────────────────────────────────────────────
function drawSummaryTable() {
  const tbody = document.getElementById("summary-tbody");
  if (!tbody) return;

  const fmtN  = (v, dec=2) => v != null ? (+v).toFixed(dec) : "—";
  const fmtPct = v => v != null ? (v*100).toFixed(1)+"%" : "—";
  const fmtG  = v => v != null ? (v/1e9).toFixed(2)+"G" : "—";

  tbody.innerHTML = MODELS.map(m => {
    const lm      = DATA.lm[m.id]      || {};
    const morph   = DATA.morph[m.id]   || {};
    const compute = DATA.compute[m.id] || {};
    const ts      = DATA.timeseries[m.id] || [];
    const trainTime = ts.length ? `${(ts[ts.length-1].wall_time_sec/3600).toFixed(1)}h` : "—";
    return `<tr>
      <td style="color:${MODELS.find(x=>x.id===m.id).color};font-weight:600">${m.label}</td>
      <td>${fmtN(lm.test_ppl)}</td>
      <td>${fmtN(morph.tokens_per_meaning_unit, 3)}</td>
      <td>${fmtPct(morph.agreement_accuracy)}</td>
      <td>${fmtN(morph.nats_per_morpheme, 3)}</td>
      <td>${fmtG(compute.flops_per_token)}</td>
      <td>${fmtN(compute.inference_latency_ms, 1)} ms</td>
      <td>${trainTime}</td>
    </tr>`;
  }).join("");
}

// ── SLIDE 10 — Findings ───────────────────────────────────────────────────────
function drawFindings() {
  const container = document.getElementById("findings-container");
  if (!container) return;

  const findings = [];

  LANGS.forEach(lang => {
    const bLm = DATA.lm[`${lang}_base`];
    const mLm = DATA.lm[`${lang}_morph`];
    const bMo = DATA.morph[`${lang}_base`];
    const mMo = DATA.morph[`${lang}_morph`];

    if (bLm && mLm) {
      const pplDelta = ((mLm.test_ppl - bLm.test_ppl) / bLm.test_ppl * 100).toFixed(1);
      const dir = parseFloat(pplDelta) <= 0 ? "lower" : "higher";
      const color = parseFloat(pplDelta) <= 0 ? "text-green-400" : "text-red-400";
      findings.push(`<div class="card">
        <span class="text-slate-300">${LANG_NAMES[lang]}:</span>
        morph model test perplexity is
        <span class="${color} font-semibold">${Math.abs(pplDelta)}% ${dir}</span>
        than baseline (${mLm.test_ppl?.toFixed(1)} vs ${bLm.test_ppl?.toFixed(1)}).
      </div>`);
    }

    if (bMo && mMo) {
      const tpuDelta = ((mMo.tokens_per_meaning_unit - bMo.tokens_per_meaning_unit)
                        / bMo.tokens_per_meaning_unit * 100).toFixed(1);
      const dir = parseFloat(tpuDelta) <= 0 ? "fewer" : "more";
      const color = parseFloat(tpuDelta) <= 0 ? "text-green-400" : "text-red-400";
      findings.push(`<div class="card">
        <span class="text-slate-300">${LANG_NAMES[lang]}:</span>
        morph tokenization uses
        <span class="${color} font-semibold">${Math.abs(tpuDelta)}% ${dir} tokens per meaning unit</span>
        than baseline (${mMo.tokens_per_meaning_unit?.toFixed(3)} vs ${bMo.tokens_per_meaning_unit?.toFixed(3)}).
      </div>`);
    }
  });

  if (findings.length === 0) {
    container.innerHTML = `<div class="card text-slate-500">
      No results yet. Run the full pipeline to populate findings.
    </div>`;
    return;
  }

  container.innerHTML = findings.join("");
}

// ── Main init ─────────────────────────────────────────────────────────────────
async function init() {
  buildNav();
  initFadeIn();
  await loadAll();
  initLearningCurves();
  drawPerplexity();
  drawTPU();
  drawAgreement();
  drawEfficiency();
  drawDownstream();
  drawPareto();
  drawSummaryTable();
  drawFindings();
}

document.addEventListener("DOMContentLoaded", init);
