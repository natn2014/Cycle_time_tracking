# Project Scope: Cycle Time Tracking via USB Webcam

## Overview

A Raspberry Pi 5–based vision system that monitors a single camera feed, detects when a product silhouette is present in a defined Region of Interest (ROI), and measures the elapsed time between **consecutive arrivals** of a matching silhouette. Each arrival closes the previous cycle and opens the next one, so the line is measured **continuously** (inter-arrival / takt time). Result is displayed in seconds on a connected HDMI monitor, and per-shift piece counts are tracked for a 3-shift benchmark.

---

## Hardware

| Component | Spec |
|-----------|------|
| Compute | Raspberry Pi 5, 8 GB RAM |
| Camera | USB webcam (UVC-compatible) |
| Display | HDMI monitor (result readout) |
| OS | Raspberry Pi OS (64-bit, Bookworm) |

---

## System Architecture

```
[USB Webcam]
     │
     ▼
[Frame Capture]  ← OpenCV VideoCapture (target: 30 fps)
     │
     ▼
[ROI Crop]       ← User-defined rectangle on first run
     │
     ▼
[Grayscale + Canny Edge Detection]
     │
     ▼
[Perceptual Hash (pHash)]
     │
     ▼
[Distance vs. Master Hash]──── distance ≤ threshold?
     │                                    │
     NO (absent)                       YES (present)
     │                                    │
     └────────────────┬───────────────────┘
                      ▼
              [State Machine]
                      │
   ┌──────────┬───────┴───────┬──────────────┐
   ▼          ▼               ▼              ▼
 IDLE      TIMING     WAITING_FOR_RETURN   RESULT
(waiting) (timer      (object left,       (log cycle,
           running)    timer still         +1 piece,
                       running)            chain to TIMING)
```

---

## Detection Pipeline (per frame)

1. **Capture** — read raw frame from webcam
2. **ROI crop** — extract pre-configured bounding box
3. **Grayscale** — reduce to single channel
4. **Canny edge detection** — extract silhouette / shape boundaries
5. **pHash** — compute 64-bit perceptual hash of edge image
6. **Distance check** — Hamming distance vs. master hash ≤ `MATCH_THRESHOLD` (default: 10)
7. **Debounce** — require `CONFIRM_FRAMES` consecutive matches (default: 5) before triggering state change
8. **Absence guard** — require `ABSENT_FRAMES` consecutive non-matches (default: 10) before the object is considered gone and a new detection cycle can begin

---

## State Machine

Cycle definition: **absent → present (timer START) → absent → present (timer STOP = next START)**

The line runs **continuously**: the arrival that stops cycle N is the same physical piece that starts cycle N+1, so no cycles are dropped between consecutive pieces.

```
IDLE  (cold start — no baseline yet)
  │
  └──(object confirmed present)──▶ TIMING  ◀── T₁ set (first baseline arrival)
        ┌──────────────────────────────┘
        ▼
     TIMING
        │
   (object confirmed absent)
        │
        ▼
 WAITING_FOR_RETURN   (timer keeps running)
        │
   (object confirmed present again)
        │
        ▼
     RESULT
   • cycle time = T₂ − T₁   → log + flash
   • +1 piece → current shift bucket
   • T₁ ← T₂                (chain: this arrival becomes the new baseline)
        │
        └──────────────▶ TIMING   (continuous — back to timing immediately)
```

> **Timing anchor points:**
> - T₁ = moment a matching silhouette is confirmed **present** (baseline arrival)
> - T₂ = moment the **next** matching silhouette is confirmed present, after an absent gap
> - Cycle time = T₂ − T₁
> - **On each RESULT, T₁ is reset to T₂** so measurement continues without a gap.
> - IDLE is only the cold-start state (before the very first arrival). After that, the machine cycles TIMING ⇄ WAITING_FOR_RETURN ⇄ RESULT.
> - A `min_cycle_seconds` floor rejects a too-fast T₂ (bounce / double-trigger) so it is not counted as a piece.

---

## Master Image Setup

- **At startup**, the system enters **Calibration Mode**:
  1. Display live feed with ROI overlay
  2. User presses `[S]` to capture the current frame as the master
  3. System applies the same Grayscale → Canny → pHash pipeline and saves the hash + reference image to `master.pkl`
- Subsequent runs load `master.pkl` automatically (skip calibration if file exists)
- Press `[C]` at any time to re-enter calibration and overwrite master

---

## Piece Counting

- **One completed cycle = one piece.** Each time the state machine reaches `RESULT` (a valid T₂ above the `min_cycle_seconds` floor), the piece counter for the **current shift** is incremented by 1.
- The piece is attributed to whichever shift is active **at the moment T₂ occurs** (based on system clock).
- Cycle time of that piece is added to the current shift's Min / Avg / Max aggregation.

---

## Data Persistence

Per-shift totals must survive an app restart or power blip, so they are stored on disk.

- **File:** `today.json` — holds the 3 shift buckets for the current production day.
- **Contents per shift:** `count`, `sum_cycle`, `min_cycle`, `max_cycle` (avg is derived = `sum_cycle / count`).
- **Write cadence:** rewritten after every completed cycle (small file, cheap on RPi 5).
- **Daily reset:** at **08:00** (start of DAY shift), the previous day's `today.json` is archived to `history/YYYY-MM-DD.json` and a fresh, zeroed `today.json` is created.
- **On startup:** if `today.json` exists and belongs to the current production day, it is loaded so counts resume; otherwise a fresh one is created.

