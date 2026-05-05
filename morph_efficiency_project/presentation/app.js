/* ============================================================
   app.js — Morphological Efficiency Dashboard
   Uses D3 v7. No build step — open index.html in browser.
   ============================================================ */
"use strict";

const LANGS      = ["en", "ar", "tr"];
const LANG_NAMES = { en: "English", ar: "Arabic", tr: "Turkish" };

const MINI_COLORS = {
  en_baseline: "#394195", en_morph: "#a74d79",
  ar_baseline: "#59a150", ar_morph: "#1d5619",
  tr_baseline: "#769bb9", tr_morph: "#df3e29",
};

const LANG_COLORS = { en: "#394195", ar: "#59a150", tr: "#769bb9" };

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
  const slides    = document.querySelectorAll(".slide");
  const nav       = document.getElementById("nav-dots");
  slides.forEach((s, i) => {
    const dot = document.createElement("div");
    dot.className = "dot" + (i === 0 ? " active" : "");
    dot.title = s.querySelector("h1,h2")?.textContent?.trim() || `Slide ${i}`;
    dot.addEventListener("click", () =>
      container.scrollTo({ top: s.offsetTop, behavior: "smooth" }));
    nav.appendChild(dot);
  });
  const dots = nav.querySelectorAll(".dot");
  const obs = new IntersectionObserver(entries => {
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
  const w = fullW - margin.left - margin.right;
  const h = fullH - margin.top  - margin.bottom;
  const svg = d3.select(el).append("svg")
    .attr("width","100%").attr("height", fullH)
    .attr("viewBox", `0 0 ${fullW} ${fullH}`)
    .append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  return { svg, w, h };
}

function addGrid(svg, scale, dir, size) {
  const axis = dir === "y"
    ? d3.axisLeft(scale).tickSize(-size).tickFormat("")
    : d3.axisBottom(scale).tickSize(-size).tickFormat("");
  svg.append("g").attr("class","grid").call(axis).select(".domain").remove();
}

// ── Arabic non-joining letters — tatweel must NOT follow these ───────────────
// These letters never connect to the next character on their left side.
const AR_NON_JOINING = new Set([...'اأإآةوردذزرءى']);
function arCanJoin(char) {
  // Returns false if this character cannot carry a tatweel on its left side
  return char && !AR_NON_JOINING.has(char);
}

// ── SLIDE 1b — Tokenisation Examples ─────────────────────────────────────────
function drawTokenisationExamples() {
  const examples = EMBEDDED_DATA.tok_examples || {};
  const container = document.getElementById("tok-examples-container");
  if (!container || !Object.keys(examples).length) return;

  const langOrder   = ["en", "ar", "tr"];
  const baseColors  = { en: "#394195", ar: "#59a150", tr: "#769bb9" };
  const morphColors = { en: "#a74d79", ar: "#e56a30", tr: "#df3e29" };

  // Parse a raw tag string into { pre, suf } — both may be null
  function parseTag(tag) {
    if (tag === "ROOT") return { pre: null, suf: null };
    if (tag.startsWith("PRE_") && tag.includes("_SUF_")) {
      const inner = tag.slice(4);
      const idx   = inner.indexOf("_SUF_");
      return { pre: inner.slice(0, idx), suf: inner.slice(idx + 5) };
    }
    if (tag.startsWith("PRE_")) return { pre: tag.slice(4), suf: null };
    if (tag.startsWith("SUF_")) return { pre: null, suf: tag.slice(4) };
    return { pre: null, suf: tag };
  }

  // Build one morph chip as a single inline breadcrumb
  function makeMorphChip(tok, lang, mc) {
    const { pre, suf } = parseTag(tok.tag);
    const isAr   = lang === "ar";
    const isRoot = !pre && !suf;

    const chip = document.createElement("span");
    chip.className = "morph-chip";
    chip.style.background = mc + "1a";
    chip.style.border     = `1px solid ${mc}50`;
    chip.title = tok.surface;

    if (isRoot) {
      const r = document.createElement("span");
      r.className = "mc-root";
      r.style.opacity = "0.65";
      r.textContent = tok.root;
      chip.appendChild(r);
      return chip;
    }

    if (isAr) {
      // Arabic RTL: bake tatweel directly into each span's text so there
      // are no gaps between the coloured boxes.
      // Only add tatweel where the last character of the preceding span
      // is a joining letter (non-joining letters: ا أ إ آ ة و ر د ذ ز).
      chip.setAttribute("dir", "rtl");

      // Does the prefix end in a joining letter?
      const preJoins = pre && arCanJoin(pre[pre.length - 1]);
      // Does the root end in a joining letter?
      const rootJoins = tok.root && arCanJoin(tok.root[tok.root.length - 1]);

      if (pre) {
        const preEl = document.createElement("span");
        preEl.className = "mc-affix";
        preEl.style.color      = mc;
        preEl.style.background = mc + "28";
        preEl.textContent = pre + (preJoins ? "ـ" : "");
        chip.appendChild(preEl);
      }

      const rootEl = document.createElement("span");
      rootEl.className = "mc-root";
      rootEl.textContent = (preJoins ? "ـ" : "") + tok.root + (suf && rootJoins ? "ـ" : "");
      chip.appendChild(rootEl);

      if (suf) {
        const sufEl = document.createElement("span");
        sufEl.className = "mc-affix";
        sufEl.style.color      = mc;
        sufEl.style.background = mc + "28";
        sufEl.textContent = (rootJoins ? "ـ" : "") + suf;
        chip.appendChild(sufEl);
      }
    } else {
      // Latin: [pre-]root[suf] inline
      if (pre) {
        const preEl = document.createElement("span");
        preEl.className = "mc-affix";
        preEl.style.color      = mc;
        preEl.style.background = mc + "28";
        preEl.textContent = pre + "-";
        chip.appendChild(preEl);
      }

      const rootEl = document.createElement("span");
      rootEl.className = "mc-root";
      rootEl.textContent = tok.root;
      chip.appendChild(rootEl);

      if (suf) {
        const sufEl = document.createElement("span");
        sufEl.className = "mc-affix";
        sufEl.style.color      = mc;
        sufEl.style.background = mc + "28";
        sufEl.textContent = suf;
        chip.appendChild(sufEl);
      }
    }

    return chip;
  }

  // Inject form badge inside the chip itself, below a gray separator line
  function wrapWithForm(chip, tok) {
    const hasForm  = tok.form;
    const hasLabel = tok.form_label;
    if (!hasForm && !hasLabel) return chip;
    // Collect existing children into a nowrap row so they never break
    const row = document.createElement("span");
    row.style.cssText = "display:inline-flex;align-items:center;white-space:nowrap;";
    while (chip.firstChild) row.appendChild(chip.firstChild);
    chip.style.display       = "inline-flex";
    chip.style.flexDirection = "column";
    chip.style.alignItems    = "center";
    chip.appendChild(row);
    const sep = document.createElement("div");
    sep.className = "form-sep";
    sep.style.cssText = "width:100%;border-top:1px solid #333;margin-top:3px;padding-top:2px;font-size:0.5rem;text-align:center;font-family:'Noto Naskh Arabic',sans-serif;line-height:1.3;white-space:nowrap;overflow:hidden;max-height:0;opacity:0;transition:max-height 0.27s ease,opacity 0.27s ease,margin-top 0.27s ease,padding-top 0.27s ease;margin-top:0;padding-top:0;border-top-color:transparent;";
    sep.setAttribute("dir", "rtl");
    if (hasForm) {
      const hasDef = tok.tag && tok.tag.includes("PRE_ال");
      if (hasDef) {
        const defSpan = document.createElement("span");
        defSpan.style.color = "#6b6b6b";
        defSpan.textContent = "الـ";
        const patSpan = document.createElement("span");
        patSpan.style.color = "#b0b0b0";
        patSpan.textContent = `${tok.form_pattern} · ${tok.form}`;
        sep.appendChild(defSpan);
        sep.appendChild(patSpan);
      } else {
        const patSpan = document.createElement("span");
        patSpan.style.color = "#b0b0b0";
        patSpan.textContent = `${tok.form_pattern} · ${tok.form}`;
        sep.appendChild(patSpan);
      }
    } else {
      sep.style.color = "#6b6b6b";
      sep.textContent = tok.form_label;
    }
    chip.appendChild(sep);
    return chip;
  }

  container.innerHTML = langOrder.map(lang => {
    const ex = examples[lang];
    if (!ex) return "";
    const isRtl = lang === "ar";
    const bc = baseColors[lang];
    const mc = morphColors[lang];
    return `
    <div class="card" style="padding:1.1rem 1.4rem;">
      <div class="flex items-baseline gap-3 mb-3 flex-wrap">
        <span style="font-family:'Noto Naskh Arabic',sans-serif;font-weight:700;font-size:0.85rem;color:#6b6b6b;text-transform:uppercase;letter-spacing:0.08em;">${LANG_NAMES[lang]}</span>
        <span class="tok-sentence" ${isRtl ? 'dir="rtl" style="flex:1;text-align:right;"' : ''} >${ex.sentence}</span>
      </div>
      <div class="grid grid-cols-2 gap-5">
        <div>
          <p style="font-size:0.68rem;color:#3d3d3d;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.55rem;">
            BPE baseline — <span style="color:${bc};font-weight:700;">${ex.baseline.length} tokens</span>
          </p>
          <div class="tok-chips-base-${lang}" style="display:flex;flex-wrap:wrap;align-items:center;${isRtl ? 'direction:rtl;' : ''}gap:1px;"></div>
        </div>
        <div>
          <p style="font-size:0.68rem;color:#3d3d3d;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.55rem;display:flex;align-items:center;gap:6px;">
            Morph — <span style="color:${mc};font-weight:700;">${ex.morph.length} tokens</span>
            <span style="color:#2a2a2a;margin-left:5px;">(${ex.baseline.length - ex.morph.length} fewer)</span>
            ${isRtl ? `<button class="forms-toggle-btn" data-lang="${lang}" style="margin-left:auto;font-size:0.6rem;padding:1px 7px;border:1px solid #e56a30;border-radius:3px;background:transparent;color:#6b6b6b;cursor:pointer;letter-spacing:0.05em;font-family:inherit;">Forms</button>` : ''}
          </p>
          <div class="tok-chips-morph-${lang}" style="display:flex;flex-wrap:wrap;align-items:flex-start;${isRtl ? 'direction:rtl;' : ''}gap:2px;"></div>
        </div>
      </div>
    </div>`;
  }).join("");

  // Animate chips in when slide scrolls into view
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      obs.disconnect();
      let delay = 0;

      langOrder.forEach(lang => {
        const ex = examples[lang];
        if (!ex) return;
        const bc = baseColors[lang];
        const mc = morphColors[lang];

        // BPE chips — group fragments into words, add tatweel for Arabic
        const baseEl = container.querySelector(`.tok-chips-base-${lang}`);
        if (baseEl) {
          baseEl.className = baseEl.className.replace(/\S+/g, c => c) + " bpe-row";
          const isAr = lang === "ar";

          // Group tokens into words: a new word starts whenever ▁ is present
          const words = [];
          let cur = [];
          ex.baseline.forEach(tok => {
            if (tok.startsWith("▁") && cur.length) { words.push(cur); cur = []; }
            cur.push(tok);
          });
          if (cur.length) words.push(cur);

          let wordDelay = delay;
          words.forEach((frags, wi) => {
            const wordEl = document.createElement("span");
            wordEl.className = "bpe-word";
            wordEl.style.background = bc + "20";
            wordEl.style.border     = `1px solid ${bc}45`;

            // For Arabic, bake tatweel into both touching edges of each join
            // so there are no isolated connector characters between spans.
            // Skip tatweel if the preceding fragment ends in a non-joining letter.
            const fragEls = frags.map((tok, fi) => {
              const raw  = tok.replace(/^▁/, "");
              let text = raw;
              if (isAr) {
                const prevRaw = fi > 0 ? frags[fi - 1].replace(/^▁/, "") : "";
                const prevJoins = prevRaw && arCanJoin(prevRaw[prevRaw.length - 1]);
                const nextExists = fi < frags.length - 1;
                const leadTw  = fi > 0 && prevJoins ? "ـ" : "";
                // trailing tatweel: only if this frag ends in a joining letter
                const trailTw = nextExists && arCanJoin(raw[raw.length - 1]) ? "ـ" : "";
                text = leadTw + raw + trailTw;
              }
              const frag = document.createElement("span");
              frag.className = "bpe-frag " + (fi === 0 ? "frag-first" : "frag-cont");
              frag.textContent = text;
              return frag;
            });
            fragEls.forEach(f => wordEl.appendChild(f));

            baseEl.appendChild(wordEl);
            setTimeout(() => wordEl.classList.add("show"), wordDelay + wi * 60);
          });
          delay += words.length * 60 + 100;
        }

        // Morph chips
        const morphEl = container.querySelector(`.tok-chips-morph-${lang}`);
        if (morphEl) {
          ex.morph.forEach((tok, i) => {
            const chip = makeMorphChip(tok, lang, mc);
            const el = wrapWithForm(chip, tok);
            morphEl.appendChild(el);
            setTimeout(() => chip.classList.add("show"), delay + i * 85);
          });
          delay += ex.morph.length * 85 + 140;
        }
      });

      // Wire Forms toggle buttons (Arabic only)
      container.querySelectorAll(".forms-toggle-btn").forEach(btn => {
        const lang = btn.dataset.lang;
        const morphEl = container.querySelector(`.tok-chips-morph-${lang}`);
        let expanded = false;

        function openSep(sep) {
          sep.style.maxHeight     = sep.scrollHeight + "px";
          sep.style.opacity       = "1";
          sep.style.marginTop     = "3px";
          sep.style.paddingTop    = "2px";
          sep.style.borderTopColor = "#333";
        }
        function closeSep(sep) {
          sep.style.maxHeight      = "0";
          sep.style.opacity        = "0";
          sep.style.marginTop      = "0";
          sep.style.paddingTop     = "0";
          sep.style.borderTopColor = "transparent";
        }

        // Lock min-height on first expand so the card never shrinks
        let heightLocked = false;

        btn.addEventListener("click", () => {
          expanded = !expanded;
          if (expanded && !heightLocked) {
            // Temporarily open all to measure full height, then lock
            morphEl.querySelectorAll(".form-sep").forEach(openSep);
            requestAnimationFrame(() => {
              morphEl.style.minHeight = morphEl.scrollHeight + "px";
              heightLocked = true;
            });
          } else if (expanded) {
            morphEl.querySelectorAll(".form-sep").forEach(openSep);
          } else {
            morphEl.querySelectorAll(".form-sep").forEach(closeSep);
          }
          btn.style.color       = expanded ? mc    : "#6b6b6b";
          btn.style.borderColor = expanded ? mc    : "#333";
        });
      });
    });
  }, { root: document.getElementById("slides-container"), threshold: 0.25 });

  const slide = document.getElementById("slide-tok");
  if (slide) obs.observe(slide);
}


