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
import random
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
W, H, FPS, DUR = 1920, 1080, 24, 20.0
FADE = 1.2                       # the closing fade, on the finished timeline
FIG_HZ = 24                      # EVERY FRAME. ARTA.md §4 holds the film on twos and the
                                 # mascot smooth, and says both are right for their medium.
                                 # This is watched as video, which is the mascot's medium:
                                 # a held drawing that reads as "drawn" in an SVG scene reads
                                 # as a dropped frame in an MP4.
GROUND = 985.0                   # the episode frame's host window ends here
SCALE = 1.39                     # Arta stands 300 px tall in a 1080 frame
STROKE = 9.7                     # the LIVE mascot's 7 units against its 218-tall figure,
                                 # at this film's 303 px — the same line the site draws

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

# No copy of any kind: the timeline carries the film, and it ends on the timeline rather than on a
# name. The only words in the whole film are the years and milestones on the two rails.

# ── the beat clock ──────────────────────────────────────────────────────────
# Arta walks in, aims left, aims right, and raises the aim over the finished timeline. Four beats
# in twenty seconds is slow on purpose: the show is about people who
# did the same thing for forty years, and a teaser that hurries argues against it.
B = dict(walk_in=0.0, arrive=2.8, settle=4.4,
         turn_l=4.6, aim_l=6.0, rows_l=6.2, drop_l=9.6,
         turn_r=10.4, aim_r=11.8, rows_r=12.0, drop_r=15.4,
         mid=17.0, end=20.0)
# EVERY TRANSITION IS SLOWER THAN THE CAP. The cap blends the previous drawing toward the target in
# a straight line through joint space, so whenever the authored motion is faster than the budget it
# cuts the corner — including the fold that keeps the arm off the face, which is how a limb still
# crossed the head after the routing was added. Authoring inside the budget is what lets the
# routing survive: the cap is then a guarantee that never has to act.
ROW_EVERY = 0.68

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



# ── THE PRODUCTION RIG, transcribed from src/rig/arta.ts ────────────────────
# The film's rig and the live mascot share a skeleton, but not a pose library and not a life. The
# teaser was built on the film's `pose()` with poses invented here, and it showed: a different
# resting arm angle, no breath, and a figure that stood perfectly still for seconds at a time.
# Everything in this block is a faithful transcription of the mascot people actually see on
# artaquest.com — the same numbers, the same names, the same reasons — so the teaser IS Arta
# rather than something built to the same measurements.
STANCE_L, STANCE_R = (7.0, -8.0), (-7.0, -8.0)
SHOULDER_MAX = 116.0
BREATH = 0.42          # Hz. arta.ts: "the one genuinely periodic thing Arta does"


def P(lean=0.0, tilt=0.0, face=1, la=(14, 15), ra=(-14, -15), ll=None, rl=None, sq=1.0, bre=1.0):
    """arta.ts P(): the resting arms are (14, 15) and (-14, -15), NOT the film's (9, 12)."""
    return dict(hip=(0.0, 0.0), lean=lean, tilt=tilt, face=face,
                la=tuple(la), ra=tuple(ra),
                ll=tuple(ll or STANCE_L), rl=tuple(rl or STANCE_R), sq=sq, bre=bre)


def foot_drop(p):
    """How far the lower foot hangs below the hip in THIS pose. arta.ts footDrop().

    Placing the hip at surface - footDrop(pose) is the definition of standing on something, and it
    holds for any pose — which is the point. Every act that plants Arta uses it rather than
    carrying its own hand-tuned offset, because a hand-tuned offset is only right for the pose it
    was tuned against."""
    s = U.skeleton(p)
    return max(l[1][1] for l in s["legs"])


def grounded(p, x):
    """Put a pose's SOLES on this film's ground, at x. arta.ts grounded(), in frame units."""
    q = dict(p)
    q["hip"] = (x, GROUND - foot_drop(p) * SCALE)
    return q


def A_stand():
    return P()


def A_think():
    """arta.ts think(): the hand comes up, the weight goes onto one leg."""
    return P(lean=-6, tilt=8, la=(22, 16), ra=(-132, -52), ll=(14, -10), rl=(-20, -30))


def A_think_fold():
    """The half-way house into the think, and the reason it exists.

    Lerping straight from a hanging arm to the think sweeps the whole arm UP THROUGH THE HEAD —
    measured at 4.5 px from the head centre against a 27.8 px radius. The arm goes OUT to the side
    with the forearm straight, and only then lifts and folds, so it travels round the head rather
    than across it. Folding first was the obvious guess and it was worse: a bent arm sweeping up is
    exactly the shape that clips the face."""
    return P(lean=-3, tilt=4, la=(18, 15), ra=(-70, -10), ll=(14, -10), rl=(-20, -30))


