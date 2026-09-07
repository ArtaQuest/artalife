# The Same Row — the ArtaQuest channel teaser

16 s · 384 frames · 24 fps · 1920 × 1080. Arta stands dead centre on a floor mark in the dark,
draws, and fires one arrow at the left edge and one at the right; a life draws itself down each
edge in the show's own rails and type; the couple's two windows fall in above, the host's window
rises out from behind them and lands around Arta, and on both rails at once the one year they
share — 1979 — turns gold. The last held frame is the show's frame
(`design/artapodcast/final/Main.dc.html`: couple windows 912 × 513 at (32, 18) and (976, 18), host
640 × 360 at (640, 625), rails at x 32..608 and 1312..1888 on a 64 px pitch, blue-bar
lower-thirds), held a full second, then a 0.25 s fade. No end card, no wordmark.

This is the design that won the judged competition (proposal "The Same Row"), built from scratch;
nothing is taken from the rejected `scenes/teaser/`.

## How it is drawn

- **One rig.** `scenes/undefined/generate.py` is imported by path under the name `arta_rig`, so the
  skeleton (spine 70 · neck 24 · head r20 · thigh/shin 52 · arm 34/32), joint convention, IK and
  proportions are the published film's. One scene-local drawing convention: the arms are DRAWN
  from a shoulder 7 rig units down the spine (`SHOULDER_DROP`), not from the neck. The rig roots
  them at the neck, which is exactly where the head ring's outer edge sits (24 = r20 + stroke/2),
  so a horizontal pointing arm put its 8-unit stroke through the ring's bottom arc and the ring
  read as sitting on a bar. Angles and lengths are the rig's; only the root moves. Figure scale
  1.58 (344 px), so the whole figure — ring included — sits inside the 360 px host window at the
  end; stroke 8 rig units, gold, round caps and joins, no fillet.
- **SVG, rasterised in the lab Chrome.** Each frame is ONE SVG — ambient, floor mark, windows,
  lower-thirds, rails, rows, figure, arrow, camera transform, vignette — written by `generate.py`
  and screenshotted by `render.mjs` over CDP `127.0.0.1:9222` (the parked ArtaFocus lab, the same
  route as `shot.mjs`; nothing ever opens in the operator's browser). Fonts (Montserrat 700,
  Inter 500/600) are embedded from `../teaser/fonts` as data URIs so the render is network-free.
- **The frame is read off the kit, not invented.** Every coordinate of the last frame comes from
  `Main.dc.html` / `Spec.dc.html` §3 and §10. Measured against a `shot.mjs` render of
  `Main.dc.html` (bright-pixel boxes): both lower-thirds identical to the pixel — man
  (32, 341, 584, 528), woman (976, 381, 1313, 528) — and all twelve rows' x-extents identical
  (left 32..408/262/335/416/343/252, right 1507/1658/1552/1607/1508/1500..1887). The only
  difference is the highlighted row: 1979 on both rails here, the kit's 1985/1984 sample in Main.
  That is a measurement, not a gate.
- **The arrow is brand blue `#1746DC`** — the proposal's `#4A72FF` is a third colour and is not
  used. Two colours only: gold `#E8B923` and blue `#1746DC` on `#010C17` / `#0C1E32`, inks
  `#F4F4F5` / `#A6A8B0` / `#8B8E98`. The arrow is a 9.5 px stroke at full opacity with 22 × 13
  barbs on a 120 px shaft; it LANDS on the birth tick and rests there 0.2 s while the tick fades
  in, then goes — it never flies off the frame.
- **Rows rise per `final/MOTION-SPEC.md`:** opacity 0→1 with translateY 24→0 over 0.3 s on
  cubic-bezier(0, 0, 0.58, 1), one row every 0.40 s as the rail's tip passes its tick, so the rises
  overlap and no frame of a list beat is still. The gold moment uses the kit's own durations: tick
  0.3 s, gold line 0.6 s, row colours 0.3 s.
- **The floor mark is under Arta only.** A soft-ended hairline from world x 560 to 1360; it never
  runs under a rail, so the sixth row — born 24 px below its tick, i.e. below the floor — is never
  struck through by it.
- **The windows have mass.** Gravity (u²) over 0.9 s to 8 px past the seat, 0.15 s settle, so the
  largest per-frame step is 53 px (was ~250 px: a slab shown at five positions), and a slab in
  motion is drawn with a vertical motion blur proportional to its step. The host's window is drawn
  BENEATH the couple's and clipped below their bottom edge (y 531): it emerges from behind them,
  so it can neither overdraw a lower-third nor fill the gap between the two windows on its way.
- **The camera** is one camera, monotonic in scale, three framings: A (1.40, his side + Arta,
  his birth tick 81 px inside the left edge), B (1.24, her side + Arta, her birth tick 81 px inside
  the right edge), C (1.00, the frame). It is authored under the motion law like the figure. Each
  list fades OUT over the 32 world px before the frame edge reaches its tick and back IN as the
  edge leaves (`list_op`), so the frame edge never slices a word or a tick; his list is gone for
  the fast part of the pull and back at full by the time the frame is the frame.

## The clock

