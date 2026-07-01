# Display Layout Concept

Full-screen OpenCV window on HDMI monitor, with **two auto-swapping tabs**:

- **Tab 1 — Live Monitor** (below): live feed + current cycle state + rolling stats.
- **Tab 2 — Shift Summary** (further down): 3-shift piece-count benchmark.

Tabs swap every `tab_swap_seconds` (default 5 s); detection keeps running on both.

---

## Tab 1 — Live Monitor

Split into two zones: **left = live feed**, **right = info panel**.
Info-panel Min/Avg/Max is a **rolling last-N-cycles** view (`stats_window`, default 20).

### Zone Map

```
┌─────────────────────────────────────────────────────────────────┐
│                        │                                        │
│                        │   STATE BADGE                         │
│                        │                                        │
│    LIVE FEED           │   ELAPSED / RESULT                    │
│    (with ROI box)      │                                        │
│                        │   ─────────────────                   │
│                        │   LAST CYCLE                          │
│                        │   MIN   AVG   MAX                     │
│                        │                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## States

### IDLE — waiting for object

```
┌─────────────────────────────────────────────────────────────────┐
│                        │                                        │
│   ┌ ─ ─ ─ ─ ─ ┐       │   ◉  IDLE                            │
│                        │      Waiting for object...            │
│   │  (ROI box) │       │                                        │
│                        │   ─────────────────────────           │
│   └ ─ ─ ─ ─ ─ ┘       │   Last cycle   --.-  s               │
│                        │   Min  --.- | Avg  --.- | Max  --.-   │
└─────────────────────────────────────────────────────────────────┘
```

---

### TIMING — object present, timer running

```
┌─────────────────────────────────────────────────────────────────┐
│                        │                                        │
│   ┌───────────┐        │   ● TIMING                           │
│   │███████████│        │                                        │
│   │  [object] │        │       4.23 s                         │
│   │███████████│        │                                        │
│   └───────────┘        │   ─────────────────────────           │
│                        │   Last cycle   12.50 s               │
│                        │   Min  10.20 | Avg  12.80 | Max  15.30│
└─────────────────────────────────────────────────────────────────┘
```
ROI box turns **yellow** while object is present.

---

### WAITING FOR RETURN — object gone, still timing

```
┌─────────────────────────────────────────────────────────────────┐
│                        │                                        │
│   ┌ ─ ─ ─ ─ ─ ┐       │   ◌  WAITING                         │
│                        │      Object absent — come back...     │
│   │  (empty)   │       │                                        │
│                        │       8.71 s  (running)              │
│   └ ─ ─ ─ ─ ─ ┘       │                                        │
│                        │   Last cycle   12.50 s               │
│                        │   Min  10.20 | Avg  12.80 | Max  15.30│
└─────────────────────────────────────────────────────────────────┘
```
ROI box returns to dashed (absent).

---

### RESULT — 2nd appearance detected

```
┌─────────────────────────────────────────────────────────────────┐
│                        │                                        │
│   ┌───────────┐        │   ✓  DONE                            │
│   │███████████│        │                                        │
│   │  [object] │        │      12.50 s  ◀ flashes green        │
│   │███████████│        │                                        │
│   └───────────┘        │   ─────────────────────────           │
│                        │   Last cycle   12.50 s               │
│                        │   Min  10.20 | Avg  12.13 | Max  15.30│
└─────────────────────────────────────────────────────────────────┘
```
Result flashes **green** for 2 s, then auto-resets to IDLE.

---

## Tab System

Two tabs auto-swap every **5 seconds**. Tab indicator shown top-right corner.

```
TAB 1: Live Monitor   ←──── swaps every 5 s ────▶   TAB 2: Shift Summary
```

The live detection state machine keeps running in the background regardless of which tab is visible.

---

## Tab 2 — Shift Summary

Full-screen summary. No live feed. Shows piece count and avg cycle time per shift, with a simple bar benchmark.

> **Piece count rule:** one completed cycle (each valid `RESULT` / T₂) = **+1 piece**, credited to whichever shift is active when T₂ occurs.
> Counts and per-shift Min/Avg/Max are read from `today.json` (see ProjectScope → Data Persistence), so they survive restarts and reset at 08:00.
> Note: Tab 2 stats span the **whole shift**, whereas Tab 1 Min/Avg/Max is a rolling **last-N-cycles** view.

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  SHIFT SUMMARY                          2026-07-01   14:32  [2/2]│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ▶ DAY      08:00 – 16:00   ████████████████░░░░   142 pcs    │
│              Avg cycle  12.3 s  |  Min  9.8 s  |  Max  18.1 s  │
│                                                                  │
│   ─────────────────────────────────────────────────────────     │
│                                                                  │
│     EVENING  16:00 – 24:00   ████████████░░░░░░░░   108 pcs    │
│              Avg cycle  14.1 s  |  Min  10.2 s |  Max  21.5 s  │
│                                                                  │
│   ─────────────────────────────────────────────────────────     │
│                                                                  │
│     NIGHT    00:00 – 08:00   ████████░░░░░░░░░░░░    89 pcs    │
│              Avg cycle  16.0 s  |  Min  11.0 s |  Max  25.3 s  │
│                                                                  │
│   ─────────────────────────────────────────────────────────     │
│                                                                  │
│   TODAY TOTAL                                         339 pcs   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Bar Chart Logic

- Bar width scales to the **best shift** of the day (highest piece count = full bar)
- Other shifts are drawn proportionally against that max
- Active / current shift row is highlighted with `▶` marker and brighter color

### Shift Detection (auto, based on system clock)

| Shift | Hours | Label |
|-------|-------|-------|
| DAY | 08:00 – 15:59 | DAY |
| EVENING | 16:00 – 23:59 | EVENING |
| NIGHT | 00:00 – 07:59 | NIGHT |

Data resets at **08:00** each day (start of DAY shift = new production day).

---

## Tab 2 — Color Coding

| Element | Color |
|---------|-------|
| Current shift row | White / bright |
| Past shift row | Light grey |
| Future shift row | Dark grey (dimmed) |
| Bar — current shift | Cyan |
| Bar — past shift | Grey |
| Bar — best shift (highest count) | Gold highlight |
| Today total | White, large |
| Tab indicator `[1/2]` / `[2/2]` | Small, top-right corner |

---

## Color Coding

| Element | Color |
|---------|-------|
| ROI box — object absent | White dashed |
| ROI box — object present | Yellow solid |
| State badge — IDLE | Grey |
| State badge — TIMING | Blue |
| State badge — WAITING | Orange |
| State badge — DONE | Green (flash) |
| Elapsed counter | White, large font |
| Result value | Green, large font |
| Stats row | Light grey, small font |

---

## Font Sizes (relative)

```
STATE BADGE      → medium  (e.g. 0.8 scale)
ELAPSED / RESULT → large   (e.g. 2.0 scale, bold)
LAST CYCLE label → small   (e.g. 0.6 scale)
MIN / AVG / MAX  → small   (e.g. 0.6 scale)
```

---

*Approve or comment on any zone, color, or element before implementation.*
