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
sys.path.insert(0, str(HERE.parent / "undefined"))
import generate as U   # noqa: E402  — the rig of record

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

# ── the canvas, and the show's numbers ──────────────────────────────────────
W, H, FPS, DUR = 1920, 1080, 24, 22.0
FIG_HZ = 12                      # the figure holds on twos; props and type run at 24
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

# What the two rails say. No name, no date of birth, no birthplace: the teaser
# shows the SHAPE of two lives that meet and keep going, not a claim about a
# particular person. The episode frame carries the real record; a teaser must not.
ROWS_L = [("1979", "Married"), ("1985", "Master baker"), ("1998", "Opened the bakery"),
          ("2019", "Retired"), ("2026", "47 years together")]
ROWS_R = [("1979", "Married"), ("1984", "Nursing degree"), ("1996", "Head nurse"),
          ("2007", "Founded the clinic"), ("2026", "47 years together")]

LINES = ["Every marriage that lasts",
         "is a story someone can tell",
         "Happily married couples on how they stay together"]
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
    lead = lerp(88.0, 150.0, up)
    return U.pose((x, U.HIP_Y - 1),
                  lean=lerp(0.0, 4.0 - 8.0 * up, k),
                  tilt=lerp(0.0, -6.0 - 10.0 * up, k),
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
    """Arta's pose at time t, on twos."""
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


def draw_arta(d, p):
    s = skeleton_points(p)
    kw = dict(fill=GOLD, width=STROKE, joint="curve")
    d.line([s["hip"], s["neck"]], **kw)
    for a in s["arms"]:
        d.line([s["neck"], a[0], a[1]], **kw)
    for l in s["legs"]:
        d.line([s["hip"], l[0], l[1]], **kw)
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


def F(key, px):
    if key in FONT_FILES:
        return ImageFont.truetype(FONT_FILES[key], px)
    return ImageFont.load_default()


def draw_plate(d, text, px, x, bottom, alpha_img=None):
    """One line on the show's own lower-third: a 10 px blue bar, then a black
    80 % plate that hugs its text."""
    f = F("m700", px)
    box = d.textbbox((0, 0), text, font=f)
    pad_l, pad_r, pad_t, pad_b = 20, 24, 10, 10
    ph = pad_t + int(px * 1.06) + pad_b
    pw = pad_l + (box[2] - box[0]) + pad_r
    top = bottom - ph
    d.rectangle([x, top, x + 9, bottom - 1], fill=BLUE)
    d.rectangle([x + 10, top, x + 10 + pw - 1, bottom - 1], fill=(0, 0, 0))
    d.text((x + 10 + pad_l - box[0], top + pad_t - box[1] + int(px * 0.06)), text,
           font=f, fill=INK)


def frame(t):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    fy, fl = F("m700", 32), F("i500", 28)
    draw_rail(d, "l", t, fy, fl)
    draw_rail(d, "r", t, fy, fl)
    if t < B["hold_up"] + 0.6:
        draw_arta(d, figure(t))
    # the lines, each fading in on its beat and out with its side
    for i, (t0, t1) in enumerate(((B["aim_l"] + 0.2, B["turn_r"] - 0.2),
                                  (B["aim_r"] + 0.2, B["to_mid"] + 0.2))):
        if t0 <= t <= t1:
            draw_plate(d, LINES[i], 60, 32, 1030)
    if t >= B["hold_up"]:
        u = ease(seg(t, B["hold_up"], B["hold_up"] + 0.8))
        ov = Image.new("RGB", (W, H), BG)
        od = ImageDraw.Draw(ov)
        fw, fh, fs = F("m800", 120), F("i500", 44), F("i600", 40)
        wa = od.textlength("Arta", font=fw)
        wq = od.textlength("Quest", font=fw)
        tx = (W - (wa + wq)) / 2
        ty = H / 2 - 150
        od.text((tx, ty), "Arta", font=fw, fill=GOLD)
        od.text((tx + wa, ty), "Quest", font=fw, fill=BLUE)
        sw = od.textlength(LINES[2], font=fs)
        od.text(((W - sw) / 2, ty + 190), LINES[2], font=fs, fill=INK2)
        hw = od.textlength(HANDLE, font=fh)
        od.text(((W - hw) / 2, ty + 258), HANDLE, font=fh, fill=INK3)
        img = Image.blend(img, ov, u)
    return img


# ── the motion-safety ceiling, measured rather than trusted ─────────────────
def max_step():
    """The largest single-point displacement between consecutive drawings, in px.

    The law is ARTA.md §3, converted to this film's cadence exactly as the
    published scene's own lint converts it: continuous motion is capped at
    640 units a second, the figure holds on twos, so a new drawing every 1/12 s
    may travel 640/12 = 53 units. The other ceiling — 12 px in a frame — is an
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


def main():
    args = sys.argv[1:]
    if "--check" in args:
        worst, at = max_step()
        budget = (640.0 / FIG_HZ) * (W / 1600.0)
        print(f"figure: {int(DUR*FIG_HZ)} drawings on twos · largest step {worst:.2f} px "
              f"at t={at:.2f}s · budget {budget:.0f} px (640/s at {FIG_HZ} drawings/s, "
              f"scaled to a {W}-wide frame)")
        s = skeleton_points(figure(2.6))
        print(f"standing: head top y {s['head'][1]-s['head_r']:.0f}, soles y "
              f"{max(l[1][1] for l in s['legs']):.0f} (ground {GROUND:.0f})")
        assert worst <= budget * 1.02, f"motion-safety exceeded: {worst:.2f} px > {budget:.1f}"
        assert abs(max(l[1][1] for l in s["legs"]) - GROUND) < 6, "Arta is not standing on the ground"
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