def via_fold(a, b, u):
    """Move between any two arm poses THROUGH the side, never across the face.

    The think has the arm up and back and the point has it out in front; lerping the shoulder
    straight between them drags the forearm over the head. Both legs of the journey go through the
    same half-way house — arm out to the side, forearm straight — which is both what a body does
    and what keeps the limb off the one shape a faceless figure has to keep legible."""
    return blend_pose(a, A_think_fold(), ease(min(1.0, u * 2))) if u < 0.5 else \
        blend_pose(A_think_fold(), b, ease((u - 0.5) * 2))


def to_think(frm, u):
    """Route any pose into the think through the fold, so the arm never crosses the face."""
    return blend_pose(frm, A_think_fold(), ease(min(1.0, u * 2))) if u < 0.5 else \
        blend_pose(A_think_fold(), A_think(), ease((u - 0.5) * 2))


def A_point(deg, face=1):
    """arta.ts point(): the signature. The POINTING arm is `ra`, and the shoulder is clamped so
    the arm folds at the elbow past 116 degrees rather than dislocating."""
    shoulder = max(-SHOULDER_MAX, min(SHOULDER_MAX, deg))
    return P(lean=4, tilt=-6, la=(18, 14),
             ra=(shoulder * face, (deg - shoulder) * face),
             ll=(10, -8), rl=(-12, -8))


class Drift:
    """arta.ts drift(): a slow wander in [-1, 1] — pick a target, ease toward it, pick another.

    It replaced three sines, and the reason is worth keeping: a sum of periodic things is periodic,
    or near enough that a person watching sees the seam. Shifting your weight is not oscillation
    anyway; it is deciding to stand differently, holding that, and later deciding again. Seeded
    here, because a film has to render the same twice."""

    def __init__(self, seed):
        self.r = random.Random(seed)
        self.v = self.to = 0.0
        self.left = 0.0

    def step(self, dt, every):
        self.left -= dt
        if self.left <= 0:
            self.to = self.r.random() * 2 - 1
            self.left = every * (0.6 + 0.8 * self.r.random())
        self.v += (self.to - self.v) * (1 - math.exp(-1.1 * dt))
        return self.v


_DRIFTS = [Drift(4242), Drift(4243), Drift(4244)]
_DRIFT_T = [0.0]


def alive(p, t, calm=1.0):
    """arta.ts's life layer: the breath, and everything else wandering.

    The breath is modulated by a slower breath, "because a body that breathes to a metronome is a
    body being animated". Without this the figure is a diagram that changes pose — which is exactly
    what the teaser was."""
    while _DRIFT_T[0] < t - 1e-9:
        dt = min(1.0 / FPS, t - _DRIFT_T[0])
        _DRIFT_T[0] += dt
        d0 = _DRIFTS[0].step(dt, 5.5)
        d1 = _DRIFTS[1].step(dt, 4.0)
        d2 = _DRIFTS[2].step(dt, 6.5)
    if _DRIFT_T[0] <= 0:
        d0 = d1 = d2 = 0.0
    else:
        d0, d1, d2 = _DRIFTS[0].v, _DRIFTS[1].v, _DRIFTS[2].v
    depth = 1 + 0.25 * math.sin(2 * math.pi * 0.037 * t)
    q = dict(p)
    q["bre"] = p.get("bre", 1.0) * (1 + 0.026 * calm * depth * math.sin(2 * math.pi * BREATH * t))
    q["lean"] = p["lean"] + 1.6 * calm * d0
    q["tilt"] = p["tilt"] + 2.2 * calm * d1
    sway = 1.8 * calm * d2
    q["la"] = (p["la"][0] + sway, p["la"][1])
    q["ra"] = (p["ra"][0] - sway, p["ra"][1])
    return q


def blend_pose(a, b, u):
    """The film's blend, over the production pose dict."""
    o = {k: lerp(a.get(k, 1.0 if k in ("sq", "bre") else 0.0),
                 b.get(k, 1.0 if k in ("sq", "bre") else 0.0), u)
         for k in ("lean", "tilt", "sq", "bre")}
    o["face"] = a["face"] if u < 0.5 else b["face"]
    for k in ("la", "ra", "ll", "rl"):
        o[k] = (lerp(a[k][0], b[k][0], u), lerp(a[k][1], b[k][1], u))
    o["hip"] = (0.0, 0.0)
    return o