// ── SLIDE 3 — Mini PPL cards + ratio bar ─────────────────────────────────────
function drawMiniPPL() {
  const mini   = EMBEDDED_DATA.mini   || {};
  const evalD  = mini.eval            || {};
  const byLang = mini.summary?.by_lang || {};

  const cards = document.getElementById("mini-ppl-cards");
  if (cards) {
    cards.innerHTML = LANGS.map(lang => {
      const base  = evalD[`${lang}_baseline`];
      const morph = evalD[`${lang}_morph`];
      const bPpl  = base?.test_ppl;
      const mPpl  = morph?.test_ppl;
      const ratio = byLang[lang]?.ppl_ratio;
      const win   = ratio != null && ratio < 1;
      return `<div class="card text-center">
        <div class="font-semibold mb-3">${LANG_NAMES[lang]}</div>
        <div class="flex justify-around">
          <div>
            <div class="stat-num" style="color:${MINI_COLORS[lang+'_baseline']}">${bPpl != null ? bPpl.toFixed(1) : "—"}</div>
            <div class="stat-label">baseline PPL</div>
          </div>
          <div>
            <div class="stat-num" style="color:${MINI_COLORS[lang+'_morph']}">${mPpl != null ? mPpl.toFixed(1) : "—"}</div>
            <div class="stat-label">morph PPL</div>
          </div>
        </div>
        ${ratio != null ? `<div class="text-xs mt-2 ${win ? 'text-green-400' : 'text-red-400'}">ratio ${ratio.toFixed(3)} — morph ${win ? 'wins' : 'loses'}</div>` : ""}
      </div>`;
    }).join("");
  }

  const r = svgOf("mini-ratio-chart", { top: 15, right: 20, bottom: 30, left: 55 }, 860, 155);
  if (!r) return;
  const { svg, w, h } = r;

  const items = LANGS.map(lang => ({
    lang, label: LANG_NAMES[lang],
    ratio: byLang[lang]?.ppl_ratio ?? null,
    color: MINI_COLORS[lang + "_morph"],
  })).filter(d => d.ratio !== null);

  const x = d3.scaleBand().domain(items.map(d => d.label)).range([0, w]).padding(0.4);
  const y = d3.scaleLinear().domain([0, 1.1]).range([h, 0]);

  addGrid(svg, y, "y", w);
  svg.append("g").attr("class","axis").attr("transform",`translate(0,${h})`).call(d3.axisBottom(x));
  svg.append("g").attr("class","axis").call(d3.axisLeft(y).ticks(4).tickFormat(d3.format(".1f")));

  svg.append("line").attr("x1",0).attr("x2",w).attr("y1",y(1)).attr("y2",y(1))
     .attr("stroke","#3d3d3d").attr("stroke-dasharray","4,3").attr("stroke-width",1);
  svg.append("text").attr("x",w+4).attr("y",y(1)+4).attr("fill","#3d3d3d").attr("font-size",9).text("baseline");
  svg.append("text").attr("transform","rotate(-90)").attr("x",-h/2).attr("y",-42)
     .attr("text-anchor","middle").attr("fill","#6b6b6b").attr("font-size",10).text("morph / baseline PPL");

  svg.selectAll(".bar").data(items).enter().append("rect")
    .attr("x", d => x(d.label)).attr("width", x.bandwidth())
    .attr("y", h).attr("height", 0).attr("fill", d => d.color).attr("rx", 4)
    .on("mouseover", (event, d) => showTip(`<b>${d.label}</b><br/>ratio: ${d.ratio.toFixed(3)}<br/>${d.ratio < 1 ? "morph wins" : "morph loses"}`, event))
    .on("mouseout", hideTip)
    .transition().duration(700).delay((_, i) => i * 120)
    .attr("y", d => y(d.ratio)).attr("height", d => h - y(d.ratio));

  svg.selectAll(".bar-label").data(items).enter().append("text")
    .attr("x", d => x(d.label) + x.bandwidth() / 2).attr("text-anchor","middle")
    .attr("y", d => y(d.ratio) - 5).attr("font-size", 11).attr("fill", d => d.color)
    .text(d => d.ratio.toFixed(3));
}

