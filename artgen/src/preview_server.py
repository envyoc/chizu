from flask import Flask, jsonify, request, render_template_string
import json, os, random, math, io, base64
from PIL import Image

app = Flask(__name__)
CONFIG_PATH = "config.json"

# ── config helpers ─────────────────────────────────────────────────────────────

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def load_palette(config):
    palette = []
    for hex_color in config["palette"]:
        h = hex_color.lstrip("#")
        palette.append(tuple(int(h[i:i+2], 16) for i in (0, 2, 4)))
    return palette

# ── generation ─────────────────────────────────────────────────────────────────

def pick_traits(config, assets_dir="assets"):
    layer_order = config["layer_order"]
    rarity      = config.get("rarity", {})
    weights     = config.get("weights", {})
    chosen      = {}
    for layer in layer_order:
        layer_path = os.path.join(assets_dir, layer)
        if not os.path.isdir(layer_path):
            continue
        skip_chance = rarity.get(layer, {}).get("rarity", 0)
        if skip_chance > 0 and random.randint(1, 100) <= skip_chance:
            chosen[layer] = None
            continue
        options = [f for f in os.listdir(layer_path) if f.endswith(".png")]
        if not options:
            chosen[layer] = None
            continue
        layer_weights = weights.get(layer, {})
        w = [layer_weights.get(f, 10) for f in options]
        chosen[layer] = random.choices(options, weights=w, k=1)[0]
    return chosen

def composite(chosen, config, assets_dir="assets"):
    base = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for layer in config["layer_order"]:
        trait = chosen.get(layer)
        if not trait:
            continue
        path = os.path.join(assets_dir, layer, trait)
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            base = Image.alpha_composite(base, img)
    return base

def generate_nft_b64(config, size=160):
    chosen = pick_traits(config)
    img    = composite(chosen, config)
    img    = img.resize((size, size), Image.NEAREST)
    buf    = io.BytesIO()
    img.save(buf, format="PNG")
    b64    = base64.b64encode(buf.getvalue()).decode()
    traits = {k: (v.replace(".png","") if v else "none") for k,v in chosen.items()}
    return b64, traits

# ── routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/generate")
def api_generate():
    n      = int(request.args.get("n", 25))
    size   = int(request.args.get("size", 160))
    config = load_config()
    results = []
    for _ in range(n):
        b64, traits = generate_nft_b64(config, size)
        results.append({"img": b64, "traits": traits})
    return jsonify(results)

@app.route("/api/config")
def api_config():
    return jsonify(load_config())

@app.route("/api/rarity", methods=["POST"])
def api_rarity():
    data   = request.json
    config = load_config()
    for layer, value in data.items():
        if layer in config["rarity"]:
            config["rarity"][layer]["rarity"] = int(value)
    save_config(config)
    return jsonify({"ok": True})

@app.route("/api/weights", methods=["POST"])
def api_weights():
    data   = request.json          # { layer: { trait: weight } }
    config = load_config()
    for layer, traits in data.items():
        if layer not in config.get("weights", {}):
            config.setdefault("weights", {})[layer] = {}
        for trait, w in traits.items():
            config["weights"][layer][trait] = int(w)
    save_config(config)
    return jsonify({"ok": True})

# ── HTML ───────────────────────────────────────────────────────────────────────

HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ChizuBuds — Rarity Studio</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

  :root {
    --bg:       #0d0d0f;
    --surface:  #16161a;
    --border:   #2a2a32;
    --accent:   #e060a6;
    --accent2:  #9369db;
    --text:     #e6e3e5;
    --muted:    #5d5d68;
    --success:  #6bdb78;
    --panel-w:  320px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Space Mono', monospace;
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  /* ── sidebar ── */
  #sidebar {
    width: var(--panel-w);
    min-width: var(--panel-w);
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  #sidebar-header {
    padding: 20px 20px 14px;
    border-bottom: 1px solid var(--border);
  }

  #sidebar-header h1 {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 18px;
    letter-spacing: -0.5px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  #sidebar-header p {
    font-size: 10px;
    color: var(--muted);
    margin-top: 3px;
  }

  #sidebar-body {
    overflow-y: auto;
    flex: 1;
    padding: 16px;
  }

  #sidebar-body::-webkit-scrollbar { width: 4px; }
  #sidebar-body::-webkit-scrollbar-track { background: transparent; }
  #sidebar-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  /* controls */
  .section-title {
    font-family: 'Syne', sans-serif;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
    margin: 18px 0 10px;
  }

  .section-title:first-child { margin-top: 0; }

  .ctrl-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }

  .ctrl-row label {
    font-size: 10px;
    color: var(--text);
    width: 100px;
    flex-shrink: 0;
    text-transform: capitalize;
  }

  .ctrl-row input[type=range] {
    flex: 1;
    accent-color: var(--accent);
    height: 3px;
    cursor: pointer;
  }

  .ctrl-row .val {
    font-size: 10px;
    color: var(--accent);
    width: 28px;
    text-align: right;
    flex-shrink: 0;
  }

  .val-input {
    width: 42px;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--accent);
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    padding: 3px 5px;
    border-radius: 4px;
    outline: none;
    text-align: center;
    flex-shrink: 0;
  }

  .val-input:focus { border-color: var(--accent); }

  .ctrl-row select {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    padding: 4px 6px;
    border-radius: 4px;
    outline: none;
  }

  .ctrl-row input[type=number] {
    width: 52px;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    padding: 4px 6px;
    border-radius: 4px;
    outline: none;
    text-align: center;
  }

  /* trait weight accordion */
  .accordion {
    border: 1px solid var(--border);
    border-radius: 6px;
    margin-bottom: 6px;
    overflow: hidden;
  }

  .accordion-head {
    background: var(--bg);
    padding: 8px 12px;
    font-size: 10px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    user-select: none;
    transition: background 0.15s;
  }

  .accordion-head:hover { background: #1e1e24; }
  .accordion-head .arrow { transition: transform 0.2s; color: var(--muted); }
  .accordion-head.open .arrow { transform: rotate(90deg); }

  .accordion-body {
    display: none;
    padding: 10px 12px;
    background: var(--surface);
    border-top: 1px solid var(--border);
  }

  .accordion-body.open { display: block; }

  .trait-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 5px;
  }

  .trait-row label {
    font-size: 9px;
    color: var(--muted);
    width: 110px;
    flex-shrink: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .trait-row input[type=range] {
    flex: 1;
    accent-color: var(--accent2);
    cursor: pointer;
  }

  .trait-row .val {
    font-size: 9px;
    color: var(--accent2);
    width: 22px;
    text-align: right;
  }

  /* buttons */
  #sidebar-footer {
    padding: 14px 16px;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .btn {
    width: 100%;
    padding: 9px;
    border: none;
    border-radius: 6px;
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    cursor: pointer;
    font-weight: 700;
    letter-spacing: 0.5px;
    transition: opacity 0.15s, transform 0.1s;
  }

  .btn:active { transform: scale(0.98); }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-secondary { background: var(--border); color: var(--text); }
  .btn:hover { opacity: 0.88; }

  #save-status {
    font-size: 9px;
    text-align: center;
    color: var(--success);
    height: 14px;
    transition: opacity 0.3s;
  }

  /* ── main grid ── */
  #main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  #topbar {
    padding: 12px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 16px;
    background: var(--surface);
  }

  #topbar .tbl { font-size: 10px; color: var(--muted); }
  #topbar .tbl b { color: var(--text); }

  .toggle-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 10px;
    color: var(--muted);
    cursor: pointer;
    user-select: none;
  }

  .pill-switch {
    width: 32px; height: 16px;
    background: var(--border);
    border-radius: 8px;
    position: relative;
    transition: background 0.2s;
  }

  .pill-switch.on { background: var(--accent); }

  .pill-switch::after {
    content: '';
    position: absolute;
    width: 12px; height: 12px;
    background: white;
    border-radius: 50%;
    top: 2px; left: 2px;
    transition: left 0.2s;
  }

  .pill-switch.on::after { left: 18px; }

  #grid-wrap {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }

  #grid {
    display: grid;
    grid-template-columns: repeat(var(--cols, 5), 1fr);
    gap: 8px;
  }

  .nft-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    cursor: pointer;
    transition: border-color 0.15s, transform 0.15s;
    position: relative;
  }

  .nft-card:hover {
    border-color: var(--accent);
    transform: scale(1.03);
    z-index: 2;
  }

  .nft-card img {
    width: 100%;
    aspect-ratio: 1;
    display: block;
    image-rendering: pixelated;
  }

  /* tooltip */
.tooltip {
    display: none;
    position: fixed;
    background: rgba(0, 0, 0, 0.72);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 10px;
    line-height: 2;
    white-space: nowrap;
    z-index: 9999;
    pointer-events: none;
    color: var(--text);
    box-shadow: 0 4px 24px rgba(0,0,0,0.5);
  }

  /* spinner */
  #spinner {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(13,13,15,0.7);
    align-items: center;
    justify-content: center;
    z-index: 100;
    font-family: 'Syne', sans-serif;
    font-size: 14px;
    letter-spacing: 2px;
    color: var(--accent);
  }

  #spinner.show { display: flex; }

  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
  #spinner span { animation: pulse 1s infinite; }