# ── the performance, on the production poses ───────────────────────────────
# Joint convention (ARTA.md §1): degrees, 0 is straight down, positive rotates
# toward +x. So a lead arm at 88 is horizontal, and at 150 it points up-forward.
def place(p, x):
    """Put a production pose on this film's ground at x — arta.ts grounded(), in frame units."""
    return grounded(p, x)


def P_walk_to(t, t0, t1, x0, x1, face):
    """The rig's own walk, its own stride, its own settle into a stand. The walk is the ONE thing
    the film and the live mascot already share verbatim, so it comes from the film's rig."""
    u = seg(t, t0, t1)
    n = max(1, round(abs(x1 - x0) / U.STRIDE))
    x = lerp(x0, x1, U.trapz(u))
    p = U.P_walk(x, (u * n) % 1.0, face)
    if u > 0.86:
        st = dict(A_stand(), face=face)
        st["hip"] = (x, U.GROUND - U.HIP_Y * 0 - foot_drop(st))
        p = U.blend(p, st, ease((u - 0.86) / 0.14))
    return dict(p, hip=(x, GROUND - (U.GROUND - p["hip"][1]) * SCALE))


def facing(t):
    """Facing is a continuous value, never a boolean: negating every joint in one frame moves a
    foot ~43 px, the largest gradient in the system and the one no blend can soften (ARTA.md §3).
    Each turn eases through zero, so the figure narrows to its own profile, passes edge-on and
    opens out the other way."""
    f = 1.0
    # A TURN IS THE FASTEST THING IN THE SYSTEM and it gets the most time: facing is applied by
    # negating every joint, so even eased through zero it moves more of the figure at once than any
    # gesture. 1.8 s is what keeps it inside the budget without the cap having to intervene.
    for t0, t1, to in ((B["turn_l"] - 1.2, B["turn_l"] + 0.6, -1.0),
                       (B["turn_r"] - 1.2, B["turn_r"] + 0.6, 1.0)):
        if t >= t0:
            f = lerp(f, to, ease(seg(t, t0, t1)))
    return f


def _target(t):
    """Where Arta WANTS to be at time t — the performance, before the motion cap.

    The performance is walk in, think, point at one rail, point at the other, and think again over
    the finished timeline. Every pose is arta.ts's own — `think()` and `point()` are the character,
    not something authored here — and the life layer runs whenever Arta is not walking, because a
    figure that holds a pose exactly is a diagram."""
    f = facing(t)
    face = 1 if f >= 0 else -1
    if t < B["arrive"]:
        p = P_walk_to(t, B["walk_in"], B["arrive"], X_IN, X_MID, 1)
        p["face_blend"] = f
        return p
    if t < B["turn_l"] + 0.5:
        base = to_think(A_stand(), seg(t, B["arrive"], B["settle"]))
    elif t < B["drop_l"]:
        base = via_fold(A_think(), A_point(96, face), seg(t, B["turn_l"] + 0.5, B["aim_l"]))
    elif t < B["turn_r"]:
        base = via_fold(A_point(96, face), A_think(), seg(t, B["drop_l"], B["turn_r"]))
    elif t < B["drop_r"]:
        base = via_fold(A_think(), A_point(96, face), seg(t, B["turn_r"] + 0.5, B["aim_r"]))
    else:
        base = via_fold(A_point(96, face), A_think(), seg(t, B["drop_r"], B["mid"]))
    base = dict(base, face=face)
    p = place(alive(base, t), X_MID)
    p["face_blend"] = f
    return p


def _disp(a, b):
    """The largest movement of any DRAWN point between two poses."""
    pa, pb = skeleton_points(a), skeleton_points(b)
    pts = lambda s: [s["hip"], s["neck"], s["head"]] + [q for arm in s["arms"] for q in arm] \
        + [q for leg in s["legs"] for q in leg]
    return max(math.dist(x, y) for x, y in zip(pts(pa), pts(pb)))


BUDGET_PX = (640.0 / FPS) * (W / 1600.0)
_POSES = {}