// ── SLIDE 3b — Mini learning curves per language ──────────────────────────────
function drawMiniCurves() {
  const tsData = EMBEDDED_DATA.mini?.timeseries || {};

  LANGS.forEach(lang => {
    const containerId = `mini-curve-${lang}`;
    const el = document.getElementById(containerId);
    if (!el) return;

    const baseKey  = `${lang}_baseline`;
    const morphKey = `${lang}_morph`;
    const basePts  = tsData[baseKey]  || [];
    const morphPts = tsData[morphKey] || [];

    if (!basePts.length && !morphPts.length) {
      el.innerHTML = `<p class="text-slate-500 text-xs p-3">No data</p>`;
      return;
    }

    const margin = { top: 28, right: 12, bottom: 36, left: 44 };
    const fullW = 260, fullH = 300;
    const w = fullW - margin.left - margin.right;
    const h = fullH - margin.top  - margin.bottom;

    const svgEl = d3.select(el).append("svg")
      .attr("viewBox", `0 0 ${fullW} ${fullH}`)
      .attr("preserveAspectRatio","xMidYMid meet")
      .style("width","100%").style("height","100%");

    const g = svgEl.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const allPts = [...basePts, ...morphPts];
    const xMax = d3.max(allPts, d => d.step);
    const yMax = d3.max(allPts, d => d.loss);
    const yMin = d3.min(allPts, d => d.loss);

    const x = d3.scaleLinear().domain([0, xMax]).range([0, w]);
    const y = d3.scaleLinear().domain([yMin * 0.97, yMax * 1.02]).range([h, 0]);

    g.append("g").attr("class","axis").attr("transform",`translate(0,${h})`)
     .call(d3.axisBottom(x).ticks(4).tickFormat(d => `${d/1000}k`));
    g.append("g").attr("class","axis").call(d3.axisLeft(y).ticks(4).tickFormat(d3.format(".1f")));

    svgEl.append("text").attr("x", fullW / 2).attr("y", 14)
      .attr("text-anchor","middle").attr("fill","#8a8a8a").attr("font-size",11)
      .attr("font-weight","600").text(LANG_NAMES[lang]);

    const lineGen = d3.line().x(d => x(d.step)).y(d => y(d.loss)).curve(d3.curveMonotoneX);

    function animateLine(pts, color, dashed) {
      if (!pts.length) return;
      const path = g.append("path").datum(pts).attr("fill","none")
        .attr("stroke", color).attr("stroke-width", 1.8)
        .attr("d", lineGen);
      if (dashed) path.attr("stroke-dasharray","5,3");
      const len = path.node().getTotalLength();
      path.attr("stroke-dashoffset", len)
        .attr("stroke-dasharray", dashed ? `5,3` : `${len}`)
        .transition().duration(900).ease(d3.easeLinear)
        .attr("stroke-dashoffset", 0)
        .on("end", () => { if (!dashed) path.attr("stroke-dasharray", null); });
    }

    animateLine(basePts,  MINI_COLORS[baseKey],  false);
    animateLine(morphPts, MINI_COLORS[morphKey], true);
  });

  // Efficiency summary cards below curves
  const mini   = EMBEDDED_DATA.mini   || {};
  const evalD  = mini.eval            || {};
  const byLang = mini.summary?.by_lang || {};
  const effCards = document.getElementById("mini-efficiency-cards");
  if (effCards) {
    effCards.innerHTML = LANGS.map(lang => {
      const ratio = byLang[lang]?.ppl_ratio;
      const pct   = ratio != null ? ((1 - ratio) * 100).toFixed(1) : null;
      const win   = ratio != null && ratio < 1;
      return `<div class="card text-center py-2">
        <div class="text-xs text-slate-500 uppercase tracking-wider mb-1">${LANG_NAMES[lang]}</div>
        ${pct != null
          ? `<div class="text-lg font-bold ${win ? 'text-green-400' : 'text-red-400'}">${win ? '-' : '+'}${Math.abs(pct)}% PPL</div>
             <div class="text-xs text-slate-500">${win ? 'morph wins' : 'morph loses'}</div>`
          : `<div class="text-slate-500 text-sm">—</div>`}
      </div>`;
    }).join("");
  }
}

