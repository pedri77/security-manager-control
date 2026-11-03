// Visor SMC (codigo propio). Lee SOLO el JSON smc-mapa/1 embebido. Todo texto del JSON entra al DOM con textContent.
// Patron de teardown (ADR-003): un modelo unico, un boton por zona, paneles con numeros reales, vistas de camara,
// visita automatica que cede el control al primer gesto. Sin codigo copiado de la skill.
const DATA = JSON.parse(document.getElementById("smc-data").textContent);
const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const COLORES = { rojo: 0xe5484d, ambar: 0xf5a524, gris: 0x8b949e, verde: 0x30a46c };
const ORDEN = ["rojo", "ambar", "gris", "verde"];
const ETIQ = { rojo: "ROJO", ambar: "ÁMBAR", gris: "GRIS (no se sabe)", verde: "VERDE" };
// Un valor desconocido NUNCA es verde: cae en gris.
const sem = (s) => (typeof s === "string" && ORDEN.includes(s) ? s : "gris");
const $ = (id) => document.getElementById(id);
const el = (tag, texto, cls) => { const e = document.createElement(tag); if (texto != null) e.textContent = String(texto); if (cls) e.className = cls; return e; };

const zonas = DATA.zonas.map((z) => ({ ...z, sin: false }));
if (DATA.sin_zona.length) zonas.push({ id: "sin_zona", nombre: "Sin zona", semaforo: "gris", n_dispositivos: DATA.sin_zona.length, dispositivos: DATA.sin_zona, sin: true });

// ---------- escena ----------
const cont = $("escena");
let renderer = null;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true, canvas: $("lienzo") });
} catch (e) {
  $("sin-webgl").hidden = false;
}
const PASO = 11, LADO = 9, COLS = 4;
const pos = (i, sin) => (sin ? { x: 0, z: 14 } : { x: (i % COLS - 1.5) * PASO, z: (Math.floor(i / COLS) - 0.5) * PASO });
const piezas = []; // {mesh, d, zi, base}
const plataformas = []; // {mesh, borde, zi}
const raiz = renderer ? new THREE.Group() : null;
const scene = renderer ? new THREE.Scene() : null;
const camera = renderer ? new THREE.PerspectiveCamera(45, 16 / 9, 0.1, 500) : null;

function etiqueta(texto, escala) {
  const c = document.createElement("canvas"); c.width = 512; c.height = 96;
  const g = c.getContext("2d"); g.font = "600 44px system-ui, sans-serif"; g.fillStyle = "#e6edf3"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(String(texto).slice(0, 28), 256, 48); // fillText no interpreta HTML
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthTest: false }));
  s.scale.set(escala * 5.33, escala, 1); s.renderOrder = 10; return s;
}
function geoTipo(tipo) {
  const t = String(tipo || "").toLowerCase();
  if (t.includes("servidor")) return new THREE.CylinderGeometry(0.7, 0.7, 1.4, 20);
  if (t.includes("ot") || t.includes("iot")) return new THREE.OctahedronGeometry(0.9);
  if (t.includes("puesto") || t.includes("endpoint")) return new THREE.BoxGeometry(1, 0.7, 1);
  if (t.includes("red")) return new THREE.BoxGeometry(1.6, 0.5, 0.9);
  return new THREE.SphereGeometry(0.8, 18, 14);
}
function colocar(d, zi, k, n, sin) {
  const p = pos(zi, sin); const cols = Math.max(1, Math.ceil(Math.sqrt(n)));
  const sep = (LADO - 2) / cols;
  return { x: p.x + ((k % cols) - (cols - 1) / 2) * sep, z: p.z + (Math.floor(k / cols) - (Math.ceil(n / cols) - 1) / 2) * sep };
}
const capaY = (c) => (Number.isInteger(c) ? 1 + c * 2.2 : -2.5); // capa desconocida: franja aparte, debajo

if (renderer) {
  scene.background = new THREE.Color(0x0d1117);
  scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const sol = new THREE.DirectionalLight(0xffffff, 1.1); sol.position.set(20, 40, 15); scene.add(sol);
  scene.add(raiz);
  zonas.forEach((z, zi) => {
    const p = pos(zi, z.sin);
    const m = new THREE.Mesh(new THREE.BoxGeometry(LADO, 0.5, LADO), new THREE.MeshLambertMaterial({ color: 0x2d3846, transparent: true }));
    m.position.set(p.x, -0.25, p.z);
    const borde = new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry), new THREE.LineBasicMaterial({ color: COLORES[sem(z.semaforo)], transparent: true }));
    borde.position.copy(m.position);
    const et = etiqueta(z.nombre, 1.9); et.position.set(p.x, 0.3, p.z + LADO / 2 + 0.9);
    raiz.add(m, borde, et);
    plataformas.push({ mesh: m, borde, et, zi });
    z.dispositivos.forEach((d, k) => {
      const c = colocar(d, zi, k, z.dispositivos.length, z.sin);
      const mesh = new THREE.Mesh(geoTipo(d.tipo), new THREE.MeshLambertMaterial({ color: COLORES[sem(d.semaforo)], transparent: true }));
      mesh.position.set(c.x, 1.1, c.z); mesh.userData = { d, zi };
      raiz.add(mesh);
      piezas.push({ mesh, d, zi, x: c.x, z: c.z, zy: 1.1 });
    });
  });
}

