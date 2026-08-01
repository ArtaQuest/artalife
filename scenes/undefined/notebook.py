#!/usr/bin/env python3
"""Assemble the publishable notebook from generate.py.

The notebook is the submission, and it is ALSO the article — the prose between
the code is not decoration, it is the piece anyone will actually read.

Constraints it has to satisfy, all from a strict reproducibility checklist:
  * stdlib only — no pip install to pin
  * no wall clock, no unseeded RNG
  * writes its output to the working directory
  * no tracebacks in the log, even caught ones

`cells.json` is the authored partition of generate.py into titled sections: the
narrative order, which is not the same as the file's order of definition. It is
a second copy of the code, so it can drift — the assertion below is what stops
that silently. A cell body must appear VERBATIM in generate.py, or the notebook
would publish code that no longer produces the film.
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).parent
groups = json.loads((HERE / "cells.json").read_text())
source = (HERE / "generate.py").read_text()
for name, body in groups:
    if body.strip() not in source:
        sys.exit(f"cells.json has drifted from generate.py at: {name}")
# the import line sits above the first section marker, so the split drops it
groups[0][1] = "import math, os, re\n\n" + groups[0][1]

def md(t):   return {"cell_type": "markdown", "metadata": {}, "source": t}
def code(t): return {"cell_type": "code", "metadata": {}, "execution_count": None,
                     "outputs": [], "source": t}

cells = [md("""# Undefined

A fifty-second silent film about the one division you are not allowed to do.

A stick figure shoves a `1` into place. A second `1` falls out of the sky. A `+`
and an `=` arrive on their own, a `2` pops out, and the figure jumps. Then it
gets curious: it tears the `+` out and hurls it away, catches a falling `÷`, and
plants it. `1 ÷ 1 = 1`. Fine. It rips out the second `1`, catches a falling `0`,
plants that instead — and the answer slot **stays empty**.

It taps the empty box. Twice. Nothing. Then the box cracks, and blue light comes
out of it.

The figure hauls the `0` back out, and sets it down on the *other* side of the
division sign, where the `1` used to be:

    0 ÷ 1 = 0

Same two symbols, opposite order. One of them is undefined; the other is just
zero. Nobody says a word.

---

**The output of this notebook is `scene.svg` — that file is the film.** Not a
recording of it: the drawing itself, animated, playing in an `<img>`. It is 168
KB, it loops seamlessly, and it re-renders at whatever size you view it, so the
hairlines are exactly as crisp on a phone as on a desktop."""),

    md("""## Why a drawing instead of a video

A 1080-wide video shown in a 430-wide card has to be resampled down by the
browser, and thin lines are what that destroys first — the codec is barely
involved. A vector scene has no such problem: the renderer draws it at the size
you are looking at.

That decision sets every constraint below, because the file has to survive a
publication gate that parses and rebuilds it against a strict allow-list:

| Constraint | Consequence for the animation |
|---|---|
| Rendered in an `<img>` | Scripts never execute. All motion is **SMIL**. |
| No `<filter>` element | No blur, no glow. Every light source is a `radialGradient`. |
| No external references | Glyphs are hand-drawn paths, not text in a font. |
| Parsed and rebuilt on publish | The file must be a byte-exact fixed point of the sanitiser. |

Everything here is Python standard library — `math`, `os`, `re`. No installs, no
data sources, no network, no clock, no randomness. Run it anywhere and it emits
the same drawing."""),

    md("""## Three rules that decide whether it reads as animation

Most of the work in this notebook is not drawing. It is the three rules below,
each of which was added after watching the thing fail without it.

**1. Hold on twos, but only while calm.** The figure is `calcMode="discrete"` —
no interpolation, so each sample *is* a drawing, the way hand-drawn animation
works. Holding each drawing for two frames is the traditional cadence. But a
walk at 2.8 strides per second on twos is four drawings per cycle, and the legs
scribble. So the cadence is not fixed: `figure_pose` measures how far any joint
travels between drawings and drops to singles above a threshold.

**2. A mirror flip only reads as a turn on a held pose.** A stick figure has no
face, so turning it round is just negating every joint angle. Do that mid-stride
and the figure appears to invert. Every direction change here gets a pivot beat
so the flip lands between two settled, near-symmetric poses.