// ── SLIDE 3c — Token compression + TPU + UNK rate ────────────────────────────
function drawMiniCompression() {
  const mini  = EMBEDDED_DATA.mini?.eval || {};

  const tokenItems = LANGS.flatMap(lang => {
    const b = mini[`${lang}_baseline`];
    const m = mini[`${lang}_morph`];
    return [
      { lang, regime: "baseline", label: `${LANG_NAMES[lang]} base`, color: MINI_COLORS[lang+"_baseline"], value: b?.num_tokens ?? null },
      { lang, regime: "morph",    label: `${LANG_NAMES[lang]} morph`, color: MINI_COLORS[lang+"_morph"],    value: m?.num_tokens ?? null },
    ];
  }).filter(d => d.value !== null);

  const r1 = svgOf("mini-tokens-chart", { top: 10, right: 10, bottom: 32, left: 62 }, 380, 220);
  if (r1) {
    const { svg, w, h } = r1;
    const x = d3.scaleBand().domain(tokenItems.map(d => d.label)).range([0, w]).padding(0.25);
    const y = d3.scaleLinear().domain([0, d3.max(tokenItems, d => d.value) * 1.1]).range([h, 0]);
    addGrid(svg, y, "y", w);
    svg.append("g").attr("class","axis").attr("transform",`translate(0,${h})`)
       .call(d3.axisBottom(x).tickFormat(l => l.replace(" base","").replace(" morph","")));
    svg.append("g").attr("class","axis").call(d3.axisLeft(y).ticks(4).tickFormat(d => `${(d/1000).toFixed(0)}k`));
    svg.append("text").attr("transform","rotate(-90)").attr("x",-h/2).attr("y",-52)
       .attr("text-anchor","middle").attr("fill","#6b6b6b").attr("font-size",9).text("Test tokens");
    svg.selectAll(".bar").data(tokenItems).enter().append("rect")
      .attr("x", d => x(d.label)).attr("width", x.bandwidth())
      .attr("y", h).attr("height", 0).attr("fill", d => d.color).attr("rx", 3)
      .on("mouseover", (event, d) => showTip(`<b>${d.label}</b><br/>${d.value.toLocaleString()} tokens`, event))
      .on("mouseout", hideTip)
      .transition().duration(700).delay((_, i) => i * 80)
      .attr("y", d => y(d.value)).attr("height", d => h - y(d.value));
  }

  const tpuItems = LANGS.map(lang => ({
    label: LANG_NAMES[lang],
    color: MINI_COLORS[lang+"_morph"],
    value: mini[`${lang}_morph`]?.tokens_per_meaning_unit ?? null,
  })).filter(d => d.value !== null);

  const r2 = svgOf("mini-tpu-chart", { top: 5, right: 20, bottom: 24, left: 65 }, 380, 135);
  if (r2) {
    const { svg, w, h } = r2;
    const x = d3.scaleLinear().domain([0, d3.max(tpuItems, d => d.value) * 1.1]).range([0, w]);
    const y = d3.scaleBand().domain(tpuItems.map(d => d.label)).range([0, h]).padding(0.35);
    svg.append("g").attr("class","axis").attr("transform",`translate(0,${h})`).call(d3.axisBottom(x).ticks(4));
    svg.append("g").attr("class","axis").call(d3.axisLeft(y));
    svg.selectAll(".bar").data(tpuItems).enter().append("rect")
      .attr("y", d => y(d.label)).attr("height", y.bandwidth())
      .attr("x", 0).attr("width", 0).attr("fill", d => d.color).attr("rx", 3)
      .on("mouseover", (event, d) => showTip(`<b>${d.label} morph</b><br/>${d.value.toFixed(2)} tokens/unit`, event))
      .on("mouseout", hideTip)
      .transition().duration(700).delay((_, i) => i * 120)
      .attr("width", d => x(d.value));
    svg.selectAll(".bar-label").data(tpuItems).enter().append("text")
      .attr("y", d => y(d.label) + y.bandwidth() / 2 + 4)
      .attr("x", d => x(d.value) + 5).attr("font-size", 10).attr("fill", d => d.color)
      .text(d => d.value.toFixed(2));
  }

  const unkContainer = document.getElementById("mini-unk-bars");
  if (unkContainer) {
    const unkItems = LANGS.map(lang => ({
      label: LANG_NAMES[lang],
      color: MINI_COLORS[lang+"_morph"],
      value: mini[`${lang}_morph`]?.unk_rate ?? null,
    })).filter(d => d.value !== null);
    unkContainer.innerHTML = unkItems.map(d => `
      <div>
        <div class="flex justify-between text-xs mb-1">
          <span style="color:${d.color}">${d.label}</span>
          <span class="text-slate-400">${(d.value * 100).toFixed(1)}% unknown</span>
        </div>
        <div style="background:#1a1a1a;border-radius:4px;height:8px;overflow:hidden;">
          <div style="width:${(d.value*100).toFixed(1)}%;height:100%;background:${d.color};border-radius:4px;transition:width 0.6s ease;"></div>
        </div>
      </div>`).join("");
  }
}

