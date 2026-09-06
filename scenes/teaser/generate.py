#!/usr/bin/env python3
"""
"Two lives" — the 22-second teaser for the ArtaQuest interview show.

Arta stands where the host will stand, and aims at what matters: first at one
side of the screen, where a life draws itself as a gold rail of years, then at
the other, where a second life does the same. At the end both rails reach the
same row and Arta aims up at the name.

ONE RIG, ONE MASCOT. Every joint here comes from `scenes/undefined/generate.py`
— the same skeleton, proportions, joint convention, walk cycle and motion-safety
ceiling as the published film and as the live mascot in `src/rig/arta.ts`. This
file adds a performance and a camera; it does not add a character.

The medium differs and that is deliberate (ARTA.md §4): the published scene is an
SVG that holds each drawing on twos, and so does the figure here — the pose is
sampled at 12 Hz while the props and type run at 24. What is different is the
output: a teaser is a video, so the frames are rasterised with PIL rather than
serialised as SMIL. A held drawing reads as drawn in either medium.

The rest of the frame is the SHOW's own geometry, not this repo's invention: the
two timeline rails sit at the coordinates the episode frame puts them at, and the
lines are set on the show's lower-third — a 10 px blue bar and a black 80 % plate.
Those numbers live in the ArtaQuest YouTube kit's editor spec, section 3, and are
repeated here as constants so this file renders on its own.

Usage:  python3 generate.py                 -> frames/*.png (all 528) + poster
        python3 generate.py --frames 0 12 …  -> only those frame numbers
        python3 generate.py --check          -> geometry and motion-safety selftest
"""

import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# THE RIG, LOADED BY PATH RATHER THAN BY NAME. `import generate` looks wrong only when it works:
# the sibling scene's file is also called generate.py, so once anything imports THIS file as
# `generate` — which a notebook does — `import generate` returns this module and the rig resolves
# to itself. It ran perfectly as a script and died on Kaggle at the first joint. A path and a
# unique module name cannot be shadowed.
import importlib.util   # noqa: E402
_rig = HERE.parent / "undefined" / "generate.py"
_spec = importlib.util.spec_from_file_location("arta_rig", _rig)
U = importlib.util.module_from_spec(_spec)
sys.modules["arta_rig"] = U
_spec.loader.exec_module(U)   # the rig of record: same skeleton, same walk, same law

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

# ── the canvas, and the show's numbers ──────────────────────────────────────
W, H, FPS, DUR = 1920, 1080, 24, 22.0
FIG_HZ = 24                      # EVERY FRAME. ARTA.md §4 holds the film on twos and the
                                 # mascot smooth, and says both are right for their medium.
                                 # This is watched as video, which is the mascot's medium:
                                 # a held drawing that reads as "drawn" in an SVG scene reads
                                 # as a dropped frame in an MP4.
GROUND = 985.0                   # the episode frame's host window ends here
SCALE = 1.39                     # Arta stands 300 px tall in a 1080 frame
STROKE = 11                      # 8 rig units at this scale — the film's own line

BG = (1, 12, 23)                 # #010C17, the frame ground
GOLD = (232, 185, 35)            # #E8B923 — Arta's colour in both themes
BLUE = (23, 70, 220)             # #1746DC
INK, INK2, INK3 = (244, 244, 245), (166, 168, 176), (139, 142, 152)

# The kit's timeline geometry (editor spec §3): two 576-wide boxes on the bare
# ground either side of the host, rails on the frame's OUTER edges.
TL_L_X, TL_R_X, TL_W = 32, 1312, 576
TL_TOP, PITCH = 613, 64
RAIL_DX, RAIL_W, TICK_W, TICK_H, CUR_W = 9, 6, 24, 6, 34
BRAND_YEAR_PX, BRAND_LABEL_PX = 32, 28

# What the two rails say. No name, no date of birth, no birthplace: the teaser
# shows the SHAPE of two lives that meet and keep going, not a claim about a
# particular person. The episode frame carries the real record; a teaser must not.
ROWS_L = [("1979", "Married"), ("1985", "Master baker"), ("1998", "Opened the bakery"),
          ("2019", "Retired"), ("2026", "47 years together")]