// ---------- estado de vista ----------
const vista = { zona: null, modo: "general", nombre: "general", soloRojos: false };
const cam = { theta: 0.6, phi: 1.0, r: 41, tx: 0, ty: 0, tz: 3 };
const VISTAS = {
  general: () => ({ theta: 0.6, phi: 1.0, r: 41, tx: 0, ty: 0, tz: 3 }),
  planta: () => ({ theta: 0, phi: 0.05, r: 42, tx: 0, ty: 0, tz: 4 }),
  capas: () => ({ theta: 0.9, phi: 1.2, r: 44, tx: 0, ty: 6, tz: 4 }),
};
function aplicarCam() {
  if (!renderer) return;
  const sp = Math.sin(cam.phi), x = cam.tx + cam.r * sp * Math.sin(cam.theta), z = cam.tz + cam.r * sp * Math.cos(cam.theta), y = cam.ty + cam.r * Math.cos(cam.phi);
  camera.position.set(x, y, z); camera.lookAt(cam.tx, cam.ty, cam.tz);
}
let anim = null;
function irA(dest) {
  if (REDUCED) { Object.assign(cam, dest); aplicarCam(); dibujar(); return; }
  const a = { ...cam }; const t0 = performance.now(); const dur = 900;
  anim = (t) => {
    const k = Math.min(1, (t - t0) / dur), e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    for (const c of Object.keys(dest)) cam[c] = a[c] + (dest[c] - a[c]) * e;
    aplicarCam(); dibujar();
    if (k >= 1) anim = null;
  };
  bucle();
}
let pidiendo = false;
function bucle() { if (pidiendo) return; pidiendo = true; requestAnimationFrame(function paso(t) { if (anim) anim(t); dibujar(); if (anim) requestAnimationFrame(paso); else pidiendo = false; }); }
function dibujar() { if (renderer) renderer.render(scene, camera); }

function aplicarModelo() {
  if (!renderer) return;
  piezas.forEach((p) => {
    const enCapas = vista.modo === "capas";
    p.mesh.position.set(p.x, enCapas ? capaY(p.d.capa_osi) : p.zy, p.z);
    const zonaOk = vista.zona == null || vista.zona === p.zi;
    const rojoOk = !vista.soloRojos || sem(p.d.semaforo) === "rojo";
    p.mesh.visible = zonaOk && rojoOk;
    p.mesh.material.opacity = 1;
  });
  plataformas.forEach((pl) => {
    const op = vista.modo === "capas" ? 0.12 : vista.zona == null || vista.zona === pl.zi ? 1 : 0.2;
    pl.mesh.material.opacity = op; pl.borde.material.opacity = op; pl.et.material.opacity = op;
  });
  document.querySelectorAll("[data-zona]").forEach((b) => b.setAttribute("aria-pressed", String(String(vista.zona) === b.dataset.zona)));
  document.querySelectorAll("[data-vista]").forEach((b) => b.setAttribute("aria-pressed", String(vista.zona == null && vista.nombre === b.dataset.vista)));
  $("b-rojos").setAttribute("aria-pressed", String(vista.soloRojos));
  dibujar();
}