def _integrate():
    """THE MOTION CAP, which is how the live mascot enforces the law rather than hoping.

    ARTA.md §3: the blend factor for the whole figure is scaled back until the largest
    single-point displacement fits the budget. Scaling the WHOLE blend — rather than clamping
    points individually — is what keeps the figure a figure: it slows as one body instead of having
    a fast limb amputated from a slow torso.

    The teaser had no cap, so it was tuned by hand instead, beat by beat, and still broke the law
    every time a gesture and a turn overlapped — the production `point()` extends the same arm that
    a facing flip negates, and `think` to `point` is 228 degrees at the shoulder. With the cap the
    performance can be authored freely: a move that is too fast simply takes longer, exactly as it
    does on the site."""
    prev = None
    for n in range(int(DUR * FPS) + 1):
        t = n / FPS
        want = _target(t)
        if prev is not None:
            # Scaling the BLEND FACTOR only approximates scaling the MOVEMENT — displacement is not
            # linear in u, and the facing narrowing makes it less so — so the first scale can still
            # land over budget. ARTA.md's formula is applied until it converges rather than once.
            target = want
            for _ in range(6):
                moved = _disp(prev, want)
                if moved <= BUDGET_PX:
                    break
                u = (BUDGET_PX / moved) * 0.98
                cur = blend_pose(prev, target, u)
                cur["hip"] = (lerp(prev["hip"][0], target["hip"][0], u),
                              lerp(prev["hip"][1], target["hip"][1], u))
                cur["face"] = target["face"]
                cur["face_blend"] = lerp(prev.get("face_blend", 1.0),
                                         target.get("face_blend", 1.0), u)
                want = cur
        _POSES[n] = want
        prev = want


def figure(t):
    """Arta's pose at time t, after the cap. Integrated once, then looked up: the cap is a
    sequential thing — each drawing is a bounded step from the one before it."""
    if not _POSES:
        _integrate()
    n = int(round(t * FPS))
    return _POSES[max(0, min(int(DUR * FPS), n))]


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

    THERE IS NO TYPE ON IT BUT THE TIMELINE'S OWN. No lines of copy, and no end card: the film ends
    on the finished timeline rather than on a name. The only words are the years and the milestones
    on the two rails, which ARE the timeline — take those away and the rails are decoration."""
    big = Image.new("RGB", (W * SS, H * SS), BG)
    d = Pen(ImageDraw.Draw(big))
    fy, fl = F("m700", BRAND_YEAR_PX), F("i500", BRAND_LABEL_PX)
    draw_rail(d, "l", t, fy, fl)
    draw_rail(d, "r", t, fy, fl)
    draw_arta(d, figure(t))
    img = big.resize((W, H), Image.LANCZOS)
    # The last beat is a fade on the finished timeline: both rails complete, Arta standing between
    # them. Ending on a held drawing rather than a card is the point of dropping the card.
    if t > DUR - FADE:
        u = ease(seg(t, DUR - FADE, DUR))
        img = Image.blend(img, Image.new("RGB", (W, H), BG), u)
    return img


# ── the motion-safety ceiling, measured rather than trusted ─────────────────
def max_step():
    """The largest single-point displacement between consecutive drawings, in px.

    The law is ARTA.md §3, converted to this film's cadence exactly as the published scene's own
    lint converts it: continuous motion is capped at 640 units a second, so a new drawing every
    1/FIG_HZ s may travel 640/FIG_HZ units — 53 on twos, 27 at every frame. Units are this
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
HEAD_GATE_PX = 22.0   # under arta.ts think()'s own 24.8 — see the assert


def head_clearance():
    """How close any limb's centre-line comes to the head centre, over the whole film.

    A stick figure has no face, so the head is the one shape that must stay legible; a limb drawn
    across it reads as a broken drawing. The aim-up pose crossed it by 2.2 px and nothing measured
    that, because the selftest only ever looked at speed and at the ground."""
    worst = (1e9, 0.0)
    for n in range(int(DUR * FPS)):
        t = n / FPS
        # MEASURED ON THE POSE, NOT ON ITS PROJECTION. Facing narrows the drawn figure toward its
        # own profile, which pulls every limb toward the head's x — so measuring the drawn frames
        # made the gate fire hardest exactly where the figure is deliberately compressed, which is
        # the one thing it was built to allow. The question is whether the ARM crosses the HEAD,
        # and that is a property of the pose; the turn is a camera on it.
        p = dict(figure(t))
        p["face_blend"] = 1.0 if p.get("face_blend", 1.0) >= 0 else -1.0
        s = skeleton_points(p)
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
              f"(head radius {HEAD_R_PX:.1f}, gate {HEAD_GATE_PX:.1f})")
        # THE THRESHOLD IS WHAT THE LIVE MASCOT DOES, not what looks tidy on paper. arta.ts's own
        # think() puts the upper arm 24.8 px from the head centre at this scale — inside the 27.8 px
        # ring — so a gate set at the radius fails the character it exists to protect, which is
        # exactly what it did. 22 px is under the mascot's own worst case: close enough to catch a
        # limb drawn ACROSS the face, loose enough to let Arta raise a hand to think.
        assert worst_head[0] >= HEAD_GATE_PX, (
            f"a limb crosses the head at t={worst_head[1]:.2f}s: {worst_head[0]:.1f} px from the centre "
            f"against a {HEAD_GATE_PX:.1f} px gate (the live think pose sits at 24.8)")
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