ROWS_R = [("1979", "Married"), ("1984", "Nursing degree"), ("1996", "Head nurse"),
          ("2007", "Founded the clinic"), ("2026", "47 years together")]

# No narrative copy: the timeline carries the film. The only words are the years and milestones
# on the rails, and the handle at the end.
HANDLE = "youtube.com/@ArtaQuest"

# ── the beat clock ──────────────────────────────────────────────────────────
# Arta walks in, aims left, aims right, walks to the middle and aims up. Five
# beats in twenty-two seconds is slow on purpose: the show is about people who
# did the same thing for forty years, and a teaser that hurries argues against it.
B = dict(walk_in=0.0, arrive=2.8, settle=3.4,
         turn_l=3.4, aim_l=4.2, rows_l=5.0, drop_l=8.3,
         turn_r=9.0, aim_r=9.8, rows_r=10.6, drop_r=13.9,
         to_mid=14.6, mid=16.0, aim_up=16.4, hold_up=18.0, end=22.0)
ROW_EVERY = 0.8

# Arta walks in once and then holds its ground: aiming left and aiming right happen
# from the SAME spot, because moving between them meant a 122 px jump between two
# drawings — nine times the motion-safety budget, and the selftest said so.
X_IN, X_MID = 620.0, 960.0


def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def seg(t, a, b):
    return 0.0 if t <= a else (1.0 if t >= b else (t - a) / (b - a))


def ease(u):
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


# ── the poses this film needs, built with the rig's own `pose` ──────────────
# Joint convention (ARTA.md §1): degrees, 0 is straight down, positive rotates
# toward +x. So a lead arm at 88 is horizontal, and at 150 it points up-forward.
def place(p):
    """Put a rig pose on THIS film's ground. The rig measures its hip height above
    its own ground line; scaling that is the only correct way to keep the soles on
    ours. Placing the hip by a constant put Arta 39 px underground, which the
    selftest caught before a single frame was rendered."""
    q = dict(p)
    q["hip"] = (p["hip"][0], GROUND - (U.GROUND - p["hip"][1]) * SCALE)
    return q


def P_stand(x):
    return U.pose((x, U.HIP_Y), face=1)


def P_aim(x, face=1, k=1.0, up=0.0):
    """The signature gesture: Arta points at what matters. `k` eases the arm out
    of a stand, `up` swings the aim from horizontal to up-forward."""
    lead = lerp(88.0, 137.0, up)
    return U.pose((x, U.HIP_Y - 1),
                  lean=lerp(0.0, 4.0 - 20.0 * up, k),
                  tilt=lerp(0.0, -6.0 - 22.0 * up, k),
                  face=face,
                  la=(lerp(9, lead, k), lerp(12, 4, k)),
                  ra=(lerp(-9, -46, k), lerp(-12, -34, k)),
                  ll=(lerp(3, 15, k), lerp(-5, -11, k)),
                  rl=(lerp(-3, -13, k), lerp(-5, -7, k)))


def P_walk_to(t, t0, t1, x0, x1, face):
    """The rig's own walk, its own stride, its own settle into a stand."""
    u = seg(t, t0, t1)
    n = max(1, round(abs(x1 - x0) / U.STRIDE))
    x = lerp(x0, x1, U.trapz(u))
    p = U.P_walk(x, (u * n) % 1.0, face)
    if u > 0.86:
        p = U.blend(p, P_stand(x), ease((u - 0.86) / 0.14))
    return p


def facing(t):
    """Facing is a continuous value, never a boolean: negating every joint in one
    frame moves a foot ~43 px, the largest gradient in the system and the one no
    blend can soften (ARTA.md §3). Each turn is eased through zero, so the figure
    narrows to its own profile, passes edge-on and opens out the other way."""
    f = 1.0
    for t0, t1, to in ((B["turn_l"] - 0.5, B["turn_l"] + 0.3, -1.0),
                       (B["turn_r"] - 0.5, B["turn_r"] + 0.3, 1.0)):
        if t >= t0:
            f = lerp(f, to, ease(seg(t, t0, t1)))
    return f