// ---------- panel (numeros leidos del JSON) ----------
function fila(dl, k, v) { dl.append(el("dt", k), el("dd", v)); }
function panelDispositivo(d) {
  const r = d.reglas || {}, v = d.vulnerabilidades || {};
  const caja = el("section", null, "disp");
  const h = el("h4", null); h.append(el("span", "●", "pt " + sem(d.semaforo)), document.createTextNode(" " + d.nombre + " (" + d.id + ")"));
  caja.append(h);
  const dl = el("dl");
  fila(dl, "Semáforo", ETIQ[sem(d.semaforo)]);
  fila(dl, "Tipo / capa OSI", d.tipo + " / " + (d.capa_osi == null ? "desconocida" : d.capa_osi));
  fila(dl, "Vertical", d.vertical || "—");
  fila(dl, "Reglas", r.estado === "no_evaluable" ? "No evaluable (candado): " + r.motivo : r.estado + (r.n_reglas != null ? " · " + r.n_reglas + " reglas · any-any " + r.reglas_any_any + " · sin uso " + r.reglas_sin_uso : ""));
  fila(dl, "Vulnerabilidades", "abiertas " + v.abiertas + " · fuera de SLA " + v.fuera_sla + " · KEV fuera de SLA " + v.kev_fuera_sla + (v.cves_fuera_sla && v.cves_fuera_sla.length ? " · " + v.cves_fuera_sla.join(", ") : ""));
  fila(dl, "Motivos", (d.semaforo_motivos || []).join("; "));
  if (d.motivo_sin_zona) fila(dl, "Sin zona", d.motivo_sin_zona);
  caja.append(dl);
  return caja;
}
function mostrarPanel(sel) {
  const p = $("panel"); p.replaceChildren();
  if (sel && sel.disp) { p.append(el("h3", "Dispositivo"), panelDispositivo(sel.disp)); return; }
  const R = DATA.resumen;
  if (sel && sel.zona != null) {
    const z = zonas[sel.zona];
    p.append(el("h3", z.nombre));
    const dl = el("dl"); fila(dl, "Semáforo de la zona", ETIQ[sem(z.semaforo)]); fila(dl, "Dispositivos", z.n_dispositivos); p.append(dl);
    z.dispositivos.forEach((d) => { if (!vista.soloRojos || sem(d.semaforo) === "rojo") p.append(panelDispositivo(d)); });
    return;
  }
  p.append(el("h3", "Resumen del mapa"));
  const dl = el("dl");
  fila(dl, "Generado para", DATA.generado_para);
  fila(dl, "Dispositivos", R.dispositivos + " (sin zona: " + R.sin_zona + ")");
  fila(dl, "Rojo / ámbar / gris / verde", ORDEN.map((s) => R.por_semaforo[s]).join(" / "));
  fila(dl, "Reglas no evaluables", R.reglas_no_evaluables);
  fila(dl, "Vulnerabilidades abiertas", R.vulnerabilidades_abiertas);
  fila(dl, "Fuera de SLA", R.vulnerabilidades_fuera_sla);
  fila(dl, "Madurez media de verticales", R.madurez_verticales_media == null ? "sin evaluación" : R.madurez_verticales_media);
  p.append(dl);
  const todos = zonas.flatMap((z) => z.dispositivos);
  const noev = todos.filter((d) => d.reglas && d.reglas.estado === "no_evaluable");
  if (noev.length) { p.append(el("h4", "Reglas no evaluables (motivo)")); const ul = el("ul"); noev.forEach((d) => ul.append(el("li", d.nombre + ": " + d.reglas.motivo))); p.append(ul); }
  const kev = todos.filter((d) => d.vulnerabilidades && d.vulnerabilidades.kev_fuera_sla > 0);
  if (kev.length) { p.append(el("h4", "KEV fuera de SLA")); const ul = el("ul"); kev.forEach((d) => ul.append(el("li", d.nombre + ": " + d.vulnerabilidades.kev_fuera_sla))); p.append(ul); }
  if (DATA.avisos.length) { p.append(el("h4", "Avisos")); const ul = el("ul"); DATA.avisos.forEach((a) => ul.append(el("li", a))); p.append(ul); }
}

// ---------- acciones ----------
function abrirZona(zi) {
  vista.zona = zi; vista.nombre = zi == null ? vista.nombre : "zona";
  mostrarPanel(zi == null ? null : { zona: zi });
  if (zi == null) { irA(vista.modo === "capas" ? VISTAS.capas() : VISTAS.general()); }
  else { const p = pos(zi, zonas[zi].sin); irA({ theta: 0.5, phi: 0.95, r: 20, tx: p.x, ty: 0, tz: p.z }); }
  aplicarModelo();
}
function cambiarVista(nombre) {
  vista.modo = nombre === "capas" ? "capas" : "general"; vista.nombre = nombre; vista.zona = null;
  mostrarPanel(null); irA(VISTAS[nombre]()); aplicarModelo();
}
const gestos = ["pointerdown", "wheel", "keydown"];
// ---------- visita ----------
let visita = { activa: false, i: 0, timer: null, calma: null };
const orden = zonas.map((z, i) => i).filter((i) => zonas[i].dispositivos.length).sort((a, b) => ORDEN.indexOf(sem(zonas[a].semaforo)) - ORDEN.indexOf(sem(zonas[b].semaforo)));
function paso() {
  if (!visita.activa || !orden.length) return;
  abrirZona(orden[visita.i % orden.length]); visita.i++;
  visita.timer = setTimeout(paso, 6000);
}
function iniciarVisita() {
  if (REDUCED || !renderer) return;
  visita.activa = true; visita.i = 0; clearTimeout(visita.calma); clearTimeout(visita.timer);
  $("b-visita").setAttribute("aria-pressed", "true"); paso();
}
function pararVisita(esperaCalma) {
  visita.activa = false; clearTimeout(visita.timer); clearTimeout(visita.calma); visita.calma = null;
  $("b-visita").setAttribute("aria-pressed", "false");
  if (esperaCalma && !REDUCED) visita.calma = setTimeout(() => { cambiarVista("general"); iniciarVisita(); }, 25000);
}
// Cualquier gesto del usuario cede el control; 25 s de calma devuelven la visita.
gestos.forEach((g) => window.addEventListener(g, (e) => {
  if (!e.isTrusted || (e.target && e.target.id === "b-visita")) return;
  if (visita.activa || visita.calma) pararVisita(true);
}, true));

