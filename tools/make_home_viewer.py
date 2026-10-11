"""Génère HomeKit/Viewer/index.html (visualiseur 3D autonome basé sur <model-viewer>) à partir de views.json."""
import json, os
root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "HomeKit")
views = json.load(open(os.path.join(root, "Scenes", "views.json")))
scenes = {
    "showroom": {"label": "Showroom — all 89 assets", "src": "../Scenes/Showroom.glb", "views": views["showroom"]["views"]},
    "place": {"label": "Example house — exterior, interior, living room", "src": "../Scenes/Example_Place.glb", "views": views["place"]["views"]},
}
html = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Home Builder Kit — 3D preview</title>
<script type="module" src="model-viewer.min.js"></script>
<style>
  :root { --bg:#eef0f3; --ink:#1d2330; --muted:#5b6475; --card:#ffffff; --line:#d9dde4; --accent:#2f6fed; }
  @media (prefers-color-scheme: dark) { :root { --bg:#12151b; --ink:#e9ecf2; --muted:#9aa3b2; --card:#1b2029; --line:#2a3140; --accent:#6c9bff; } }
  * { box-sizing: border-box; }
  html, body { margin:0; height:100%; background:var(--bg); color:var(--ink); font:15px/1.4 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  .app { display:grid; grid-template-rows:auto 1fr auto; height:100%; max-width:1500px; margin:0 auto; padding:12px 16px 12px; gap:10px; }
  header { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:8px 16px; }
  h1 { font-size:18px; margin:0; letter-spacing:.2px; }
  .tabs, .views { display:flex; flex-wrap:wrap; gap:6px; }
  button { font:inherit; color:var(--ink); background:var(--card); border:1px solid var(--line); border-radius:8px; padding:7px 12px; cursor:pointer; }
  button:hover { border-color:var(--accent); }
  button[aria-pressed="true"] { background:var(--accent); border-color:var(--accent); color:#fff; }
  .stage { position:relative; min-height:320px; border:1px solid var(--line); border-radius:12px; overflow:hidden; background:var(--card); }
  model-viewer { width:100%; height:100%; --poster-color:transparent; background:linear-gradient(#cfd8e6, #f4f6fa 60%); }
  @media (prefers-color-scheme: dark) { model-viewer { background:linear-gradient(#232a38, #11151c 70%); } }
  .bar { position:absolute; left:0; right:0; bottom:0; height:3px; background:transparent; }
  .bar > i { display:block; height:100%; width:0; background:var(--accent); transition:width .15s; }
  .hint { color:var(--muted); font-size:13px; }
  .badge { position:absolute; left:12px; top:10px; padding:4px 10px; border-radius:999px; background:rgba(0,0,0,.55); color:#fff; font-size:12px; pointer-events:none; }
</style>
</head>
<body>
<div class="app">
  <header>
    <h1>Home Builder Kit <span class="hint">· 3D preview</span></h1>
    <div class="tabs" id="tabs" role="tablist"></div>
  </header>
  <div class="stage">
    <model-viewer id="mv" camera-controls touch-action="pan-y" interaction-prompt="none" shadow-intensity="1.1" shadow-softness="0.8"
      exposure="1.05" environment-image="neutral" min-camera-orbit="auto 5deg 2m" max-camera-orbit="auto 88deg 400m"
      min-field-of-view="10deg" max-field-of-view="60deg" field-of-view="38deg" loading="eager" alt="Home Builder Kit 3D scene"></model-viewer>
    <div class="badge" id="badge">Loading…</div>
    <div class="bar"><i id="prog"></i></div>
  </div>
  <footer>
    <div class="views" id="views"></div>
    <div class="hint" style="margin-top:6px">Drag to orbit · scroll or pinch to zoom · right-drag or two fingers to pan</div>
  </footer>
</div>
<script>
const SCENES = __SCENES__;
const mv = document.getElementById("mv"), tabs = document.getElementById("tabs"), viewsEl = document.getElementById("views");
const badge = document.getElementById("badge"), prog = document.getElementById("prog");
let current = null;
function goto(v) {
  const [az, polar, r] = v.orbit;
  mv.cameraTarget = v.target.map(n => n + "m").join(" ");
  mv.cameraOrbit = az + "deg " + polar + "deg " + r + "m";
  mv.jumpCameraToGoal ? 0 : 0;
  badge.textContent = v.label;
  [...viewsEl.children].forEach(b => b.setAttribute("aria-pressed", b.dataset.id === v.id));
}
function load(key) {
  current = SCENES[key];
  [...tabs.children].forEach(b => b.setAttribute("aria-pressed", b.dataset.key === key));
  badge.textContent = "Loading…"; prog.style.width = "0";
  mv.src = current.src;
  viewsEl.innerHTML = "";
  current.views.forEach(v => {
    const b = document.createElement("button");
    b.textContent = v.label; b.dataset.id = v.id; b.setAttribute("aria-pressed", "false");
    b.onclick = () => goto(v);
    viewsEl.appendChild(b);
  });
  mv.addEventListener("load", () => goto(current.views[0]), { once: true });
}
Object.entries(SCENES).forEach(([key, s]) => {
  const b = document.createElement("button");
  b.textContent = s.label; b.dataset.key = key; b.setAttribute("aria-pressed", "false");
  b.onclick = () => load(key);
  tabs.appendChild(b);
});
mv.addEventListener("progress", e => { prog.style.width = Math.round(e.detail.totalProgress * 100) + "%"; });
load(new URLSearchParams(location.search).get("scene") === "place" ? "place" : "showroom");
</script>
</body>
</html>
'''.replace("__SCENES__", json.dumps(scenes))
open(os.path.join(root, "Viewer", "index.html"), "w", encoding="utf-8").write(html)
print("viewer OK")