def figure(t):
    """Arta's pose at time t.

    The quantiser is an exact no-op while FIG_HZ equals FPS, which is the point: it is the single
    line that would put the figure back on the published film's cadence, and leaving it in place
    keeps the two mediums one edit apart rather than one rewrite."""
    t = math.floor(t * FIG_HZ) / FIG_HZ
    f = facing(t)
    face = 1 if f >= 0 else -1
    if t < B["arrive"]:
        p = P_walk_to(t, B["walk_in"], B["arrive"], X_IN, X_MID, 1)
    elif t < B["to_mid"]:
        # aim left, hold, drop, aim right, hold, drop — one gesture ramp per side
        k = 0.0
        if t < B["drop_l"]:
            k = ease(seg(t, B["turn_l"] + 0.2, B["aim_l"]))
        elif t < B["turn_r"]:
            k = 1.0 - ease(seg(t, B["drop_l"], B["turn_r"]))
        elif t < B["drop_r"]:
            k = ease(seg(t, B["turn_r"] + 0.2, B["aim_r"]))
        else:
            k = 1.0 - ease(seg(t, B["drop_r"], B["to_mid"]))
        p = P_aim(X_MID, face, k)
    else:
        k = ease(seg(t, B["aim_up"], B["hold_up"]))
        p = P_aim(X_MID, 1, k, up=k)
    # Facing is applied as the continuous value the guide requires: the pose is
    # built at face ±1 and the whole figure is narrowed toward its own profile
    # while |f| is small, which is what a real turn looks like from the side.
    p = place(p)
    p["face_blend"] = f
    return p


def skeleton_points(p):
    """Every drawn point of the figure, in frame coordinates."""
    s = U.skeleton(p)
    hx, hy = p["hip"]
    nx = abs(p.get("face_blend", p["face"]))
    nx = clamp(nx, 0.12, 1.0)                      # edge-on, never a zero-width line

    def P(q):
        return (hx + q[0] * SCALE * nx, hy + q[1] * SCALE)

    return dict(hip=(hx, hy), neck=P(s["neck"]), head=P(s["head"]),
                arms=[[P(q) for q in a] for a in s["arms"]],
                legs=[[P(q) for q in l] for l in s["legs"]],
                head_r=U.HEAD_R * SCALE)


FILLET = 16.0        # px of bend at an elbow or a knee


