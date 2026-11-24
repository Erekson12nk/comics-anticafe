// Редактор карты заведения: перетаскивание комнат и сохранение на сервер.
const NS = "http://www.w3.org/2000/svg";
const svg = document.getElementById("editor");
const rooms = JSON.parse(document.getElementById("rooms-data").textContent);
const props = document.getElementById("props");
let selected = null;

function toSvg(evt) {
  const pt = svg.createSVGPoint();
  pt.x = evt.clientX; pt.y = evt.clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

function draw() {
  svg.querySelectorAll("g").forEach(g => g.remove());
  rooms.forEach(room => {
    const g = document.createElementNS(NS, "g");
    g.style.cursor = "move";
    const r = document.createElementNS(NS, "rect");
    Object.entries({x: room.x, y: room.y, width: room.width, height: room.height, rx: 14,
      fill: room.color, "fill-opacity": .2, stroke: room.color,
      "stroke-width": room === selected ? 6 : 3}).forEach(([k, v]) => r.setAttribute(k, v));
    const t = document.createElementNS(NS, "text");
    t.setAttribute("x", room.x + 12); t.setAttribute("y", room.y + 28);
    t.setAttribute("font-size", 20); t.setAttribute("font-weight", 700);
    t.textContent = room.name;
    g.append(r, t);
    g.addEventListener("pointerdown", e => startDrag(e, room));
    svg.append(g);
  });
}

function startDrag(evt, room) {
  selected = room;
  showProps();
  const start = toSvg(evt), ox = room.x, oy = room.y;
  const move = e => {
    const p = toSvg(e);
    room.x = Math.max(0, Math.min(1000 - room.width, Math.round(ox + p.x - start.x)));
    room.y = Math.max(0, Math.min(600 - room.height, Math.round(oy + p.y - start.y)));
    draw();
  };
  const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", up);
  draw();
}

function showProps() {
  props.innerHTML = `
    <label class="form-label small">Название</label><input class="form-control mb-2" data-k="name">
    <div class="row g-2"><div class="col-6"><label class="form-label small">Ширина</label><input type="number" class="form-control" data-k="width" value="${selected.width}"></div>
    <div class="col-6"><label class="form-label small">Высота</label><input type="number" class="form-control" data-k="height" value="${selected.height}"></div></div>
    <label class="form-label small mt-2">Цвет</label><input type="color" class="form-control form-control-color" data-k="color" value="${selected.color}">`;
  props.querySelector("[data-k=name]").value = selected.name;
  props.querySelectorAll("input").forEach(inp => inp.addEventListener("input", () => {
    const k = inp.dataset.k;
    selected[k] = (k === "width" || k === "height") ? Math.max(40, +inp.value || 40) : inp.value;
    draw();
  }));
}

document.getElementById("save").addEventListener("click", async () => {
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]").value;
  const resp = await fetch(location.href, {method: "POST", headers: {"X-CSRFToken": csrf, "Content-Type": "application/json"},
    body: JSON.stringify({rooms})});
  document.getElementById("saved").textContent = resp.ok ? "Сохранено ✔" : "Ошибка сохранения";
});

draw();