// ── SLIDE 3d — Bundle Agreement Accuracy bars ─────────────────────────────────
function drawMiniAgreement() {
  const evalD  = EMBEDDED_DATA.mini?.eval || {};
  const byLang = EMBEDDED_DATA.mini?.summary?.by_lang || {};
  const container = document.getElementById("mini-agreement-bars");
  if (!container) return;

  // Random baselines: 1/n_bundles per language
  const randomBaseline = { en: 1/23, ar: 1/270, tr: 1/63 };

  const items = LANGS.map(lang => ({
    lang,
    label: LANG_NAMES[lang],
    color: MINI_COLORS[lang + "_morph"],
    accuracy: evalD[`${lang}_morph`]?.bundle_accuracy ?? byLang[lang]?.bundle_accuracy ?? null,
    random: randomBaseline[lang],
  })).filter(d => d.accuracy !== null);

  container.innerHTML = items.map(d => {
    const pct = (d.accuracy * 100).toFixed(1);
    const rndPct = (d.random * 100).toFixed(1);
    return `
    <div>
      <div class="flex justify-between text-xs mb-1">
        <span style="color:${d.color}" class="font-semibold">${d.label}</span>
        <span class="text-slate-300">${pct}% accuracy
          <span class="text-slate-500 ml-2">(random baseline: ${rndPct}%)</span>
        </span>
      </div>
      <div style="background:#1a1a1a;border-radius:4px;height:10px;overflow:hidden;position:relative;">
        <div class="acc-bar-fill" data-width="${pct}"
             style="width:0%;height:100%;background:${d.color};border-radius:4px;transition:width 0.8s ease;"></div>
        <div style="position:absolute;top:0;left:${rndPct}%;width:2px;height:100%;background:#f59e0b;opacity:0.8;"></div>
      </div>
    </div>`;
  }).join("");

  // Animate bars in when slide is visible
  const slide = document.getElementById("slide-3d");
  if (!slide) return;
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      obs.disconnect();
      container.querySelectorAll(".acc-bar-fill").forEach(el => {
        setTimeout(() => { el.style.width = el.dataset.width + "%"; }, 200);
      });
    });
  }, { root: document.getElementById("slides-container"), threshold: 0.3 });
  obs.observe(slide);
}

