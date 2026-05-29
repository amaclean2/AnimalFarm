# World Viewer

An interactive 3D world preview tool, separate from the simulation, for generating and saving worlds before running a game.

---

## Phase 1 — 3D Viewer

### Entry point

A **Generate World** button appears below **Start Game** in the main UI. Clicking it opens `/world-viewer` in a new browser tab.

### What it shows

The viewer uses **Three.js** to render the world as a 3D scene with orbit controls (pan, zoom, rotate).

| Layer | Rendering |
|---|---|
| Terrain | `PlaneGeometry(100, 100, 99, 99)` with vertex Y-positions displaced by the elevation array. Colored by elevation (low → green, high → grey/white). |
| Rivers | River tiles overlaid on the terrain surface as blue geometry — either a flat mesh offset slightly above the terrain, or vertex coloring. |
| Food | Small instanced green billboards at each food position, sitting on the terrain surface. |
| Clouds | Translucent white spheres floating above the terrain at a fixed altitude, sized and positioned from the cloud data (`cx`, `cy`, `radius`, `strength`). |

### Data source

On load, the viewer calls `GET /world/preview` which generates a fresh world using current defaults and returns:

```json
{
  "width": 100,
  "height": 100,
  "seed": 482910,
  "elevation": [...],
  "rivers": [{ "river_id": "...", "tiles": [[x, y], ...] }],
  "food": [{ "x": 12, "y": 34 }, ...],
  "clouds": [{ "cx": 40.2, "cy": 55.1, "radius": 12.0, "strength": 0.8 }]
}
```

This endpoint generates a world in isolation — it does not touch the running simulation or the game world.

---

## Phase 2 — Control Panel

A collapsible sidebar in the viewer exposes sliders for world generation parameters:

| Slider | Config key | Range |
|---|---|---|
| Seed | `seed` | 0 – 999999 (also a "Randomize" button) |
| Springs | `num_springs` | 1 – 8 |
| Food clusters | `num_food_clusters` | 1 – 10 |
| Food abundance | `food_peak_probability` | 0.05 – 0.5 |
| Elevation coarseness | `elevation_coarse_scale` | 10 – 80 |

**Generate** re-calls `POST /world/preview` with the current slider values and re-renders the scene in place.

**Save World** calls `POST /world/save` with the config and seed. A small name input lets the user label the world (defaults to "World N").

---

## Phase 3 — Load Saved World

### Saved world storage

Worlds are saved as JSON files in `worlds/` at the project root. Each file stores the config and seed (not the full tile data — the world is regenerated deterministically at load time).

```json
{
  "id": "a3f9...",
  "name": "World 1",
  "created_at": "2026-05-29T14:00:00",
  "seed": 482910,
  "config": {
    "num_springs": 3,
    "num_food_clusters": 4,
    "food_peak_probability": 0.2
  }
}
```

### New API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/world/preview` | Generate world from defaults, return tile data |
| `POST` | `/world/preview` | Generate world from provided config, return tile data |
| `POST` | `/world/save` | Save current world config + seed to `worlds/` |
| `GET` | `/world/saved` | List all saved worlds (id, name, created_at) |
| `DELETE` | `/world/saved/{id}` | Delete a saved world |

### Starting from a saved world

The **Start Game** config panel gains a **Load World** dropdown populated from `GET /world/saved`. If a world is selected, `POST /start` accepts an optional `world_id`; the server loads that world's seed and config overrides before running the usual setup, skipping random seed generation.

---

## Implementation order

1. `GET /world/preview` endpoint + `POST /world/preview`
2. `/world-viewer` static page with Three.js terrain + river + food + cloud rendering
3. Control panel sliders wired to `POST /world/preview`
4. Save/load endpoints and `worlds/` persistence
5. Load World dropdown in the main Start Game UI
