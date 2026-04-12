# Workflow Mindmap Generation Spec

> Fixed specification for generating self-contained bidirectional mindmap HTML files from workflow documents.

---

## 1. Scope / Trigger

- **Trigger**: Any workflow document (e.g. `工作流总纲.md`) needs a visual mindmap companion
- **Scope**: Generate a single self-contained `.html` file with no external dependencies (no CDN, no npm packages)
- **Output location**: `<workflow-dir>/工作流思维导图.html`

---

## 2. Architecture Contract

### 2.1 File Requirements

| Contract | Value |
|----------|-------|
| Format | Single `.html` file, fully self-contained |
| External deps | **None** — no CDN, no `<script src>`, no npm |
| Encoding | UTF-8, `lang="zh-CN"` |
| Rendering engine | Vanilla JS DOM + inline SVG |
| Browser compat | Any modern browser, open via `file://` |

### 2.2 Data Structure

The mindmap tree is a JS array literal `const tree = [...]` embedded in the HTML:

```javascript
const tree = [
  {
    html: 'Root Title<br>Version',  // HTML content
    level: 0,                        // only on root node
    id: 'root',                      // unique string ID
    children: [
      // ── Right-side phases (expand rightward) ──
      {
        html: 'Phase Title',
        cls: 'L1 c1',                // CSS class: L1 + color class
        id: 'p1',
        sub: '<span class="cmd">/command</span>',  // subtitle (commands)
        children: [
          { html: 'Detail Title', cls: 'L2', det: 'description<br>lines', id: 'p1_1' },
          { html: '/command', cls: 'L3', id: 'p1_c', cp: 'path/to/file', cd: 'description' },
          { html: 'skill-name', cls: 'SK', id: 'p1_s', su: 'usage description' },
          { html: 'Gate Name', cls: 'GT', id: 'p1_g', det: 'gate description' },
        ]
      },
      // ── Left-side branches (expand leftward) ──
      {
        html: 'Branch Title',
        cls: 'BR',
        id: 'br_xxx',
        bdesc: 'branch description',
        btrig: 'trigger condition',
        side: 'left',                // marks left-side branch
        children: [
          { html: 'Sub-item', cls: 'L2', det: 'detail', id: 'br_xx_1' },
        ]
      }
    ]
  }
];
```

### 2.3 Node Types (CSS Classes)

| Class | Purpose | Required Fields |
|-------|---------|----------------|
| `L0` (implicit) | Root node | `html`, `level:0`, `id` |
| `L1` | Phase node (§1–§7) | `html`, `cls:'L1 cN'`, `id`, `sub` |
| `L2` | Detail/task node | `html`, `cls:'L2'`, `id`, `det` |
| `L3` | Command/path node | `html`, `cls:'L3'`, `id`, `cp`, `cd` |
| `SK` | Skill node | `html`, `cls:'SK'`, `id`, `su` |
| `GT` | Gate/checkpoint node | `html`, `cls:'GT'`, `id`, `det` |
| `BR` | Branch/diversion node | `html`, `cls:'BR'`, `id`, `bdesc`, `btrig`, `side:'left'` |

### 2.4 Color Scheme

Phase-to-color mapping (one per `§N`):

```javascript
// CSS classes                   // Connection colors
.c1 { border-color: #ff9e64 }    // §1 orange
.c2 { border-color: #7aa2f7 }    // §2 blue
.c3 { border-color: #bb9af7 }    // §3 purple
.c4 { border-color: #2ac3de }    // §4 cyan
.c5 { border-color: #9ece6a }    // §5 green
.c6 { border-color: #f7768e }    // §6 red
.c7 { border-color: #e0af68 }    // §7 yellow
// BR branches: #d2a8ff (purple)
```

---

## 3. Layout Engine Contract

### 3.1 Direction — Bidirectional

- **Right side**: Root → phases §1–§7 expanding rightward
- **Left side**: Root → branch flows expanding leftward
- Mark left-side root children with `side: 'left'` in data
- Build two independent flat maps: `rFlat` (right) and `lFlat` (left)