</style>
</head>
<body>
<div id="global-tooltip" style="display:none;position:fixed;z-index:9999;font-family:'Space Mono',monospace;"></div>

<!-- ── SIDEBAR ── -->
<div id="sidebar">
  <div id="sidebar-header">
    <h1>RARITY STUDIO</h1>
    <p>ChizuBuds Art Generator</p>
  </div>

  <div id="sidebar-body">

    <!-- generation controls -->
    <div class="section-title">Generation</div>

    <div class="ctrl-row">
      <label>Count</label>
      <input type="number" id="ctrl-count" value="25" min="1" max="100">
    </div>

    <div class="ctrl-row">
      <label>Grid cols</label>
      <input type="number" id="ctrl-cols" value="5" min="2" max="20">
    </div>

    <div class="ctrl-row">
      <label>Image size</label>
      <select id="ctrl-size">
        <option value="96">96px (fast)</option>
        <option value="160" selected>160px</option>
        <option value="256">256px (slow)</option>
      </select>
    </div>

    <div class="ctrl-row">
      <label>Auto-refresh</label>
      <span class="toggle-pill" onclick="toggleAuto()">
        <span class="pill-switch" id="auto-pill"></span>
        <span id="auto-label">off</span>
      </span>
    </div>

    <div class="ctrl-row">
      <label>Interval (s)</label>
      <input type="number" id="ctrl-interval" value="2" min="1" max="30">
    </div>

    <!-- layer rarity -->
    <div class="section-title">Layer Rarity (skip %)</div>
    <div id="layer-controls"></div>

    <!-- trait weights -->
    <div class="section-title">Trait Weights</div>
    <div id="trait-controls"></div>

  </div>

  <div id="sidebar-footer">
    <div id="save-status"></div>
    <button class="btn btn-primary" onclick="saveAndRefresh()">SAVE + REFRESH</button>
    <button class="btn btn-secondary" onclick="fetchGrid()">REFRESH ONLY</button>
  </div>
</div>

<!-- ── MAIN ── -->
<div id="main">
  <div id="topbar">
    <div class="tbl">SHOWING <b id="lbl-count">—</b> GENERATIONS</div>
    <div class="tbl">LAST REFRESH <b id="lbl-time">—</b></div>
  </div>

  <div id="grid-wrap">
    <div id="grid"></div>
  </div>
</div>

<div id="spinner"><span>GENERATING...</span></div>

<script>
let autoTimer = null;
let autoOn    = false;
let config    = {};

// ── boot ──────────────────────────────────────────────────────────────────────
async function boot() {
  const res = await fetch("/api/config");
  config = await res.json();
  buildLayerControls();
  buildTraitControls();
  applyGridCols();
  fetchGrid();
}

// ── grid cols ─────────────────────────────────────────────────────────────────
function applyGridCols() {
  const cols = parseInt(document.getElementById("ctrl-cols").value) || 5;
  document.getElementById("grid").style.setProperty("--cols", cols);
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("ctrl-cols").addEventListener("input", applyGridCols);
});

// ── layer controls ────────────────────────────────────────────────────────────
function buildLayerControls() {
  const wrap   = document.getElementById("layer-controls");
  wrap.innerHTML = "";
  const rarity = config.rarity || {};

  for (const [layer, data] of Object.entries(rarity)) {
    const val = data.rarity ?? 0;
    const row = document.createElement("div");
    row.className = "ctrl-row";
    row.innerHTML = `
      <label>${layer}</label>
      <input type="range" min="0" max="100" value="${val}"
             id="r-${layer}"
             oninput="syncRarityVal('${layer}', this.value)">
      <input type="number" class="val-input" id="rv-${layer}" value="${val}" min="0" max="100"
             oninput="syncRaritySlider('${layer}', this.value)">
    `;
    wrap.appendChild(row);
  }
}

// ── trait weight accordion ────────────────────────────────────────────────────
function buildTraitControls() {
  const wrap    = document.getElementById("trait-controls");
  wrap.innerHTML = "";
  const weights = config.weights || {};

  for (const [layer, traits] of Object.entries(weights)) {
    const acc  = document.createElement("div");
    acc.className = "accordion";

    const head = document.createElement("div");
    head.className = "accordion-head";
    head.innerHTML = `<span>${layer}</span><span class="arrow">▶</span>`;
    head.onclick = () => {
      head.classList.toggle("open");
      body.classList.toggle("open");
    };

    const body = document.createElement("div");
    body.className = "accordion-body";

    for (const [trait, w] of Object.entries(traits)) {
      const name = trait.replace(".png","");
      const row  = document.createElement("div");
      row.className = "trait-row";
      row.innerHTML = `
        <label title="${name}">${name}</label>
        <input type="range" min="1" max="50" value="${w}"
               id="w-${layer}-${name}"
               oninput="document.getElementById('wv-${layer}-${name}').textContent=this.value">
        <span class="val" id="wv-${layer}-${name}">${w}</span>
      `;
      body.appendChild(row);
    }

    acc.appendChild(head);
    acc.appendChild(body);
    wrap.appendChild(acc);
  }
}