| s | beat |
|---|------|
| 0.10–1.70 | the arm rises from a stand to the point (the film opens on a draw, not a held pose) |
| 1.75 | fire left; lands 2.41 on the birth tick; his six rows rise to 4.79 |
| 3.00–4.60 | the turn: face −1 → +1 AND the pointing arm comes down, one motivated move; the rear knee lifts and replants, so the legs are never one line edge-on |
| 4.75–8.25 | pan A → B (his list fades as the edge reaches it, 5.17–5.37) |
| 6.00–7.60 | the arm rises to the right point; 7.65 fire right; lands 8.31 with the mark 96 px inside the edge |
| 8.55–10.05 | arm down |
| 9.90–12.20 | pull B → C; the couple's windows fall at 10.60 and 10.85 (settled 11.65 / 11.90); ambient and vignette gone by 11.50 |
| 12.05 | the flinch — noticing |
| 12.35 | THE SAME ROW: 1979 turns gold on both rails at once |
| 12.75–13.35 | one nod, ending on zero |
| 13.05 | the host window emerges from behind the couple's; lands 13.85, settled 14.00; the floor mark goes |
| 13.35–14.75 | the think: stand → arm out with the elbow bent and the forearm hanging (0.4 s) → the forearm swings up to the chin (1.0 s) |
| 14.75–15.75 | the payoff held, 1.0 s at full brightness |
| 15.75–16.00 | fade |

## Run

```
python3 generate.py --check      # gates only (measures the type in the lab Chrome on first run)
python3 generate.py              # svg/*.svg + gates
python3 generate.py render       # + frames/*.png, silent.mp4, the music mux, manifest.json
```

`render` writes `/Users/arash/Downloads/artaquest/artaquest-teaser/ArtaQuest_teaser_v2.mp4`:
`silent.mp4` (libx264 crf 17, yuv420p) muxed with `teaser_music.wav` trimmed to 16 s, 1.2 s fade in,
2.4 s fade out, loudnorm I = −14 TP = −1.5 (two-pass, linear). The manifest is read back off the
delivered file (duration, frame count, sha256, measured loudness), never from the render intent.

## The gates (`--check` fails loudly)

1. **Motion — ARTA.md §3, literally.** No drawn point of the figure moves more than
   `min(640 px/s · dt, 12 px)` between two painted frames, in FRAME pixels with the camera applied.
   At 24 fps that is 12 px; it is not re-derived. A governor scales the whole blend back when an
   authored move would break it (the figure slows as one body); every move is authored so the
   governor does not have to act, and `--check` prints how often it did (0 of 384).
2. **Head — intrusion.** Every limb is sampled at one rig unit; samples within 13 units of the
   neck are a shoulder and ignored; no sample may lie inside the ring's outer edge
   (`HEAD_R + STROKE/2 = 24`). A "centre-line ≥ radius" rule cannot go green because the arms
   root 24 units from the head centre; this one passes stand, point, fold and the solved think,
   and flags the film's own cheer and lift. The think pose is solved against it: hand under the
   head where a chin would be, 28 units from its centre, elbow below the shoulder.
3. **Labels.** No figure ink (stroke included) inside a live row's text box on any frame; boxes
   are measured in the browser (`metrics.json`). Honest note: Arta never leaves x = 960 and the
   boxes lie at x < 420 and x > 1580, so this gate cannot fail with the current staging — it is
   kept for the day the staging changes, and it proves nothing about the frame edge; gate 7 does.
4. **Aim.** At each fire the whole arm lies on the line from the SHOULDER it is drawn from to the
   mark it hits, within 2° (the `face` is carried by the pose, so `point()` aims where it is
   told — the sign bug that made the last teaser turn left and point right is fixed at its cause).
5. **Frame.** On the last held frame all THREE windows are seated, the vignette, ambient and floor
   mark are gone, and the whole figure — stroke and ring included — lies inside the host window
   from the moment the host falls to the end (Arta in the host's chair, not through its lintel).
6. **Arrival.** Each mark is inside the frame, 24 px or more from every edge, at the instant its
   arrow lands (this is the one that would have caught her rail drawing off-screen).
7. **Edge.** No visible type — any row or lower-third text box at effective opacity above 0.02 —
   is cut by the frame edge on any frame.
8. **Windows.** No slab steps more than 60 frame px between two frames while it falls.

Stated exceptions, in `manifest.json`: the arrow is a tool, not a drawn point of the figure — it
flies 50 world px/frame against a 120 px shaft, so consecutive drawings overlap by half; the
windows are slabs with mass (gravity over 0.9 s, 8 px overshoot, 0.15 s settle, steps capped and
blurred). A walk was not added: under the 12 px law a lawful root speed at this scale is ~65 px/s,
which is not a walk.

## Notes for the operator

- Arta stands in the host's window. The window is an empty placeholder, nothing is drawn OVER a
  host, but it reads as Arta in the host's chair — the proposal's risk 1.
- The gold moment plays at the frame's own scale (1.00): a 1.15 hold was considered and refused —
  at 1.15 the camera sees 939 world px of height, and the composition from the windows' top (18)
  to the rails' foot (985) is 967, so the couple's windows would land with their tops cut and the
  reveal would need a second pull. The nod 0.4 s later is the emphasis.
- The rails sit at x 32 and 1888 because the last frame is the show's frame; that is outside the
  10 % title-safe inset, as it is on `Main.dc.html`.
- The lower-thirds carry the kit's fictional sample names. `--no-lower-thirds` drops them.
- The sample data is fictional and nothing on the frame says so; the seats are empty (no busts).