// ---------- botones ----------
const barra = $("zonas");
const bT = el("button", "Todas las zonas"); bT.type = "button"; bT.dataset.zona = "null"; bT.addEventListener("click", () => abrirZona(null)); barra.append(bT);
zonas.forEach((z, i) => {
  const b = el("button", null); b.type = "button"; b.dataset.zona = String(i);
  b.append(el("span", "●", "pt " + sem(z.semaforo)), document.createTextNode(" " + z.nombre + " (" + z.n_dispositivos + ")"));
  b.addEventListener("click", () => abrirZona(i)); barra.append(b);
});
document.querySelectorAll("[data-vista]").forEach((b) => b.addEventListener("click", () => cambiarVista(b.dataset.vista)));
$("b-rojos").addEventListener("click", () => { vista.soloRojos = !vista.soloRojos; mostrarPanel(vista.zona == null ? null : { zona: vista.zona }); aplicarModelo(); });
$("b-visita").addEventListener("click", () => { if (visita.activa) pararVisita(false); else iniciarVisita(); });

// ---------- raton: orbita, zoom, seleccion ----------
if (renderer) {
  const lienzo = $("lienzo"); const rc = new THREE.Raycaster(); const v2 = new THREE.Vector2();
  let arr = null;
  lienzo.addEventListener("pointerdown", (e) => { arr = { x: e.clientX, y: e.clientY, mov: false }; lienzo.setPointerCapture(e.pointerId); });
  lienzo.addEventListener("pointermove", (e) => {
    if (!arr) return; const dx = e.clientX - arr.x, dy = e.clientY - arr.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) arr.mov = true;
    if (arr.mov) { cam.theta -= dx * 0.006; cam.phi = Math.min(1.5, Math.max(0.05, cam.phi - dy * 0.006)); arr.x = e.clientX; arr.y = e.clientY; aplicarCam(); dibujar(); }
  });
  lienzo.addEventListener("pointerup", (e) => {
    if (arr && !arr.mov) {
      const r = lienzo.getBoundingClientRect(); v2.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      rc.setFromCamera(v2, camera);
      const hit = rc.intersectObjects(piezas.filter((p) => p.mesh.visible).map((p) => p.mesh))[0];
      if (hit) mostrarPanel({ disp: hit.object.userData.d });
    }
    arr = null;
  });
  lienzo.addEventListener("wheel", (e) => { e.preventDefault(); cam.r = Math.min(120, Math.max(8, cam.r * (1 + Math.sign(e.deltaY) * 0.1))); aplicarCam(); dibujar(); }, { passive: false });
  lienzo.addEventListener("keydown", (e) => {
    const k = { ArrowLeft: [-0.1, 0], ArrowRight: [0.1, 0], ArrowUp: [0, -0.1], ArrowDown: [0, 0.1] }[e.key];
    if (k) { e.preventDefault(); cam.theta += k[0]; cam.phi = Math.min(1.5, Math.max(0.05, cam.phi + k[1])); aplicarCam(); dibujar(); }
    if (e.key === "+" || e.key === "=") { cam.r = Math.max(8, cam.r * 0.9); aplicarCam(); dibujar(); }
    if (e.key === "-") { cam.r = Math.min(120, cam.r * 1.1); aplicarCam(); dibujar(); }
  });
  function ajustar() {
    const w = cont.clientWidth || 800, h = cont.clientHeight || 450;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)); renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix(); aplicarCam(); dibujar();
  }
  window.addEventListener("resize", ajustar);
  ajustar();
}
mostrarPanel(null);
Object.assign(cam, VISTAS.general());
aplicarCam(); aplicarModelo();
document.documentElement.dataset.listo = renderer ? "3d" : "texto";
if (!REDUCED) iniciarVisita();