// ── fetch grid ────────────────────────────────────────────────────────────────
async function fetchGrid(silent=false) {
  const n    = parseInt(document.getElementById("ctrl-count").value) || 25;
  const size = parseInt(document.getElementById("ctrl-size").value)  || 160;

  if (!silent) document.getElementById("spinner").classList.add("show");

  try {
    const res  = await fetch(`/api/generate?n=${n}&size=${size}`);
    const data = await res.json();
    renderGrid(data);
    document.getElementById("lbl-count").textContent = data.length;
    document.getElementById("lbl-time").textContent  =
      new Date().toLocaleTimeString();
  } finally {
    document.getElementById("spinner").classList.remove("show");
  }
}

function renderGrid(data) {
  const grid = document.getElementById("grid");
  grid.innerHTML = "";
  const tip = document.getElementById("global-tooltip");

  for (const item of data) {
    const card = document.createElement("div");
    card.className = "nft-card";
    card.innerHTML = `<img src="data:image/png;base64,${item.img}" alt="">`;

    card.addEventListener("mouseenter", (e) => {
      const lines = Object.entries(item.traits)
        .map(([l, t]) => {
          const label = l.padEnd(14);
          const val   = t === "none"
            ? `<span style="color:var(--muted)">none</span>`
            : `<span style="color:var(--accent)">${t}</span>`;
          return `<div>${label}  ${val}</div>`;
        }).join("");
      tip.innerHTML = lines;
      tip.style.display = "block";
      positionTip(e);
    });

    card.addEventListener("mousemove", positionTip);

    card.addEventListener("mouseleave", () => {
      tip.style.display = "none";
    });

    grid.appendChild(card);
  }
}

function positionTip(e) {
  const tip = document.getElementById("global-tooltip");
  const pad = 14;
  let x = e.clientX + pad;
  let y = e.clientY + pad;
  const rect = tip.getBoundingClientRect();
  if (x + rect.width  > window.innerWidth)  x = e.clientX - rect.width  - pad;
  if (y + rect.height > window.innerHeight) y = e.clientY - rect.height - pad;
  tip.style.left = x + "px";
  tip.style.top  = y + "px";
}

// ── save ──────────────────────────────────────────────────────────────────────
async function saveRarity() {
  const rarity = {};
  for (const layer of Object.keys(config.rarity || {})) {
    const el = document.getElementById(`rv-${layer}`);
    if (el) rarity[layer] = el.value;
  }
  await fetch("/api/rarity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rarity)
  });
}

async function saveWeights() {
  const weights = {};
  for (const [layer, traits] of Object.entries(config.weights || {})) {
    weights[layer] = {};
    for (const trait of Object.keys(traits)) {
      const name = trait.replace(".png","");
      const el   = document.getElementById(`w-${layer}-${name}`);
      if (el) weights[layer][trait] = el.value;
    }
  }
  await fetch("/api/weights", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(weights)
  });
}

async function saveAndRefresh() {
  await saveRarity();
  await saveWeights();
  const status = document.getElementById("save-status");
  status.textContent = "✓ saved to config.json";
  setTimeout(() => status.textContent = "", 2000);
  fetchGrid();
}

// ── auto refresh ──────────────────────────────────────────────────────────────
function toggleAuto() {
  autoOn = !autoOn;
  const pill  = document.getElementById("auto-pill");
  const label = document.getElementById("auto-label");
  pill.classList.toggle("on", autoOn);
  label.textContent = autoOn ? "on" : "off";

  if (autoOn) {
    const secs = parseInt(document.getElementById("ctrl-interval").value) || 2;
    autoTimer  = setInterval(() => fetchGrid(true), secs * 1000);
  } else {
    clearInterval(autoTimer);
  }
}

// ── rarity sync ───────────────────────────────────────────────────────────────
function syncRarityVal(layer, value) {
  const num = document.getElementById(`rv-${layer}`);
  if (num) num.value = value;
}

function syncRaritySlider(layer, value) {
  const v = Math.max(0, Math.min(100, parseInt(value) || 0));
  const slider = document.getElementById(`r-${layer}`);
  if (slider) slider.value = v;
}

boot();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("\n  ChizuBuds Rarity Studio")
    print("  Open http://localhost:5000 in your browser\n")
    app.run(debug=False, port=5000)