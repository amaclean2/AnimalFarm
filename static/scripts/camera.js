import {
  CELL_DESKTOP,
  CELL_MOBILE,
  WORLD_WIDTH,
  WORLD_HEIGHT,
  SCROLL_SPEED,
} from "./constants.js";

const canvas = document.getElementById("game");
const panel = document.getElementById("panel");
const mobileQuery = window.matchMedia("(max-width: 600px)");

export const camera = { x: 0, y: 0 };
export const viewport = {
  cellSize: mobileQuery.matches ? CELL_MOBILE : CELL_DESKTOP,
};

const pressedKeys = new Set();

export const centerOnWorld = (worldX, worldY) => {
  camera.x =
    worldX * viewport.cellSize + viewport.cellSize / 2 - canvas.width / 2;
  camera.y =
    worldY * viewport.cellSize + viewport.cellSize / 2 - canvas.height / 2;
  clampCamera();
};

export const clampCamera = () => {
  camera.x = Math.max(
    0,
    Math.min(
      Math.max(0, WORLD_WIDTH * viewport.cellSize - canvas.width),
      camera.x,
    ),
  );
  camera.y = Math.max(
    0,
    Math.min(
      Math.max(0, WORLD_HEIGHT * viewport.cellSize - canvas.height),
      camera.y,
    ),
  );
};

export const resize = () => {
  const panelBottom = mobileQuery.matches
    ? Math.round(panel.getBoundingClientRect().bottom) + 8
    : 0;
  canvas.style.marginTop = panelBottom + "px";
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight - panelBottom;
};

export const scrollCamera = (deltaTime) => {
  if (pressedKeys.has("ArrowLeft") || pressedKeys.has("a"))
    camera.x -= SCROLL_SPEED * deltaTime;
  if (pressedKeys.has("ArrowRight") || pressedKeys.has("d"))
    camera.x += SCROLL_SPEED * deltaTime;
  if (pressedKeys.has("ArrowUp") || pressedKeys.has("w"))
    camera.y -= SCROLL_SPEED * deltaTime;
  if (pressedKeys.has("ArrowDown") || pressedKeys.has("s"))
    camera.y += SCROLL_SPEED * deltaTime;
  clampCamera();
};

window.addEventListener("keydown", (event) => {
  if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) {
    event.preventDefault();
  }
  pressedKeys.add(event.key);
});

window.addEventListener("keyup", (event) => pressedKeys.delete(event.key));

const LINE_HEIGHT = 16;
const CELL_MAX = 80;

const cellMin = () =>
  Math.max(canvas.width / WORLD_WIDTH, canvas.height / WORLD_HEIGHT);

const zoomToward = (screenX, screenY, newCellSize) => {
  const clamped = Math.max(cellMin(), Math.min(CELL_MAX, newCellSize));
  const worldX = (camera.x + screenX) / viewport.cellSize;
  const worldY = (camera.y + screenY) / viewport.cellSize;
  viewport.cellSize = clamped;
  camera.x = worldX * clamped - screenX;
  camera.y = worldY * clamped - screenY;
  clampCamera();
};

canvas.addEventListener(
  "wheel",
  (event) => {
    event.preventDefault();

    if (event.ctrlKey) {
      const rect = canvas.getBoundingClientRect();
      zoomToward(
        event.clientX - rect.left,
        event.clientY - rect.top,
        viewport.cellSize * (1 - event.deltaY * 0.02),
      );
      return;
    }

    const scale =
      event.deltaMode === 1
        ? LINE_HEIGHT
        : event.deltaMode === 2
          ? canvas.height
          : 1;
    camera.x += event.deltaX * scale;
    camera.y += event.deltaY * scale;
    clampCamera();
  },
  { passive: false },
);

let _pinchDist = null;
let _pinchCellSize = null;

const pinchDist = (t1, t2) => {
  const dx = t1.clientX - t2.clientX;
  const dy = t1.clientY - t2.clientY;
  return Math.sqrt(dx * dx + dy * dy);
};

canvas.addEventListener(
  "touchstart",
  (event) => {
    if (event.touches.length !== 2) return;
    _pinchDist = pinchDist(event.touches[0], event.touches[1]);
    _pinchCellSize = viewport.cellSize;
  },
  { passive: true },
);

canvas.addEventListener(
  "touchmove",
  (event) => {
    if (event.touches.length !== 2 || _pinchDist === null) return;
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const midX =
      (event.touches[0].clientX + event.touches[1].clientX) / 2 - rect.left;
    const midY =
      (event.touches[0].clientY + event.touches[1].clientY) / 2 - rect.top;
    const dist = pinchDist(event.touches[0], event.touches[1]);
    zoomToward(midX, midY, _pinchCellSize * (dist / _pinchDist));
  },
  { passive: false },
);

const resetPinch = () => {
  _pinchDist = null;
};
canvas.addEventListener("touchend", resetPinch);
canvas.addEventListener("touchcancel", resetPinch);
