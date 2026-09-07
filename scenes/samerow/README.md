# The Same Row — the ArtaQuest channel teaser

16 s · 384 frames · 24 fps · 1920 × 1080. Arta stands dead centre on a hairline in the dark and
fires one arrow at the left edge and one at the right; a life draws itself down each edge in the
show's own rails and type; the couple's two windows fall in above, the host's window lands around
Arta, and on both rails at once the one year they share — 1979 — turns gold. The last held frame
is the show's frame (`design/artapodcast/final/Main.dc.html`: couple windows 912 × 513 at (32, 18)
and (976, 18), host 640 × 360 at (640, 625), rails at x 32..608 and 1312..1888 on a 64 px pitch,
blue-bar lower-thirds), then a 0.8 s fade. No end card, no wordmark.

This is the design that won the judged competition (proposal "The Same Row"), built from scratch;
nothing is taken from the rejected `scenes/teaser/`.

## How it is drawn

- **One rig.** `scenes/undefined/generate.py` is imported by path under the name `arta_rig`, so the
  skeleton (spine 70 · neck 24 · head r20 · thigh/shin 52 · arm 34/32), joint convention, IK and
  proportions are the published film's. Figure scale 1.73 (377 px, 35 % of the frame at 1:1),
  stroke 8 rig units, gold, round caps and joins, no fillet.
- **SVG, rasterised in the lab Chrome.** Each frame is ONE SVG — ambient, hairline, windows,
  lower-thirds, rails, rows, figure, arrow, camera transform, vignette — written by `generate.py`
  and screenshotted by `render.mjs` over CDP `127.0.0.1:9222` (the parked ArtaFocus lab, the same
  route as `shot.mjs`; nothing ever opens in the operator's browser). Fonts (Montserrat 700,
  Inter 500/600) are embedded from `../teaser/fonts` as data URIs so the render is network-free.
- **The frame is read off the kit, not invented.** Every coordinate of the last frame comes from
  `Main.dc.html` / `Spec.dc.html` §3 and §10; the final frame was checked against a `shot.mjs`
  render of `Main.dc.html` and the type lands on the same pixels.
- **The arrow is brand blue `#1746DC`** — the proposal's `#4A72FF` is a third colour and is not
  used. Two colours only: gold `#E8B923` and blue `#1746DC` on `#010C17` / `#0C1E32`, inks
  `#F4F4F5` / `#A6A8B0` / `#8B8E98`.
- **Rows rise per `final/MOTION-SPEC.md`:** opacity 0→1 with translateY 24→0 over 0.3 s on
  cubic-bezier(0, 0, 0.58, 1), one row every 0.44 s as the rail's tip passes its tick, so the rises
  overlap and no frame of a list beat is still. The gold moment uses the kit's own durations: tick
  0.3 s, gold line 0.6 s, row colours 0.3 s.
- **The camera** is one camera, monotonic in scale, three framings: A (1.40, his side + Arta),
  B (1.32, her side + Arta), C (1.00, the frame). It is authored under the motion law like the
  figure.

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
   governor does not have to act, and `--check` prints how often it did.
2. **Head — intrusion.** Every limb is sampled at one rig unit; samples within 13 units of the
   neck are a shoulder and ignored; no sample may lie inside the ring's outer edge
   (`HEAD_R + STROKE/2 = 24`). A "centre-line ≥ radius" rule cannot go green because the arms
   root 24 units from the head centre; this one passes stand, point, fold and the solved think,
   and flags the film's own cheer and lift. The think pose is solved against it: hand under the
   head where a chin would be, 28 units from its centre, elbow below the shoulder.
3. **Labels.** No figure ink (stroke included) inside a live row's text box on any frame; boxes
   are measured in the browser (`metrics.json`).
4. **Aim.** At each fire the forearm lies on the line from the neck to the mark it hits (the
   `face` is carried by the pose, so `point()` aims where it is told — the sign bug that made the
   last teaser turn left and point right is fixed at its cause).
5. **Frame.** On the last held frame all three windows are seated, the vignette, ambient and
   hairline are gone.

Stated exceptions, in `manifest.json`: the arrow is a tool, not a drawn point of the figure — it
flies 50 world px/frame against a 100 px shaft, so consecutive drawings overlap by half; the
windows are slabs with mass (ease-in 0.55 s, 8 px overshoot, 0.18 s settle). A walk was not added:
under the 12 px law a lawful root speed at this scale is ~65 px/s, which is not a walk.

## Notes for the operator

- Arta stands in the host's window. The window is an empty placeholder, nothing is drawn OVER a
  host, but it reads as Arta in the host's chair — the proposal's risk 1.
- The rails sit at x 32 and 1888 because the last frame is the show's frame; that is outside the
  10 % title-safe inset, as it is on `Main.dc.html`.
- The lower-thirds carry the kit's fictional sample names. `--no-lower-thirds` drops them.
- The sample data is fictional and nothing on the frame says so; the seats are empty (no busts).