```json
{
  "production_day": "2026-07-01",
  "shifts": {
    "DAY":     { "count": 142, "sum_cycle": 1746.6, "min_cycle": 9.8,  "max_cycle": 18.1 },
    "EVENING": { "count": 108, "sum_cycle": 1522.8, "min_cycle": 10.2, "max_cycle": 21.5 },
    "NIGHT":   { "count": 89,  "sum_cycle": 1424.0, "min_cycle": 11.0, "max_cycle": 25.3 }
  }
}
```

---

## Output Display

- Full-screen OpenCV window on HDMI monitor, **two auto-swapping tabs** (swap every `tab_swap_seconds`).
  - **Tab 1 — Live Monitor:** live feed + ROI + current state + elapsed + rolling stats.
  - **Tab 2 — Shift Summary:** 3-shift piece counts + benchmark bars.
- Detection runs in the background regardless of which tab is visible.
- **Rolling stats on Tab 1** (Last cycle / Min / Avg / Max) are computed over the **last N completed cycles** (`stats_window`, default 20) — a short-term view of current performance.
- **Per-shift stats on Tab 2** are computed over the **whole shift** from `today.json` — the long-term benchmark.
- On `RESULT`: cycle time flashes green for `result_hold_seconds`.
- **Full visual spec (zones, states, colors, both tabs): see [layout.md](layout.md).**

---

## Configuration (config.yaml)

```yaml
camera_index: 0           # USB webcam device index
camera_width: 640         # capture resolution (cap to protect USB bandwidth)
camera_height: 480
target_fps: 30
roi:
  x: 200
  y: 150
  w: 240
  h: 180
canny_low: 50             # Canny edge detection lower threshold
canny_high: 150           # Canny edge detection upper threshold
match_threshold: 10       # Hamming distance (0 = identical, 64 = opposite)
confirm_frames: 5         # consecutive frames required to confirm PRESENT
absent_frames: 10         # consecutive non-match frames to confirm ABSENT
min_cycle_seconds: 2.0    # reject faster T₂ as bounce / double-trigger
stats_window: 20          # rolling window for Tab 1 Min/Avg/Max
display_fullscreen: true
tab_swap_seconds: 5       # auto-swap interval between Live and Summary tabs
result_hold_seconds: 2    # how long to flash the result before chaining
shifts:                   # 3 working shifts (24h coverage); day resets at DAY start
  DAY:     { start: "08:00", end: "16:00" }
  EVENING: { start: "16:00", end: "24:00" }
  NIGHT:   { start: "00:00", end: "08:00" }
```

---

## File Structure

```
cycle_time_tracking/
├── main.py               # entry point, main loop
├── config.yaml           # tuneable parameters
├── master.pkl            # saved master hash + reference image (generated at runtime)
├── detector.py           # Canny + pHash matching logic
├── state_machine.py      # IDLE / TIMING / WAITING_FOR_RETURN / RESULT (chained)
├── shift_tracker.py      # shift detection, piece buckets, today.json persistence
├── tabs.py               # auto-swap tab manager (Live ⇄ Summary)
├── display.py            # OpenCV overlay rendering (both tabs)
├── calibration.py        # master image capture workflow
├── today.json            # current day's per-shift totals (generated at runtime)
├── history/              # archived daily JSON files (YYYY-MM-DD.json)
└── requirements.txt      # imagehash, opencv-python, pyyaml, numpy
```

---

## Tech Stack

| Layer | Library | Reason |
|-------|---------|--------|
| Video capture & display | `opencv-python` | Native UVC + full GUI rendering (`imshow`); **not** the `-headless` build, which cannot draw windows |
| Edge detection | `cv2.Canny` | Fast, built into OpenCV |
| Image hashing | `imagehash` (pHash) | Robust to minor lighting/angle variance |
| Config | `pyyaml` | Human-editable tuning |
| Compute | Python 3.11 | Best RPi 5 support, asyncio if needed later |

---

## MVP Acceptance Criteria

- [ ] Live webcam feed displays with ROI box
- [ ] Calibration captures and persists master hash
- [ ] Object first becomes **present** → timer starts (T₁)
- [ ] Object goes **absent**, then becomes **present again** → cycle time = T₂ − T₁, and T₁ chains to T₂ (continuous)
- [ ] Cycle time displayed in seconds with 2 decimal places
- [ ] Each completed cycle increments the current shift's piece count
- [ ] Rolling Min / Avg / Max (last N cycles) shown on Tab 1
- [ ] Tab 2 shows per-shift piece counts + benchmark bars, auto-swapping every 5 s
- [ ] Shift totals persist to `today.json` and survive a restart
- [ ] Data resets/archives at 08:00 daily
- [ ] Configurable via `config.yaml` without code changes
- [ ] Runs on boot (systemd service) with monitor connected

---

## Out of Scope (MVP)

- Multiple simultaneous products in the ROI
- Full SQL database (MVP uses flat `today.json` + daily archive; add DB in v2 if needed)
- Network dashboard / remote monitoring
- Multi-camera support
- Object ID / tracking across frames (no YOLO or deep-learning required)

---

## Open Questions / Risks

| # | Question | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | Lighting variation between cycles | pHash distance may drift above threshold | Tune `match_threshold`; add adaptive histogram equalisation if needed |
| 2 | USB bandwidth at 30 fps | Frame drops on RPi 5 if resolution is high | Cap at 640×480 or use MJPEG compression mode |
| 3 | Object partially in ROI during entry/exit | False detection edges | Debounce (`confirm_frames`) handles transient partial visibility |
| 4 | Two products too close together | 2nd product triggers 2nd detection early | Enforce minimum cycle time floor (configurable) |

---

*Status: Concept approved → ready for implementation*