### 3.2 Algorithm — Measure-First, Bottom-Up

```
Phase 1 — Flatten:
  Split tree[0].children by side marker
  Walk each side independently → rFlat / lFlat with _parent, _kids, _depth

Phase 2 — Measure (OFF-SCREEN, before layout):
  Render each node in a hidden measuring container
  Record _ownH = offsetHeight (node's own rendered height)
  Set _h = _ownH initially
  CRITICAL: measureBox must use position:fixed on document.body
             NOT position:absolute inside #wrap (CSS interference)

Phase 3 — Subtree height (bottom-up):
  For each root-level branch: subH(flat, id)
    if leaf: return _h (= _ownH)
    if parent: _h = max(sum(children._h + gaps), _ownH)
    return _h

Phase 4 — Placement (bottom-up via placeBlock):
  placeBlock(flat, id, top) → returns bottom y
    if leaf: _top = top, return top + _h
    if parent:
      1. Place children sequentially: cursor advances by child._h + gap
      2. Compute kidsCenter = (firstKid._top + lastKid._top + lastKid._h) / 2
      3. Set _top = kidsCenter - _ownH / 2   ← USE _ownH, NOT _h
      4. return cursor (bottom of last child)

Phase 5 — Recenter on real DOM:
  After rendering DOM elements, re-run centering using actual offsetHeight
  This eliminates any measurement vs rendering discrepancies

Phase 6 — Render:
  Place DOM elements at (_top, computed left)
  Draw SVG cubic bezier edges
```

### 3.3 Side Placement

```javascript
// RIGHT: sequential from top=40
placeRight(rFlat, 40);

// LEFT: centered at same vertical position as right side
const rCenter = (rFirst._top + rLast._top + rLast._h) / 2;
const lBranchH = sum(lRoots._h) + (lRoots.length - 1) * gv(0);
placeLeft(lFlat, rCenter - lBranchH / 2);
```

### 3.4 Spacing Constants

```javascript
const VGAP = [60, 28, 18];
// VGAP[0] = gap between root-level siblings (phases/branches)
// VGAP[1] = gap between depth-2 nodes (details within a phase)
// VGAP[2] = gap between depth-3 nodes (commands/skills/gates)

const COL_GAP = 60;
// Horizontal gap between parent right-edge and child left-edge
```

### 3.5 Root Positioning

```javascript
// Root X: manually set to center in viewport
// Value depends on sidebar width; typically 700-900px
rootEl.style.left = '900px';

// Root Y: centered between all children (both sides)
const globalCenter = (minTop + maxBottom) / 2;
rootEl.style.top = (globalCenter - rootEl.offsetHeight / 2) + 'px';
```

### 3.6 Connection Lines

```javascript
// Cubic bezier: M fx fy C cpx fy, cpx ty, tx ty
// cpx offset: 40px from parent edge
// root→phase (right): stroke-width 2, phase color from phC
// root→branch (left): stroke-width 1.8, #d2a8ff
// child edges: stroke-width 1.2, #30363d
// opacity: 0.55
// NO arrow markers (removed for cleaner look)
```

### 3.7 Layout Validation Rules

| Rule | How to verify |
|------|--------------|
| No overlaps | No two nodes share any pixel area |
| Parent centered | `|parent.center - kids.center| ≤ 1px` |
| Root centered | Root Y center within 2px of global children block center |
| Bidirectional | Right children X > root.X; Left children X < root.X |
| Phase spacing | §1..§7 nodes have ≥40px vertical gap |
| Branch spreading | Left branches spread evenly around root, not stacked at top |

---

## 4. CSS Contract

### 4.1 Base Styles

```css
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
     background:#0d1117;color:#c9d1d9;overflow:auto}
#wrap{position:relative;padding:40px}
svg{position:absolute;top:0;left:0;pointer-events:none;z-index:0}
.nd{position:absolute;border-radius:8px;z-index:1;white-space:nowrap}
```

### 4.2 Node Styles (Final Values)

