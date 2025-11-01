## Zoomable Bubble Graph — Implementation Documentation

This document explains the implementation, data format, and runtime behavior of the "Zoomable Bubble Graph" located in the `frontend/` folder. The visualization is a small, self-contained D3 (v7) example that renders hierarchical data as a zoomable circle packing layout.

## Files

- `frontend/index.html` — Minimal HTML shell. Loads `d3.v7` from the official CDN and `script.js` as a module.
- `frontend/style.css` — Simple responsive CSS for layout and sizing of the chart container.
- `frontend/data.json` — Example hierarchical data (root -> children -> leaf nodes) used by the chart.
- `frontend/script.js` — Main implementation: builds the hierarchy, computes packing layout, draws the SVG, and implements zooming.

## High-level behavior / contract

- Inputs: a hierarchical JSON object in `frontend/data.json` (root node with nested `children` arrays). Each leaf node must have a numeric `value` property.
- Output: an interactive SVG circle-packing diagram appended to `#chart` in the page. Circles represent nodes and are color-coded by depth; clicking a circle zooms into it; clicking the background zooms out.
- Error modes: if `data.json` is missing, malformed, or missing `value` numbers at leaves, the chart won't render properly. The code does not currently provide explicit user-facing error messages.

## How the implementation works (walkthrough of `script.js`)

1. Load data
   - `const data = await d3.json("data.json");`
   - Uses D3's `d3.json` helper (fetch under the hood) to load `data.json`. Note: when opening `index.html` via `file://`, modern browsers may block the fetch. Serve the folder over HTTP when testing locally (see "How to run" below).

2. Setup constants
   - `width` and `height` are set to `928` (square). The SVG will be responsive using `viewBox` and CSS in `style.css`.

3. Color scale
   - A linear color scale maps node `depth` to a range of HSL colors:
     - `d3.scaleLinear().domain([0, 5]).range(["hsl(152,80%,80%)", "hsl(228,30%,40%)"]).interpolate(d3.interpolateHcl)`
   - `d3.interpolateHcl` is used for perceptually smoother interpolation of HSL colors.

4. Build packing layout
   - `pack` is a function that constructs a `d3.pack()` layout with `.size([width, height])` and `.padding(3)`.
   - The layout is applied to a `d3.hierarchy(data)` that:
     - Calls `.sum(d => d.value)` to compute each node's summed value used for circle area.
     - Calls `.sort((a, b) => b.value - a.value)` to sort siblings so larger bubbles are placed first.
   - The result is a `root` node with computed `x`, `y`, and `r` for every node in the hierarchy.
   - (Reference: d3-hierarchy pack & hierarchy — see links below.)

5. Create the SVG
   - `d3.create("svg")` creates an in-memory SVG element (not yet in the DOM). The SVG uses a `viewBox` centered at (0,0) with width/height equal to `width` and `height`.
   - The style includes `max-width: 100%` and `height: auto` so the chart scales responsively within `#chart`.

6. Draw nodes and labels
   - Circles: bound to `root.descendants().slice(1)` (skipping the root container circle), fill color is `color(d.depth)` for non-leaf nodes and `white` for leaves. Pointer-events are disabled for leaf nodes so clicks only register on parents.
   - Labels: an SVG `<g>` containing `<text>` elements for each node. Labels are only displayed (opacity and display style) for nodes whose parent is currently the root view. During zoom transitions their visibility and opacity are toggled.

7. Zoom behavior
   - Clicking a circle calls `zoom(event, d)`, which:
     - Sets `focus = d`.
     - Creates a transition with duration `750` ms (or `7500` ms if Alt key is pressed during the click).
     - Uses `d3.interpolateZoom(view, [focus.x, focus.y, focus.r * 2])` to compute a smooth zoom interpolation.
     - The helper `zoomTo(v)` applies computed transform: scales and translates node positions and radii so the focused circle fills the view.
   - Clicking the SVG background zooms back to the root.
   - This produces the standard smooth zooming seen in the D3 "Zoomable circle packing" example.
   - (Reference: the Observable example by Mike Bostock.)

## Data format expectations (`data.json`)

- Root object: `{ "name": "Root Name", "children": [...] }`.
- Internal nodes: objects with `name` + `children` array.
- Leaf nodes: objects with `name` and numeric `value`.

Example (already present at `frontend/data.json`):
- Top-level `name`: "Football Conversation" with nested categories: "Match Discussion", "Players", etc.
- Leaf nodes include `{"name":"Manchester City","value":50}` and so on.

Important: the packing layout uses `.sum(d => d.value)` so leaves must include a valid number in `value`.

## How to run locally

1. Recommended: serve the `frontend/` directory over a local HTTP server. From the repository root run (macOS / zsh):

```bash
# from repository root
cd frontend
python3 -m http.server 8000
```

2. Open http://localhost:8000 in your browser and the `index.html` will load `data.json` correctly.

3. Alternatively, you can open `index.html` directly with `file://` in some browsers, but this may fail due to cross-origin restrictions when loading `data.json`.

## Edge cases and notes

- Missing or non-numeric `value` on leaf nodes: the `.sum(d => d.value)` call will produce NaN or zero which may collapse nodes visually. Validate or sanitize input data before rendering.
- Very deep hierarchies or extremely large/small `value` ranges: packing may produce circles too small to interact with—consider clamping or min-radius logic for usability.
- Accessibility: current implementation uses no ARIA attributes or keyboard controls. Consider adding keyboard navigation and ARIA roles for better accessibility.
- Performance: for very large datasets the SVG + DOM approach can be slow. Consider using Canvas or limit the displayed depth.

## Suggestions for small improvements

- Add a minimal loading/error UI in `index.html` when `d3.json` fails.
- Add a toggle for label visibility and a legend explaining color scale.
- Add keyboard controls to zoom in/out (arrow keys, Enter/Esc) and accessible labels for screen readers.

## Key implementation references

- Zoomable circle packing example (matching this implementation):
  - https://observablehq.com/@d3/zoomable-circle-packing

- d3-hierarchy (pack, hierarchy, sum, sort):
  - https://github.com/d3/d3-hierarchy
  - Official docs: https://d3js.org/d3-hierarchy

- d3-scale and d3-interpolate (color interpolation helpers):
  - https://github.com/d3/d3-scale
  - https://github.com/d3/d3-interpolate

## Quick checklist for maintainers

- Where to change data: edit `frontend/data.json` (must preserve `children` structure and numeric leaf `value`).
- Where to change visuals/size: `frontend/script.js` — update `width`, `height`, or color scale.
- Where to change layout padding: `pack().padding(3)`.

## Completion / verification

- I reviewed `frontend/index.html`, `frontend/script.js`, `frontend/style.css`, and `frontend/data.json`.
- I consulted the D3 Observable example and the `d3-hierarchy` repository README to ensure accurate descriptions of `pack`, `hierarchy`, and the zoom interpolation.

If you'd like, I can:
- Add a short `README.md` inside `frontend/` with the run instructions.
- Implement a minimal `try/catch` + user-facing error message around the `d3.json` load.
- Add keyboard controls and basic ARIA annotations for accessibility.