def _fillet(pts, r=FILLET, steps=9):
    """A limb as a smooth chain: straight into the joint, a quadratic through it, straight out.

    PIL's round line-join rounds the OUTSIDE of a corner by the stroke width and nothing more, so
    an elbow stays a hard angle however wide the line is. Bending the limb itself is what makes a
    joint read as a joint, and it is the difference the operator saw as "broken"."""
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        v1 = (a[0] - b[0], a[1] - b[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        n1 = math.hypot(*v1) or 1.0
        n2 = math.hypot(*v2) or 1.0
        r1, r2 = min(r, n1 / 2), min(r, n2 / 2)
        p1 = (b[0] + v1[0] / n1 * r1, b[1] + v1[1] / n1 * r1)
        p2 = (b[0] + v2[0] / n2 * r2, b[1] + v2[1] / n2 * r2)
        out.append(p1)
        for k in range(1, steps):
            u = k / steps
            w = (1 - u) ** 2
            out.append((w * p1[0] + 2 * (1 - u) * u * b[0] + u * u * p2[0],
                        w * p1[1] + 2 * (1 - u) * u * b[1] + u * u * p2[1]))
        out.append(p2)
    out.append(pts[-1])
    return out


def draw_arta(d, p):
    s = skeleton_points(p)
    kw = dict(fill=GOLD, width=STROKE, joint="curve")
    d.line(_fillet([s["hip"], s["neck"]]), **kw)
    for a in s["arms"]:
        d.line(_fillet([s["neck"], a[0], a[1]]), **kw)
    for l in s["legs"]:
        d.line(_fillet([s["hip"], l[0], l[1]]), **kw)
    r = s["head_r"]
    d.ellipse([s["head"][0] - r, s["head"][1] - r, s["head"][0] + r, s["head"][1] + r],
              outline=GOLD, width=STROKE)


# ── the two rails: the show's own timeline, drawn where an episode draws it ──
def rows_shown(t, side):
    t0 = B["rows_l"] if side == "l" else B["rows_r"]
    n = clamp(int((t - t0) / ROW_EVERY) + 1, 0, 5) if t >= t0 else 0
    # the last row is held back until both sides are done, so they land together
    if n >= 5 and t < B["mid"]:
        n = 4
    return int(n)


def draw_rail(d, side, t, fy, fl):
    rows = ROWS_L if side == "l" else ROWS_R
    bx = TL_L_X if side == "l" else TL_R_X
    shown = rows_shown(t, side)
    if shown <= 0:
        return
    rail_x = bx + RAIL_DX if side == "l" else bx + TL_W - RAIL_DX - RAIL_W
    first_c = TL_TOP + PITCH // 2
    last_c = first_c + PITCH * (len(rows) - 1)
    t0 = B["rows_l"] if side == "l" else B["rows_r"]
    grow = clamp((t - t0) / (ROW_EVERY * (len(rows) - 1)), 0.0, 1.0)
    d.rectangle([rail_x, first_c - 3, rail_x + RAIL_W - 1, last_c + 2], fill=INK3)
    gold_to = first_c + (last_c - first_c) * ease(grow)
    d.rectangle([rail_x, first_c - 3, rail_x + RAIL_W - 1, int(gold_to) + 2], fill=GOLD)
    for i, (yr, lab) in enumerate(rows[:shown]):
        cy = first_c + PITCH * i
        cur = (i == shown - 1)
        col = INK if cur else INK2
        if side == "l":
            d.rectangle([bx, cy - 3, bx + TICK_W - 1, cy + 2], fill=GOLD)
            x = bx + 40
            d.text((x, cy - 23), yr, font=fy, fill=col)
            d.text((x + d.textlength(yr, font=fy) + 16, cy - 22), lab, font=fl, fill=col)
            if cur:
                d.rectangle([bx, cy - 3, bx + CUR_W - 1, cy + 2], fill=GOLD)
        else:
            rx = bx + TL_W
            d.rectangle([rx - TICK_W, cy - 3, rx - 1, cy + 2], fill=GOLD)
            yw = d.textlength(yr, font=fy)
            d.text((rx - 40 - yw, cy - 23), yr, font=fy, fill=col)
            lw = d.textlength(lab, font=fl)
            d.text((rx - 40 - yw - 16 - lw, cy - 22), lab, font=fl, fill=col)
            if cur:
                d.rectangle([rx - CUR_W, cy - 3, rx - 1, cy + 2], fill=GOLD)


# ── the type: the show's lower-third, and the closing lockup ────────────────
def fonts():
    """Montserrat and Inter, or the run says so rather than setting in a fallback."""
    d = HERE / "fonts"
    out = {}
    for key, files in (("m700", ("Montserrat-700.ttf",)), ("m800", ("Montserrat-800.ttf",)),
                       ("i500", ("Inter-500.ttf",)), ("i600", ("Inter-600.ttf",))):
        for f in files:
            p = d / f
            if p.exists():
                out[key] = str(p)
    return out


FONT_FILES = fonts()


SS = 3               # supersample factor: draw at 3x, resample down with LANCZOS


def F(key, px):
    """A font at DRAWING size — every caller works in frame units and the pen scales."""
    if key in FONT_FILES:
        return ImageFont.truetype(FONT_FILES[key], int(round(px * SS)))
    return ImageFont.load_default()


class Pen:
    """ImageDraw in frame coordinates, drawing into an SS-times-larger canvas.

    PIL will not anti-alias a line or an ellipse: it fills whole pixels, so a limb at any angle but
    0 or 45 degrees is a staircase and a 6 px rail tick has hard corners. Supersampling is the fix,
    and putting it behind a pen keeps every coordinate in this file honest — the geometry stays in
    the frame units the kit's spec is written in, and only the pen knows about SS."""

    def __init__(self, d, s=SS):
        self.d, self.s = d, s

    def _p(self, pts):
        return [(x * self.s, y * self.s) for x, y in pts]

    def line(self, pts, fill=None, width=1, joint=None):
        self.d.line(self._p(pts), fill=fill, width=max(1, int(round(width * self.s))), joint=joint)

    def rectangle(self, box, fill=None):
        x0, y0, x1, y1 = box
        # +1 on the far edge: a rectangle in pixel coordinates is inclusive, so scaling the
        # corners alone would shrink every bar by SS-1 subpixels and thin the rails.
        self.d.rectangle([x0 * self.s, y0 * self.s,
                          (x1 + 1) * self.s - 1, (y1 + 1) * self.s - 1], fill=fill)

    def ellipse(self, box, outline=None, width=1):
        x0, y0, x1, y1 = box
        self.d.ellipse([x0 * self.s, y0 * self.s, x1 * self.s, y1 * self.s],
                       outline=outline, width=max(1, int(round(width * self.s))))

    def text(self, xy, txt, font=None, fill=None):
        self.d.text((xy[0] * self.s, xy[1] * self.s), txt, font=font, fill=fill)

    def textlength(self, txt, font=None):
        return self.d.textlength(txt, font=font) / self.s

    def textbbox(self, xy, txt, font=None):
        b = self.d.textbbox((xy[0] * self.s, xy[1] * self.s), txt, font=font)
        return tuple(v / self.s for v in b)


def frame(t):
    """One frame, drawn at SS times the size and resampled down.

    There is no narrative copy on it. The timeline is the story — two lives that begin apart, meet
    in the same year and keep going — and a line of type over it would say the same thing worse.
    The only words are the years and the milestones on the rails, which ARE the timeline, and the
    name at the end."""
    big = Image.new("RGB", (W * SS, H * SS), BG)
    d = Pen(ImageDraw.Draw(big))
    fy, fl = F("m700", BRAND_YEAR_PX), F("i500", BRAND_LABEL_PX)
    draw_rail(d, "l", t, fy, fl)
    draw_rail(d, "r", t, fy, fl)
    # Drawn until the end card has fully covered it: cutting the figure DURING the dissolve
    # pops, because the frame under a partly-transparent overlay is still visible.
    if t < B["hold_up"] + 0.9:
        draw_arta(d, figure(t))
    if t >= B["hold_up"]:
        # The sign-off: the wordmark and the handle, nothing else. It fades up over the finished
        # rails rather than cutting, so the last thing on screen is still the two lives.
        u = ease(seg(t, B["hold_up"], B["hold_up"] + 0.9))
        ov = Image.new("RGB", (W * SS, H * SS), BG)
        od = Pen(ImageDraw.Draw(ov))
        fw, fh = F("m800", 120), F("i500", 44)
        wa = od.textlength("Arta", font=fw)
        wq = od.textlength("Quest", font=fw)
        tx = (W - (wa + wq)) / 2
        ty = H / 2 - 96
        od.text((tx, ty), "Arta", font=fw, fill=GOLD)
        od.text((tx + wa, ty), "Quest", font=fw, fill=BLUE)
        hw = od.textlength(HANDLE, font=fh)
        od.text(((W - hw) / 2, ty + 190), HANDLE, font=fh, fill=INK3)
        big = Image.blend(big, ov, u)
    return big.resize((W, H), Image.LANCZOS)


# ── the motion-safety ceiling, measured rather than trusted ─────────────────
def max_step():
    """The largest single-point displacement between consecutive drawings, in px.

    The law is ARTA.md §3, converted to this film's cadence exactly as the
    published scene's own lint converts it: continuous motion is capped at
    640 units a second, so a new drawing every 1/FIG_HZ s may travel 640/FIG_HZ
    units — 53 on twos, 27 at every frame. The other ceiling — 12 px in a frame — is an
    anti-strobe rule for 60 Hz-class motion and does not transfer to a film on
    twos; asserting it here failed a perfectly good walk. Units are this
    composition's own, so the film's 1600-wide canvas scales to our 1920."""
    prev, worst, at = None, 0.0, 0.0
    for i in range(int(DUR * FIG_HZ)):
        t = i / FIG_HZ
        s = skeleton_points(figure(t))
        pts = [s["hip"], s["neck"], s["head"]] + [q for a in s["arms"] for q in a] \
            + [q for l in s["legs"] for q in l]
        if prev:
            m = max(math.dist(a, b) for a, b in zip(prev, pts))
            if m > worst:
                worst, at = m, t
        prev = pts
    return worst, at


HEAD_R_PX = U.HEAD_R * SCALE


def head_clearance():
    """How close any limb's centre-line comes to the head centre, over the whole film.

    A stick figure has no face, so the head is the one shape that must stay legible; a limb drawn
    across it reads as a broken drawing. The aim-up pose crossed it by 2.2 px and nothing measured
    that, because the selftest only ever looked at speed and at the ground."""
    worst = (1e9, 0.0)
    for n in range(int(DUR * FPS)):
        t = n / FPS
        s = skeleton_points(figure(t))
        c = s["head"]
        for chain in ([s["neck"], *s["arms"][0]], [s["neck"], *s["arms"][1]],
                      [s["hip"], *s["legs"][0]], [s["hip"], *s["legs"][1]]):
            for i in range(len(chain) - 1):
                a, b = chain[i], chain[i + 1]
                dx, dy = b[0] - a[0], b[1] - a[1]
                L = dx * dx + dy * dy or 1e-9
                u = max(0.0, min(1.0, ((c[0] - a[0]) * dx + (c[1] - a[1]) * dy) / L))
                d = math.hypot(a[0] + u * dx - c[0], a[1] + u * dy - c[1])
                if d < worst[0]:
                    worst = (d, t)
    return worst


def main():
    args = sys.argv[1:]
    if "--check" in args:
        worst, at = max_step()
        budget = (640.0 / FIG_HZ) * (W / 1600.0)
        print(f"figure: {int(DUR*FIG_HZ)} drawings at {FIG_HZ} Hz · largest step {worst:.2f} px "
              f"at t={at:.2f}s · budget {budget:.0f} px (640/s at {FIG_HZ} drawings/s, "
              f"scaled to a {W}-wide frame)")
        s = skeleton_points(figure(2.6))
        print(f"standing: head top y {s['head'][1]-s['head_r']:.0f}, soles y "
              f"{max(l[1][1] for l in s['legs']):.0f} (ground {GROUND:.0f})")
        assert worst <= budget * 1.02, f"motion-safety exceeded: {worst:.2f} px > {budget:.1f}"
        assert abs(max(l[1][1] for l in s["legs"]) - GROUND) < 6, "Arta is not standing on the ground"
        worst_head = head_clearance()
        print(f"closest a limb comes to the head centre: {worst_head[0]:.1f} px at t={worst_head[1]:.2f}s "
              f"(head radius {HEAD_R_PX:.1f})")
        assert worst_head[0] >= HEAD_R_PX, (
            f"a limb crosses the head at t={worst_head[1]:.2f}s: {worst_head[0]:.1f} px from the centre "
            f"against a {HEAD_R_PX:.1f} px radius")
        print("selftest: PASS")
        return
    out = HERE / "frames"
    out.mkdir(exist_ok=True)
    wanted = [int(x) for x in args[args.index("--frames") + 1:]] if "--frames" in args else \
        list(range(int(DUR * FPS)))
    for n in wanted:
        frame(n / FPS).save(out / f"{n:05d}.png")
    print(f"frames/ {len(wanted)} png at {W}x{H}")


if __name__ == "__main__":
    main()