| Class | Border | Background | Font | Padding |
|-------|--------|------------|------|---------|
| `.L0` | 2px solid `#7aa2f7` | gradient `#1a1b26→#24283b` | 22px bold | 14px 28px |
| `.L1` | 2px solid (phase color) | transparent | 17px bold | 12px 20px |
| `.L2` | 1px solid `#30363d` | `#161b22` | 14px semibold | 10px 16px |
| `.L3` | 1px dashed `#3fb950` | `#1c2333` | 13px mono | 8px 14px |
| `.SK` | 1px solid `#bb9af7` | `#1a1f2e` | 12px | 7px 14px |
| `.GT` | 2px solid `#f0883e` | `#2d1f1f` | 13px | 8px 14px |
| `.BR` | 2px solid `#d2a8ff` | `#1a1b22` | 14px bold | 10px 18px |

### 4.3 Sub-element Styles

| Selector | Font Size | Color | Notes |
|----------|-----------|-------|-------|
| `.L1 .cmd` | 12px | `#8b949e` | monospace |
| `.L2 .det` | 12px | `#8b949e` | max-width: 260px, normal wrap |
| `.L3 .cn` | 13px | `#3fb950` | monospace |
| `.L3 .cp` | 11px | `#8b949e` | max-width: 280px |
| `.L3 .cd` | 12px | `#c9d1d9` | |
| `.SK .sn` | 12px | `#bb9af7` | |
| `.SK .su` | 11px | `#8b949e` | |
| `.BR .bdesc` | 12px | `#8b949e` | max-width: 240px, normal wrap |
| `.BR .btrig` | 11px | `#d2a8ff` | monospace, opacity 0.8 |

---

## 5. Key Decisions

### Design Decision: Measure-First with Off-Screen Container

**Problem**: Hardcoded leaf heights (42px) don't match actual rendered heights (36-91px), causing overlaps and miscalculated centering.

**Decision**: Measure all node heights before layout, using an off-screen DOM container.

**Critical gotcha**: The measuring container MUST use `position:fixed` on `document.body`, NOT `position:absolute` inside `#wrap`. The `#wrap` container's CSS (`white-space:nowrap`, padding, etc.) can interfere with measurement, producing different widths than actual rendering.

```javascript
// CORRECT
const measureBox = document.createElement('div');
measureBox.style.cssText = 'position:fixed;top:-99999px;left:-99999px;visibility:hidden;';
document.body.appendChild(measureBox);

// WRONG — measurement may differ from actual rendering
const measureBox = document.createElement('div');
measureBox.style.cssText = 'position:absolute;top:-99999px;visibility:hidden;';
W.appendChild(measureBox);
```

### Design Decision: Separate _ownH and _h

**Problem**: `subH()` overwrites `_h` with subtree total height, but centering formula needs the node's own height.