**3. A held pose must still move.** On discrete twos, a settled figure is one
drawing shown for several seconds — a literally frozen frame. So a resting
figure breathes, shifts its weight and drifts its head, at an amplitude that
falls to zero the moment it is genuinely moving. The breath lengthens the spine
rather than lifting the hip, because scaling the legs would raise the feet off
the ground line.""")]

titles = {
    "Constants, the beat clock, and easing": """## The beat clock

Every event in the film is one named entry in a single dictionary, so retiming a
beat is a one-line edit and nothing can drift out of sync with it. Glyphs sit
200 units apart and the figure only ever comes to rest on a gap centre `G1..G4`
— at 160 apart it stood elbow-to-elbow with every glyph and the silhouettes
merged into an unreadable smudge.""",
    "The figure: a jointed skeleton": """## The figure

Six drawable parts resolved by forward kinematics from joint angles. `face = -1`
mirrors the whole figure by negating every angle, which is all a stick figure
needs in order to turn around.""",
    "Blocking: the performance, as a list of timed segments": """## The performance

An ordered list of `(start, pose function)` segments, built through helpers
rather than written out flat, so rules 2 and 3 above are enforced by
construction instead of remembered.""",
    "Glyphs and the SVG document model": """## Glyphs, and emitting the file

The digits and operators are stroked paths on a 140-unit cap height, drawn by
hand so the file depends on no font. `check_path` re-tokenises every path the
way a browser would and asserts it says what it was meant to say — the compact
encoding is exactly the sort of thing that is wrong in one frame out of a
thousand, and a browser answers a malformed value list by silently ignoring it,
so a limb just stops moving and nothing reports it.""",
    "Choreography: the props, the void, the camera": """## The props, the void, and the camera

Glyphs are physical objects: they fall, they are caught, they squash on impact
and stretch along a fall. The stretch is the only motion blur available — with
`<filter>` unavailable there is nothing else — and it is what animators draw by
hand anyway.

The camera is treated as a character: it pushes in on the empty slot as the
figure starts to worry about it, and yanks out when the void opens.""",
    "Assembly, and the continuity lint": """## Assembly, and checking the result

The lint at the end samples every animated track and reports the largest change
between consecutive drawings. A teleport, a limb popping 70° in one frame, or a
gesture cut off mid-swing all show up here as a single large number, and every
one of those was a real defect this caught.""",
}

for name, body in groups:
    cells.append(md(titles[name]))
    cells.append(code(body.rstrip()))

cells.append(md("""## Emit the film

`scene.svg` is the deliverable. The checks below are the ones that matter: the
loop must close (the last drawing has to equal the first, or the seam shows on
every repeat), and every path in the file must re-tokenise correctly."""))

cells.append(code('''svg = serialise(None)
with open("scene.svg", "w") as f:
    f.write(svg)

# The loop must close: the stage opacity is zero at both ends, so a viewer never
# sees the cut. Assert it rather than trusting it.
assert abs(stage(0.0)) < 1e-9 and abs(stage(DUR)) < 1e-9, "loop seam is visible"

# Re-tokenise every path in the finished file, not just the ones poly() built.
paths = re.findall(r\'\\bd="([^"]+)"\', svg) + [
    v for a in re.findall(r\'attributeName="d" values="([^"]+)"\', svg) for v in a.split(";")]
for d in paths:
    check_path(d)

print(f"scene.svg     {len(svg):,} bytes")
print(f"duration      {DUR:g}s, seamless loop")
print(f"paths checked {len(paths):,}")
print(f"tracks        {len(LINT)} animated")
lint()'''))

cells.append(md("""## What this does not do

It is silent. The reference for this idiom carries a great deal of its weight in
sound design, and a drawing cannot hold audio; watched without sound, this is
noticeably thinner than the thing it is answering to.

It also does not execute in the reader's browser in any sense beyond declarative
animation. There is no script in the file, and there could not be — the format
it is delivered in does not run one."""))

nb = {"cells": cells,
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                  "name": "python3"},
                   "language_info": {"name": "python", "version": "3.11.0"}},
      "nbformat": 4, "nbformat_minor": 5}

out = HERE / "undefined.ipynb"
out.write_text(json.dumps(nb, indent=1))
print(f"{out.name}: {len(cells)} cells, {out.stat().st_size:,} bytes")