// ── SLIDE 6 — EN learning curves (full scale) ─────────────────────────────────
function drawLearningCurves() {
  const margin = { top: 20, right: 20, bottom: 50, left: 55 };
  const fullW = 900, fullH = 380;
  const r = svgOf("learning-curve-chart", margin, fullW, fullH);
  if (!r) return;
  const { svg, w, h } = r;

  const enModels = [
    { id: "en_baseline", label: "en_baseline", color: "#394195" },
    { id: "en_morph",    label: "en_morph",    color: "#a74d79" },
  ];

  const allSeries = enModels.map(m => ({
    model: m,
    data: (EMBEDDED_DATA.timeseries[m.id] || []).filter(d => d.loss != null),
  })).filter(s => s.data.length > 0);

  if (allSeries.length === 0) {
    svg.append("text").attr("x",w/2).attr("y",h/2).attr("text-anchor","middle")
       .attr("fill","#3d3d3d").text("No training data available.");
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
  svg.append("text").attr("x",w/2).attr("y",h+40).attr("text-anchor","middle")
     .attr("fill","#6b6b6b").attr("font-size",11).text("Tokens processed");
  svg.append("text").attr("transform","rotate(-90)").attr("x",-h/2).attr("y",-42)
     .attr("text-anchor","middle").attr("fill","#6b6b6b").attr("font-size",11).text("Loss");

  const line = d3.line().x(d => x(d.tokens)).y(d => y(d.loss)).curve(d3.curveMonotoneX);

  allSeries.forEach(({ model, data }) => {
    const path = svg.append("path").datum(data)
      .attr("fill","none").attr("stroke", model.color)
      .attr("stroke-width", 2).attr("d", line);
    const len = path.node().getTotalLength();
    path.attr("stroke-dasharray", len).attr("stroke-dashoffset", len)
      .transition().duration(1200).ease(d3.easeLinear).attr("stroke-dashoffset", 0);

    svg.selectAll(`.dot-${model.id}`).data(data.filter((_,i) => i % 5 === 0))
      .enter().append("circle")
      .attr("cx", d => x(d.tokens)).attr("cy", d => y(d.loss))
      .attr("r", 3).attr("fill", model.color).attr("opacity", 0.7)
      .on("mouseover", (event, d) =>
        showTip(`<b>${model.label}</b><br/>tokens: ${(d.tokens/1e6).toFixed(0)}M<br/>loss: ${d.loss}<br/>ppl: ${d.ppl}`, event))
      .on("mouseout", hideTip);
  });

  const leg = document.getElementById("curve-legend");
  if (leg) {
    leg.innerHTML = allSeries.map(({ model }) =>
      `<span style="display:inline-flex;align-items:center;gap:6px;">
         <span style="width:20px;height:3px;background:${model.color};display:inline-block;border-radius:2px;"></span>
         ${model.label}
       </span>`).join("");
  }
}

// ── Main init ─────────────────────────────────────────────────────────────────
async function init() {
  if (typeof lucide !== "undefined") {
    lucide.createIcons();
    // Force token-id-seq icon color — Lucide replaces <i> with <svg> and drops inline style
    const hashNode = document.getElementById("node-token-id-seq");
    if (hashNode) {
      const svg = hashNode.querySelector(".pipeline-node-icon svg");
      if (svg) { svg.style.color = "#394195"; svg.style.stroke = "#394195"; }
    }
  }
  buildNav();
  initFadeIn();
  drawTokenisationExamples();
  drawMiniPPL();
  drawMiniCurves();
  drawMiniCompression();
  drawMiniAgreement();
  drawLearningCurves();

  // Fullscreen toggle
  const btn      = document.getElementById("btn-fullscreen");
  const iconExp  = document.getElementById("fs-icon-expand");
  const iconComp = document.getElementById("fs-icon-compress");
  function syncIcon() {
    const isFs = !!document.fullscreenElement;
    iconExp.style.display  = isFs ? "none"  : "";
    iconComp.style.display = isFs ? ""      : "none";
  }
  if (btn) {
    btn.addEventListener("click", () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    });
    document.addEventListener("fullscreenchange", syncIcon);
    // keyboard shortcut: F key
    document.addEventListener("keydown", e => {
      if (e.key === "f" || e.key === "F") btn.click();
    });
  }

  // Presenter keys: B = blackout, H = hide chrome (nav dots + logos + fs btn)
  let blackoutEl = null;
  document.addEventListener("keydown", e => {
    if (e.key === "b" || e.key === "B") {
      if (blackoutEl) { blackoutEl.remove(); blackoutEl = null; return; }
      blackoutEl = document.createElement("div");
      blackoutEl.style.cssText = "position:fixed;inset:0;background:#000;z-index:9999;";
      document.body.appendChild(blackoutEl);
    }
    if (e.key === "h" || e.key === "H") {
      const ids = ["nav-dots", "uni-logo", "bme-icon", "btn-fullscreen"];
      ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = (el.style.display === "none") ? "" : "none";
      });
    }
  });

  // Arrow key slide navigation
  const scroller = document.getElementById("slides-container");
  const slideEls = () => [...document.querySelectorAll(".slide")];
  document.addEventListener("keydown", e => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp" &&
        e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const slides  = slideEls();
    const scrollTop = scroller.scrollTop;
    // Find the slide closest to the current scroll position
    let cur = 0;
    let minDist = Infinity;
    slides.forEach((s, i) => {
      const dist = Math.abs(s.offsetTop - scrollTop);
      if (dist < minDist) { minDist = dist; cur = i; }
    });
    const next = (e.key === "ArrowDown" || e.key === "ArrowRight")
      ? Math.min(cur + 1, slides.length - 1)
      : Math.max(cur - 1, 0);
    scroller.scrollTo({ top: slides[next].offsetTop, behavior: "smooth" });
  });
}

document.addEventListener("DOMContentLoaded", init);