**Decision**: Keep `_ownH` (node's own rendered height, immutable) separate from `_h` (subtree total height, computed by `subH`). Centering uses `_ownH`, spacing uses `_h`.

```javascript
n._ownH = measuredHeight;  // set once, never changed
n._h = measuredHeight;     // initially same, overwritten by subH
// subH: n._h = max(sum(children._h + gaps), n._ownH)
// placeBlock: n._top = kidsCenter - n._ownH / 2  ← NOT _h
```

### Design Decision: Bidirectional with Independent Flat Maps

**Problem**: Single flat map with left/right marker makes placement logic complex.

**Decision**: Split into two independent flat maps (`rFlat`, `lFlat`), each treated as a standalone tree. Each has its own `walkSide`, `subH`, `placeBlock` calls.

### Design Decision: DOM Recenter Pass

**Problem**: Off-screen measurement may still differ slightly from actual rendering (0-14px).

**Decision**: After all DOM elements are created, run a `recenterAll` pass that re-centers every parent using `elMap[id].offsetHeight` and `elMap[kidId].offsetTop / offsetHeight`. This guarantees pixel-perfect centering.

### Design Decision: No Arrow Markers

**Problem**: SVG arrow triangles add visual clutter on dense mindmaps.

**Decision**: Remove all `marker-end` attributes and marker `<defs>`. Connection lines are clean curves without arrowheads.

---

## 6. Generation Process

### Step 1: Parse Source Document

Read the workflow document and extract:
- Phases (§1–§7) as L1 nodes (right side)
- Sub-steps (1.1, 1.2, ...) as L2 nodes
- Commands as L3 nodes, Skills as SK nodes, Gates as GT nodes
- Branch flows as BR nodes (left side, with `side:'left'`)

### Step 2: Build Tree

Construct the `const tree = [...]` array with:
- Unique `id` for every node
- Correct `cls` for node type + color class `c1`–`c7`
- Left-side branches marked with `side: 'left'`
- `sub`, `det`, `cp`, `cd`, `su`, `bdesc`, `btrig` fields as appropriate

### Step 3: Validate

Before writing the file:
- [ ] Every node has a unique `id`
- [ ] Every L1 node has a color class `c1`–`c7`
- [ ] Root node has `level: 0`
- [ ] Left-side branches have `side: 'left'`
- [ ] `phC` keys match L1 node IDs

### Step 4: Write and Test

- Write to `<workflow-dir>/工作流思维导图.html`
- Open in browser and verify:
  - No overlaps between any nodes
  - Every parent node vertically centered on its children block
  - Root centered between left and right sides
  - Left branches spread evenly (not clustered at top or bottom)
  - Connection lines render without arrow markers
  - All text readable with adequate font size

---

## 7. Wrong vs Correct

### Wrong: External dependency

```html
<!-- WRONG: CDN dependency, fails offline -->
<script src="https://cdn.jsdelivr.net/npm/markmap-view@0.17.2"></script>
```

### Correct: Self-contained

```html
<!-- CORRECT: All code inline, works from file:// -->
<script>
const tree = [ /* ... */ ];
// layout + render code inline
</script>
```

### Wrong: Hardcoded leaf height

```javascript
// WRONG: all leaves assumed 42px
if (!n._kids.length) { n._h = 42; return 42; }
```

### Correct: Measured height

```javascript
// CORRECT: measure actual rendered height
n._ownH = measureNode(id, n.cls, renderInner(n)).h;
n._h = n._ownH;
// subH preserves _ownH, only updates _h
```

### Wrong: Centering with subtree height

```javascript
// WRONG: _h is subtree total, not node's own height
n._top = kidsCenter - n._h / 2;
```

### Correct: Centering with own height

```javascript
// CORRECT: _ownH is the node's own rendered height
n._top = kidsCenter - n._ownH / 2;
```

### Wrong: MeasureBox inside #wrap

```javascript
// WRONG: #wrap CSS affects measurement
W.appendChild(measureBox);
```

### Correct: MeasureBox on body with position:fixed

```javascript
// CORRECT: isolated from #wrap CSS
document.body.appendChild(measureBox);
```

### Wrong: Single flat map with side flag

```javascript
// WRONG: complex placement logic mixing left/right
const flat = {};
walkTree(allChildren, flat, 'root', 1);
// then needs side-aware branching in every function
```

### Correct: Independent flat maps per side

```javascript
// CORRECT: each side is a standalone tree
const rFlat = {}, lFlat = {};
walkSide(rightKids, rFlat, 'root', 1);
walkSide(leftKids, lFlat, 'root', 1);
// placement, subH, render all operate independently per side
```

---

## 8. Tests Required

| Test | Assertion |
|------|-----------|
| No DOM overlap | For every pair of nodes: bounding rects do not intersect |
| Parent centering | `|parent.center - kids.center| ≤ 1px` for all parents |
| Root centering | Root Y center within 2px of global children block center |
| Left branch spreading | Left branches' _top values are distributed, not all clustered in one region |
| All IDs unique | `new Set(allIds).size === allIds.length` |
| No orphan nodes | Every non-root node has a valid _parent |
| Measure accuracy | `_ownH` matches `elMap[id].offsetHeight` after DOM creation |
| Root X in viewport | `rootEl.offsetLeft > 0` and `rootEl.offsetLeft + rootEl.offsetWidth < window.innerWidth` |
| Phase colors | `phC` keys match L1 node IDs exactly |
