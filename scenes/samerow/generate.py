#!/usr/bin/env python3
"""
"The Same Row" — the ArtaQuest channel teaser. 16 s · 384 frames · 24 fps · 1920x1080.

Arta stands dead centre on a hairline in the dark and fires one arrow at the left edge and one at
the right; a life draws itself down each edge in the show's own rails and type; then the couple's
two windows fall in above, the host's window lands around Arta, and on both rails at once the one
year they share turns gold — so the last held frame of the teaser is the first frame of the show.

HOW IT IS DRAWN. Every frame is ONE SVG — figure, rails, rows, windows and camera transform — and
the SVG is rasterised by the parked lab Chrome (render.mjs, CDP 127.0.0.1:9222, the same route
as design/artapodcast/shot.mjs). That is how the published film (scenes/undefined) gets round caps,
constant width and clean joins; PIL cannot draw a round cap, and the last teaser's chisel hands and
wedge spine were exactly that. The rig is IMPORTED by path from the film of record, so skeleton,
proportions and joint convention are the character's, not a lookalike's.

THE LAWS, ENFORCED NOT REMEMBERED (`python3 generate.py --check`):
  * Motion — ARTA.md §3, taken literally: no drawn point of the figure moves more than
    min(640 px/s · dt, 12 px) between two painted frames, measured in FRAME pixels with the camera
    applied. At 24 fps that is 12 px. It is not re-derived; a governor slows the figure as one body
    when an authored move would break it, and the camera is authored under it.
  * Head — an INTRUSION gate: every limb is sampled at one rig unit, points within 13 units of the
    neck are a shoulder and ignored, and no sample may lie inside the ring's outer edge
    (HEAD_R + STROKE/2 = 24). A "centre-line ≥ radius" rule is unsatisfiable by construction
    because the arms root 24 units from the head centre; this one passes stand, point and think
    and flags the film's own cheer and lift, which are visibly drawn through the skull.
  * Labels — no figure pixel (stroke included) inside a live row's text box, ever.
  * Rows — rise per final/MOTION-SPEC.md: opacity 0→1 with translateY 24→0 over 0.3 s on
    cubic-bezier(0, 0, 0.58, 1). Nothing pops.
The arrow and the falling windows are not drawn points of the figure and cannot obey a 12 px
ceiling and still be an arrow or a slab; their criteria (travel under half the shaft per frame;
mass and a settle) are stated in the manifest rather than hidden.

Usage:  python3 generate.py            -> svg/*.svg + gates (fails loudly)
        python3 generate.py --check    -> gates only
        python3 generate.py render     -> svg + gates + PNG frames + silent.mp4 + music mux + manifest
"""

import base64, hashlib, importlib.util, json, math, os, random, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

# ── the rig, imported by PATH under a unique name ────────────────────────────
# The sibling film is also called generate.py; a plain `import generate` would return this file.
_spec = importlib.util.spec_from_file_location("arta_rig", ROOT / "scenes" / "undefined" / "generate.py")
rig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rig)
skeleton, lerp, seg, ease = rig.skeleton, rig.lerp, rig.seg, rig.ease
SPINE, NECK_H, HEAD_R = rig.SPINE, rig.NECK_H, rig.HEAD_R
THIGH, SHIN, UARM, LARM = rig.THIGH, rig.SHIN, rig.UARM, rig.LARM
assert (SPINE, NECK_H, HEAD_R, THIGH, SHIN, UARM, LARM) == (70, 24, 20, 52, 52, 34, 32)

# ── frame, clock, palette ───────────────────────────────────────────────────
W, H, FPS, DUR = 1920, 1080, 24, 16.0
N = int(round(DUR * FPS))                     # 384
DT = 1.0 / FPS
GOLD, BLUE = "#E8B923", "#1746DC"             # the pair; never a third
BG, SPACE3 = "#010C17", "#0C1E32"
INK, INK2, INK3 = "#F4F4F5", "#A6A8B0", "#8B8E98"

# ── the figure ──────────────────────────────────────────────────────────────
SCALE = 1.73                                  # rig units -> world px: 218 * 1.73 = 377 px, 35 % of 1080
STROKE = 8.0                                  # rig units, like the film's .fig
RING = HEAD_R + STROKE / 2                    # the head ring's OUTER edge, 24 units
SHOULDER_EXCL = 13.0                          # within this of the neck a limb sample is a shoulder
SHOULDER_MAX = 116                            # arta.ts point(): past this the arm folds at the elbow
ARTA_X, GROUND = 960.0, 985.0                 # the host window's bottom edge; Arta never leaves it
MAX_PX_PER_FRAME = min(640.0 * DT, 12.0)      # ARTA.md §3 at 24 fps: 12 px, no re-derivation
ARROW_SPEED, ARROW_SHAFT = 1200.0, 100.0      # world px/s, world px: 50 px/frame, half the shaft

# ── the show's frame (final/Main.dc.html, Spec.dc.html §3 and §10) ──────────
WIN_MAN, WIN_WOMAN, WIN_HOST = (32, 18, 912, 513), (976, 18, 912, 513), (640, 625, 640, 360)
WIN_R = 16
TL_TOP, PITCH = 613, 64                       # row tops 613 … 933; tick centres 645 … 965
TL_L_X, TL_R_X, TL_W = 32, 1312, 576
RAIL_INSET, RAIL_W, TICK_W, CURSOR_W, TICK_H = 9, 6, 24, 34, 6
YEAR_X_INSET, LABEL_GAP = 40, 16
ROWS_L = [("1951", "Born 9 May · Tabriz"), ("1979", "Married"), ("1985", "Master baker"),
          ("1994", "Opened the bakery"), ("2008", "Second shop"), ("2019", "Retired")]
ROWS_R = [("1955", "Born 2 June · Porto"), ("1979", "Married"), ("1984", "Nursing degree"),
          ("1996", "Head nurse"), ("2007", "Founded the clinic"), ("2021", "Published a memoir")]
SHARED_ROW = 1                                # 1979, on both rails
LT_MAN = (["Mohammadreza", "Hosseinzadeh-Tabrizi"], "Master baker")   # the kit's own sample copy
LT_WOMAN = (["Ana Costa"], "Head nurse")
LOWER_THIRDS = "--no-lower-thirds" not in sys.argv

def tick_cy(i):  return TL_TOP + PITCH * i + 32
RAIL_TOP, RAIL_BOT = tick_cy(0), tick_cy(5)   # 645, 965

# ── the beat clock (seconds) ────────────────────────────────────────────────
B = dict(
    fire_l=0.60,                              # the arrow leaves the hand
    arm_down_l=1.60, arm_down_l_end=3.20,
    turn=3.20, turn_end=4.45,                 # face -1 -> +1 between two held stands
    pan=4.10, pan_end=7.70,                   # camera A -> B
    aim_r=4.50, aim_r_end=6.05,
    fire_r=6.10,
    arm_down_r=7.10, arm_down_r_end=8.75,
    pull=8.90, pull_end=11.10,                # camera B -> C
    win_man=9.70, win_woman=9.95,             # the couple's windows fall
    vig_off=9.40, vig_off_end=10.60,
    flinch=10.85,                             # 0.35 s after the second landing settles: noticing
    gold=11.50,                               # THE SAME ROW
    nod=11.90,
    win_host=12.90,
    think=13.50, think_end=14.90,
    fade=15.20, end=16.00,
)
RAIL_DRAW = 2.20                              # s for 320 px: 145 px/s, a speed you can follow
ROW_PITCH_S = RAIL_DRAW / 5                   # 0.44 s: rows overlap their 0.3 s rises

# ── easing ──────────────────────────────────────────────────────────────────
def smooth(u):    return u * u * (3 - 2 * u)
def ease_in(u):   return u ** 3
def ease_out(u):  return 1 - (1 - u) ** 3

def trapz(u, r=0.2):
    if u < r:      return 0.5 * u * u / (r * (1 - r))
    if u > 1 - r:  return 1.0 - 0.5 * (1 - u) ** 2 / (r * (1 - r))
    return (u - r / 2) / (1 - r)

def css_ease_out(u):
    """cubic-bezier(0, 0, 0.58, 1) — the kit's one easing. Solve x(t) = u, return y(t)."""
    u = max(0.0, min(1.0, u))
    lo, hi = 0.0, 1.0
    for _ in range(24):
        t = (lo + hi) / 2
        x = 3 * (1 - t) * t * t * 0.58 + t ** 3
        if x < u: lo = t
        else:     hi = t
    t = (lo + hi) / 2
    return 3 * t * t - 2 * t ** 3

def rise(t, t0, d=0.3):
    """MOTION-SPEC: opacity 0->1, translateY 24->0 over 0.3 s, ease-out. Returns (opacity, dy)."""
    k = css_ease_out(seg(t, t0, t0 + d))
    return k, 24.0 * (1 - k)

def num(x):
    s = f"{float(x):.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s

def mix(c1, c2, u):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(lerp(a[i], b[i], u)) for i in range(3))

# ── poses (rig units; the rig's own convention: 0 straight down, + toward +x) ─
def P(**kw):
    d = dict(hip=(0.0, 0.0), lean=0.0, tilt=0.0, face=1.0,
             la=(9, 12), ra=(-9, -12), ll=(3, -5), rl=(-3, -5), sq=1.0, bre=1.0)   # the film's stance
    d.update(kw)
    return d

def A_stand():
    """A held stand. The film's closed stance (arms ±9, legs ±3) merges into the torso at this
    stroke and reads as a lollipop — reviewer 3's word — so the arms sit a little wider and one
    forward of the other, the legs a little apart, with a small lean and tilt so the body has a
    direction. Still far from the mascot's ±14/±7 page stance, which stands bandy at film scale."""
    return P(lean=3, tilt=5, la=(15, 14), ra=(-13, -11), ll=(6, -6), rl=(-5, -6))

def mirror(p):
    """The same DRAWING expressed with face=+1: negate what skeleton() would have negated."""
    q = dict(p); q["face"] = 1.0
    f = p["face"]
    q["lean"], q["tilt"] = p["lean"] * f, p["tilt"] * f
    for k in ("la", "ra", "ll", "rl"):
        q[k] = (p[k][0] * f, p[k][1] * f)
    return q

def A_point(deg, face):
    """arta.ts point(): the FOREARM lies on the absolute aim `deg`. The angles carry `face` and so
    does the pose — skeleton() multiplies by face again, so face² cancels and the arm aims where it
    was told to. Returning the pose without face=face is the bug that made the last teaser turn
    left and point right."""
    shoulder = max(-SHOULDER_MAX, min(SHOULDER_MAX, deg))
    return P(lean=4, tilt=-6, face=face, la=(18, 14),
             ra=(shoulder * face, (deg - shoulder) * face), ll=(10, -8), rl=(-12, -8))

def A_fold():
    """The half-way house on the road to the think: arm OUT to the side, forearm straight, so the
    limb travels round the head rather than across it."""
    return P(lean=-3, tilt=4, la=(18, 15), ra=(-70, -10), ll=(8, -4), rl=(-8, -8))

def A_think():
    """Solved, not drawn: the hand under the head where a chin would be, 28 units from its centre,
    the elbow hanging BELOW the shoulder (a think, not a salute), and the whole arm outside the
    ring by the gate's own measure. The live rig's (-132, -52) puts the upper arm 6 units into the
    ring and is not used. The legs stay near the stand's — the live rig's (14,-10)/(-20,-30) is a
    lunge that would slide both feet 25 units across the ground on the way in; the banner's think
    stands on a narrow base, and so does this."""
    return P(lean=-6, tilt=8, la=(22, 16), ra=(-41, -140), ll=(8, -4), rl=(-8, -8))

def A_crouch(k):
    return P(lean=14 * k, tilt=6 * k, la=(9 - 43 * k, 12 - 4 * k), ra=(-9 - 31 * k, -12 + 18 * k),
             ll=(3 + 23 * k, -5 - 57 * k), rl=(-3 - 19 * k, -5 - 53 * k), bre=1.0 - 0.04 * k)

def foot_drop(p):
    """How far the lower sole hangs below the hip. Grounding EVERY pose by this is what keeps the
    feet on the line through a blend, a crouch and a breath alike."""
    f = p["face"]
    pts = [rig._limb((0.0, 0.0), a[0] * f, a[1] * f, THIGH * p["sq"], SHIN * p["sq"])[1]
           for a in (p["ll"], p["rl"])]
    return max(y for _, y in pts)

def grounded(p, x=ARTA_X):
    q = dict(p)
    q["hip"] = (x, GROUND - foot_drop(p) * SCALE)
    return q

def blend_pose(a, b, u):
    """Every channel lerps, INCLUDING face — a turn is continuous, never a flip (ARTA.md §3)."""
    o = {}
    for k in ("lean", "tilt", "face", "sq", "bre"):
        o[k] = lerp(a[k], b[k], u)
    for k in ("la", "ra", "ll", "rl"):
        o[k] = (lerp(a[k][0], b[k][0], u), lerp(a[k][1], b[k][1], u))
    o["hip"] = (lerp(a["hip"][0], b["hip"][0], u), lerp(a["hip"][1], b["hip"][1], u))
    return o

def cycles(t, t0, span, n):
    """n out-and-back cycles then still, ending ON zero (the film's own rule)."""
    u = seg(t, t0, t0 + span)
    return 0.0 if u >= 1.0 else math.sin(math.pi * ((u * n) % 1.0))

# ── the aim: computed from the neck at fire time, not hand-tuned ────────────
def neck_world(p):
    s = skeleton(p)
    return p["hip"][0] + s["neck"][0] * SCALE, p["hip"][1] + s["neck"][1] * SCALE

def aim_deg(neck, target):
    dx, dy = target[0] - neck[0], target[1] - neck[1]
    return math.degrees(math.atan2(dx, dy))

TARGET_L = (TL_L_X + RAIL_INSET + RAIL_W / 2, RAIL_TOP)            # (44, 645) his birth tick
TARGET_R = (TL_R_X + TL_W - RAIL_INSET - RAIL_W / 2, RAIL_TOP)     # (1876, 645) hers

_neck0 = neck_world(grounded(A_point(-95, -1)))
AIM_L = aim_deg(_neck0, TARGET_L)
AIM_R = aim_deg(_neck0, TARGET_R)

# ── the authored performance ────────────────────────────────────────────────
# Every authored pose is normalised to face=+1 (`mirror` keeps the drawing), so the governor's
# blend never lerps `face` and the turn is authored explicitly below.
STAND_L = mirror(grounded(dict(A_stand(), face=-1.0)))
STAND_R = grounded(A_stand())
POINT_L = mirror(grounded(A_point(AIM_L, -1)))
POINT_R = grounded(A_point(AIM_R, 1))
def _same_drawing(p, q):
    a, b = skeleton(p), skeleton(q)
    pts = lambda s: [s["neck"], s["head"]] + [j for lm in s["arms"] + s["legs"] for j in lm]
    return max(math.hypot(x - u, y - v) for (x, y), (u, v) in zip(pts(a), pts(b))) < 1e-9
for _p in (grounded(dict(A_stand(), face=-1.0)), grounded(A_point(AIM_L, -1))):
    assert _same_drawing(_p, mirror(_p)), "mirror() changed the drawing"

def turn(u):
    """The turn, continuous (ARTA.md §3): every angle eases from the left-facing drawing to the
    right-facing one. Taken literally that passes through a figure with every limb straight down,
    which at 4 frames is the rig's own edge-on moment — but a body turning also swings its arms,
    so a swing is added that peaks mid-turn and is zero at both ends, and the knees give a little
    for weight. The feet move under 3 units, so nothing skates."""
    k = smooth(u)
    p = blend_pose(STAND_L, STAND_R, k)
    sw = math.sin(math.pi * k)
    p["la"] = (p["la"][0] + 14 * sw, p["la"][1] + 6 * sw)
    p["ra"] = (p["ra"][0] - 14 * sw, p["ra"][1] - 6 * sw)
    p["ll"] = (p["ll"][0] + 3 * sw, p["ll"][1] - 6 * sw)
    p["rl"] = (p["rl"][0] - 3 * sw, p["rl"][1] - 6 * sw)
    p["sq"] = 1.0 - 0.03 * sw
    return grounded(p)
FOLD = grounded(A_fold()); THINK = grounded(A_think())

def authored(t):
    """The pose Arta WANTS at t. The governor below is what it gets."""
    if t < B["arm_down_l"]:
        return POINT_L
    if t < B["turn"]:
        return blend_pose(POINT_L, STAND_L, smooth(seg(t, B["arm_down_l"], B["arm_down_l_end"])))
    if t < B["aim_r"]:
        return turn(seg(t, B["turn"], B["turn_end"]))
    if t < B["arm_down_r"]:
        return blend_pose(STAND_R, POINT_R, smooth(seg(t, B["aim_r"], B["aim_r_end"])))
    if t < B["flinch"]:
        return blend_pose(POINT_R, STAND_R, smooth(seg(t, B["arm_down_r"], B["arm_down_r_end"])))
    if t < B["nod"]:
        # the flinch: a quarter-strength crouch, down in 0.20 s, back in 0.35 s
        k = 0.25 * (smooth(seg(t, B["flinch"], B["flinch"] + 0.20))
                    - smooth(seg(t, B["flinch"] + 0.20, B["flinch"] + 0.55)))
        return grounded(blend_pose(A_stand(), A_crouch(1.0), k))
    if t < B["think"]:
        k = cycles(t, B["nod"], 1.3, 2)
        p = A_stand(); p["tilt"] += 16 * k; p["lean"] += 3 * k
        return grounded(p)
    u = seg(t, B["think"], B["think_end"])
    if u < 0.5:
        return grounded(blend_pose(A_stand(), A_fold(), smooth(u * 2)))
    return grounded(blend_pose(A_fold(), A_think(), smooth((u - 0.5) * 2)))

# ── the life layer: breath and seeded drift (arta.ts), scaled by calm ───────
class Drift:
    """A slow wander in [-1, 1]: pick a target, ease toward it, pick another. A sum of sines is
    periodic or near enough that a viewer sees the seam; shifting your weight is a decision."""
    def __init__(self, seed):
        self.r = random.Random(seed); self.v = self.to = 0.0; self.left = 0.0
    def step(self, dt, every):
        self.left -= dt
        if self.left <= 0:
            self.to = self.r.random() * 2 - 1
            self.left = every * (0.6 + 0.8 * self.r.random())
        self.v += (self.to - self.v) * (1 - math.exp(-1.1 * dt))
        return self.v

BREATH = 0.42

def alive(p, t, drifts, calm):
    d0, d1, d2 = drifts
    depth = 1 + 0.25 * math.sin(2 * math.pi * 0.037 * t)
    q = dict(p)
    q["bre"] = p["bre"] * (1 + 0.026 * calm * depth * math.sin(2 * math.pi * BREATH * t))
    q["lean"] = p["lean"] + 1.6 * calm * d0
    q["tilt"] = p["tilt"] + 2.2 * calm * d1
    sway = 1.8 * calm * d2
    q["la"] = (p["la"][0] + sway, p["la"][1])
    q["ra"] = (p["ra"][0] - sway, p["ra"][1])
    return q

# ── the camera: ONE camera, monotonic in scale, three framings ──────────────
CAM_A = (1.40, 660.0, 690.0)      # his side + Arta:  world x -26..1346
CAM_B = (1.32, 1169.0, 705.0)     # her side + Arta:  world x 442..1896
CAM_C = (1.00, 960.0, 540.0)      # the frame

def camera(t):
    s, cx, cy = CAM_A
    s = lerp(s, 1.38, seg(t, 0.0, B["pan"]))                       # a creep, so A is never a still
    cx = lerp(cx, 680.0, seg(t, 0.0, B["pan"]))
    u = trapz(seg(t, B["pan"], B["pan_end"]), 0.2)
    s, cx, cy = lerp(s, CAM_B[0], u), lerp(cx, CAM_B[1], u), lerp(cy, CAM_B[2], u)
    u = smooth(seg(t, B["pull"], B["pull_end"]))
    return lerp(s, CAM_C[0], u), lerp(cx, CAM_C[1], u), lerp(cy, CAM_C[2], u)

def to_frame(cam, x, y):
    s, cx, cy = cam
    return (x - cx) * s + W / 2, (y - cy) * s + H / 2

# ── drawn points ────────────────────────────────────────────────────────────
def world_pts(p):
    """Every joint and end of every stroke, plus the head centre, in world px. Limbs are straight
    segments, so the furthest-moving point of a segment is one of its ends."""
    s, (hx, hy) = skeleton(p), p["hip"]
    pts = [(0.0, 0.0), s["neck"], s["head"]] + [j for lm in s["arms"] + s["legs"] for j in lm]
    return [(hx + x * SCALE, hy + y * SCALE) for x, y in pts]

def frame_pts(p, cam):
    return [to_frame(cam, x, y) for x, y in world_pts(p)]

def spread(a, b):
    return max(math.hypot(x - u, y - v) for (x, y), (u, v) in zip(a, b))

# ── the governor: the law, applied ──────────────────────────────────────────
def perform():
    """Render-order pass over every frame. Each frame the figure wants `authored(t)` plus its
    life layer; if that would move any drawn point more than the budget in FRAME px (camera
    included), the whole blend from the previous drawing is scaled back until it fits — the
    figure slows as one body rather than losing a limb (ARTA.md §3). Returns the poses actually
    drawn, and the per-frame peak."""
    drifts = [Drift(4242), Drift(4243), Drift(4244)]
    poses, peaks, governed = [], [], 0
    prev = None; prev_fp = None
    for i in range(N):
        t = i * DT
        cam = camera(t)
        d = (drifts[0].step(DT, 5.5), drifts[1].step(DT, 4.0), drifts[2].step(DT, 6.5))
        want_dry = authored(t)
        # calm falls to zero the moment the authored figure is actually moving
        nxt = authored(min(DUR, t + DT))
        moving = spread(world_pts(want_dry), world_pts(nxt))
        calm = max(0.0, 1.0 - moving / 3.0)
        want = alive(want_dry, t, d, calm)
        if prev is None:
            pose = want
        else:
            fp = frame_pts(want, cam)
            if spread(prev_fp, fp) <= MAX_PX_PER_FRAME:
                pose = want
            else:
                governed += 1
                lo, hi = 0.0, 1.0
                for _ in range(18):
                    u = (lo + hi) / 2
                    if spread(prev_fp, frame_pts(blend_pose(prev, want, u), cam)) <= MAX_PX_PER_FRAME:
                        lo = u
                    else:
                        hi = u
                pose = blend_pose(prev, want, lo)
        fp = frame_pts(pose, cam)
        peaks.append(spread(prev_fp, fp) if prev_fp else 0.0)
        poses.append(pose); prev, prev_fp = pose, fp
    return poses, peaks, governed

# ── the arrow (blue: a tool, ARTA.md §8) ────────────────────────────────────
def hand_world(p):
    s = skeleton(p)
    return p["hip"][0] + s["arms"][1][1][0] * SCALE, p["hip"][1] + s["arms"][1][1][1] * SCALE

def arrow_at(t, poses):
    """One short shaft in flight from the hand toward the mark it was aimed at, then out past the
    frame's edge. Returns (tip, tail, opacity) in world px, or None."""
    for fire, target in ((B["fire_l"], TARGET_L), (B["fire_r"], TARGET_R)):
        age = t - fire
        if age < 0 or age > 1.6:
            continue
        p = poses[int(round(fire * FPS))]
        hx, hy = hand_world(p)
        dx, dy = target[0] - hx, target[1] - hy
        L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
        d = 18.0 + ARROW_SPEED * age                                     # tip distance from the hand
        tip = (hx + ux * d, hy + uy * d)
        tail = (tip[0] - ux * ARROW_SHAFT, tip[1] - uy * ARROW_SHAFT)
        op = 0.85 * min(1.0, age / 0.12)
        return tip, tail, (ux, uy), op
    return None

def arrival(fire, poses, target):
    p = poses[int(round(fire * FPS))]
    hx, hy = hand_world(p)
    return fire + (math.hypot(target[0] - hx, target[1] - hy) - 18.0) / ARROW_SPEED

# ── the rails ───────────────────────────────────────────────────────────────
def rail_state(t, t_land, side):
    """One list's drawing at t. t_land is when the arrow reached the birth tick."""
    tip = RAIL_TOP + (RAIL_BOT - RAIL_TOP) * seg(t, t_land, t_land + RAIL_DRAW)
    gold_len = (tick_cy(SHARED_ROW) - RAIL_TOP) * css_ease_out(seg(t, B["gold"], B["gold"] + 0.6))
    kgold = css_ease_out(seg(t, B["gold"], B["gold"] + 0.3))
    rows = []
    for i in range(6):
        t_i = t_land + ROW_PITCH_S * i
        top, dy = rise(t, t_i + (0.08 if i == 0 else 0.0))
        tick_op = css_ease_out(seg(t, t_i, t_i + 0.3))
        col = INK3
        if i == 0:               col = mix(INK3, INK2, kgold)
        elif i == SHARED_ROW:    col = mix(INK3, INK, kgold)
        tick_col = mix(INK3, GOLD, kgold) if i in (0, SHARED_ROW) else INK3
        tick_w = TICK_W + (CURSOR_W - TICK_W) * kgold if i == SHARED_ROW else TICK_W
        rows.append(dict(op=top, dy=dy, tick_op=tick_op, col=col, tick_col=tick_col, tick_w=tick_w))
    return dict(tip=tip, gold=gold_len, rows=rows, visible=t >= t_land)

# ── the windows ─────────────────────────────────────────────────────────────
def fall_y(t, t0, y_final):
    """A slab with mass: ease-in over 0.55 s to 8 px past its seat, then a 0.18 s ease-out settle."""
    u = seg(t, t0, t0 + 0.55)
    if u <= 0:
        return None
    y = lerp(-560.0, y_final + 8.0, ease_in(u))
    if u >= 1.0:
        y = lerp(y_final + 8.0, y_final, ease_out(seg(t, t0 + 0.55, t0 + 0.73)))
    return y

# ── type metrics (measured in the browser, see render.mjs measure) ──────────
FONTS = dict(m700=HERE.parent / "teaser" / "fonts" / "Montserrat-700.ttf",
             i500=HERE.parent / "teaser" / "fonts" / "Inter-500.ttf",
             i600=HERE.parent / "teaser" / "fonts" / "Inter-600.ttf")
YEAR_FONT = ("Montserrat", 700, 32, "-0.01em")
LABEL_FONT = ("Inter", 500, 28, "0")
NAME_FONT_2 = ("Montserrat", 700, 48, "-0.01em")
NAME_FONT_1 = ("Montserrat", 700, 60, "-0.01em")
SUB_FONT = ("Inter", 600, 44, "0.005em")

def _baseline(font, line_h):
    """Where the baseline of a CSS line box of height line_h sits below the box's top, for this
    font — from its ascent and descent (PIL reads the same hhea table the browser lays out on)."""
    from PIL import ImageFont
    fam, wt, px, _ = font
    key = {("Montserrat", 700): "m700", ("Inter", 500): "i500", ("Inter", 600): "i600"}[(fam, wt)]
    f = ImageFont.truetype(str(FONTS[key]), px)
    asc, desc = f.getmetrics()
    return (line_h - (asc + desc)) / 2 + asc

def text_specs():
    """Every string the film sets, so the measure pass can return each one's box."""
    out = {}
    for side, rows in (("L", ROWS_L), ("R", ROWS_R)):
        for i, (yr, lab) in enumerate(rows):
            out[f"yr{side}{i}"] = (yr, YEAR_FONT)
            out[f"lab{side}{i}"] = (lab, LABEL_FONT)
    for j, line in enumerate(LT_MAN[0]):
        out[f"nameM{j}"] = (line, NAME_FONT_2)
    out["subM"] = (LT_MAN[1], SUB_FONT)
    for j, line in enumerate(LT_WOMAN[0]):
        out[f"nameW{j}"] = (line, NAME_FONT_1)
    out["subW"] = (LT_WOMAN[1], SUB_FONT)
    return out

def text_el(txt, font, x, y, fill, anchor="start", extra=""):
    fam, wt, px, ls = font
    txt = txt.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{num(x)}" y="{num(y)}" font-family="{fam}" font-weight="{wt}" '
            f'font-size="{px}" letter-spacing="{ls}" text-anchor="{anchor}" fill="{fill}"{extra}>{txt}</text>')

def measure_svg():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">']
    for k, (txt, font) in text_specs().items():
        parts.append(text_el(txt, font, 100, 300, INK, extra=f' id="{k}"'))
    parts.append("</svg>")
    return "".join(parts)

def load_metrics():
    p = HERE / "metrics.json"
    if not p.exists():
        (HERE / "measure.svg").write_text(measure_svg())
        subprocess.run(["node", str(HERE / "render.mjs"), "measure"], check=True, timeout=120)
    m = json.loads(p.read_text())
    for k in text_specs():
        assert k in m, f"metrics.json lacks {k}; delete it and re-run"
    return m

# ── layout of the rows and the lower-thirds, in world px ────────────────────
def row_layout(M):
    """Returns per side per row: year (x, baseline, anchor), label (x, baseline, anchor), and the
    live text box (x0, y0, x1, y1) in world px, for the label gate."""
    yb = _baseline(YEAR_FONT, 36); lb = _baseline(LABEL_FONT, 36)
    out = {"L": [], "R": []}
    for i in range(6):
        cy = tick_cy(i); top = cy - 32 + 14                     # the 36 px line box, centred in 64
        yw, lw = M[f"yrL{i}"]["w"], M[f"labL{i}"]["w"]
        yx = TL_L_X + YEAR_X_INSET; lx = yx + yw + LABEL_GAP
        box = (yx + M[f"yrL{i}"]["x"], top + yb + M[f"yrL{i}"]["y"],
               lx + M[f"labL{i}"]["x"] + lw, top + lb + M[f"labL{i}"]["y"] + M[f"labL{i}"]["h"])
        out["L"].append(dict(yr=(yx, top + yb, "start"), lab=(lx, top + lb, "start"), box=box))
        yw, lw = M[f"yrR{i}"]["w"], M[f"labR{i}"]["w"]
        yx = TL_R_X + TL_W - YEAR_X_INSET; lx = yx - yw - LABEL_GAP
        box = (lx - lw, top + yb + M[f"yrR{i}"]["y"], yx, top + lb + M[f"labR{i}"]["y"] + M[f"labR{i}"]["h"])
        out["R"].append(dict(yr=(yx, top + yb, "end"), lab=(lx, top + lb, "end"), box=box))
    return out

def lower_third(M, win, key, lines, sub, name_font):
    """The kit's lower-third: a 10 px blue bar, then plates hugging their text, flush to the
    window's bottom-left. Name plate padding 10/24/10/20, sub plate 6/24/6/20, 6 px gap."""
    wx, wy, ww, wh = win
    lh = 52 if len(lines) > 1 else 64
    name_h = 10 + lh * len(lines) + 10
    name_w = max(M[f"name{key}{j}"]["w"] for j in range(len(lines))) + 44
    sub_h, sub_w = 6 + 48 + 6, M[f"sub{key}"]["w"] + 44
    total = name_h + 6 + sub_h
    bottom = wy + wh
    top = bottom - total
    parts = [f'<rect x="{wx}" y="{num(top)}" width="10" height="{total}" fill="{BLUE}"/>',
             f'<rect x="{wx + 10}" y="{num(top)}" width="{num(name_w)}" height="{name_h}" fill="#000000" fill-opacity="0.8"/>']
    nb = _baseline(name_font, lh)
    for j, line in enumerate(lines):
        parts.append(text_el(line, name_font, wx + 10 + 20, top + 10 + lh * j + nb, INK))
    st = bottom - sub_h
    parts.append(f'<rect x="{wx + 10}" y="{num(st)}" width="{num(sub_w)}" height="{sub_h}" fill="#000000" fill-opacity="0.8"/>')
    parts.append(text_el(sub, SUB_FONT, wx + 10 + 20, st + 6 + _baseline(SUB_FONT, 48), INK))
    return "".join(parts)

# ── one frame as SVG ────────────────────────────────────────────────────────
def figure_svg(p):
    s = skeleton(p)
    hx, hy = p["hip"]
    def pl(*pts):
        return '<path d="M' + "L".join(f"{num(x)} {num(y)}" for x, y in pts) + '"/>'
    body = [pl((0, 0), s["neck"])]
    for i in (0, 1):
        body.append(pl(s["neck"], s["arms"][i][0], s["arms"][i][1]))
        body.append(pl((0, 0), s["legs"][i][0], s["legs"][i][1]))
    body.append(f'<circle cx="{num(s["head"][0])}" cy="{num(s["head"][1])}" r="{num(HEAD_R)}"/>')
    return (f'<g transform="translate({num(hx)} {num(hy)}) scale({SCALE})" fill="none" stroke="{GOLD}" '
            f'stroke-width="{STROKE}" stroke-linecap="round" stroke-linejoin="round">' + "".join(body) + "</g>")

def frame_svg(frame, poses, M, layout, t_land_l, t_land_r):
    t = frame * DT
    cam = camera(t)
    s, cx, cy = cam
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           '<defs>',
           f'<radialGradient id="amb" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{SPACE3}" stop-opacity="0.85"/>'
           f'<stop offset="0.55" stop-color="{SPACE3}" stop-opacity="0.35"/><stop offset="1" stop-color="{SPACE3}" stop-opacity="0"/></radialGradient>',
           '<radialGradient id="vig" cx="0.5" cy="0.5" r="0.5"><stop offset="0.50" stop-color="#000" stop-opacity="0"/>'
           '<stop offset="0.82" stop-color="#000" stop-opacity="0.16"/><stop offset="1" stop-color="#000" stop-opacity="0.42"/></radialGradient>']
    for k, (wx, wy, ww, wh) in (("cm", WIN_MAN), ("cw", WIN_WOMAN), ("ch", WIN_HOST)):
        out.append(f'<clipPath id="{k}"><rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="{WIN_R}"/></clipPath>')
    out.append('</defs>')
    out.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    out.append(f'<g transform="translate({W / 2} {H / 2}) scale({num(s)}) translate({num(-cx)} {num(-cy)})">')

    # the ambient and the hairline belong to the shot; both are gone when the shot becomes the frame
    stage = 1.0 - smooth(seg(t, B["vig_off"], B["vig_off_end"]))
    if stage > 0:
        out.append(f'<ellipse cx="{ARTA_X}" cy="820" rx="760" ry="520" fill="url(#amb)" opacity="{num(stage)}"/>')
    hair = (0.20 + 0.05 * math.sin(2 * math.pi * 0.08 * t)) * (1.0 - smooth(seg(t, B["win_host"] + 0.55, B["win_host"] + 0.85)))
    if hair > 0:
        out.append(f'<line x1="-700" y1="{GROUND}" x2="2620" y2="{GROUND}" stroke="{INK3}" stroke-width="1.5" opacity="{num(hair)}"/>')

    # the windows, behind everything
    for key, win, t0, lt in (("cm", WIN_MAN, B["win_man"], ("M",) + LT_MAN),
                             ("cw", WIN_WOMAN, B["win_woman"], ("W",) + LT_WOMAN),
                             ("ch", WIN_HOST, B["win_host"], None)):
        y = fall_y(t, t0, win[1])
        if y is None:
            continue
        wx, wy, ww, wh = win
        out.append(f'<rect x="{wx}" y="{num(y)}" width="{ww}" height="{wh}" rx="{WIN_R}" fill="{SPACE3}"/>')
        if lt and LOWER_THIRDS:
            op, dy = rise(t, t0 + 0.73 + 0.17)
            if op > 0:
                nf = NAME_FONT_2 if len(lt[1]) > 1 else NAME_FONT_1
                out.append(f'<g clip-path="url(#{key})"><g opacity="{num(op)}" transform="translate(0 {num(dy)})">'
                           + lower_third(M, win, lt[0], lt[1], lt[2], nf) + '</g></g>')

    # the rails
    for side, rows, x0, t_land in (("L", ROWS_L, TL_L_X, t_land_l), ("R", ROWS_R, TL_R_X, t_land_r)):
        st = rail_state(t, t_land, side)
        if not st["visible"]:
            continue
        rx = x0 + RAIL_INSET if side == "L" else x0 + TL_W - RAIL_INSET - RAIL_W
        out.append(f'<rect x="{rx}" y="{RAIL_TOP}" width="{RAIL_W}" height="{num(st["tip"] - RAIL_TOP)}" fill="{INK3}"/>')
        if st["gold"] > 0:
            out.append(f'<rect x="{rx}" y="{RAIL_TOP}" width="{RAIL_W}" height="{num(st["gold"])}" fill="{GOLD}"/>')
        for k, r in enumerate(st["rows"]):
            if r["tick_op"] <= 0:
                continue
            tx = x0 if side == "L" else x0 + TL_W - r["tick_w"]
            out.append(f'<rect x="{num(tx)}" y="{tick_cy(k) - TICK_H / 2}" width="{num(r["tick_w"])}" height="{TICK_H}" '
                       f'fill="{r["tick_col"]}" opacity="{num(r["tick_op"])}"/>')
            if r["op"] > 0:
                L = layout[side][k]
                out.append(f'<g opacity="{num(r["op"])}" transform="translate(0 {num(r["dy"])})">'
                           + text_el(rows[k][0], YEAR_FONT, L["yr"][0], L["yr"][1], r["col"], L["yr"][2])
                           + text_el(rows[k][1], LABEL_FONT, L["lab"][0], L["lab"][1], r["col"], L["lab"][2]) + "</g>")

    out.append(figure_svg(poses[frame]))

    a = arrow_at(t, poses)
    if a:
        (tx, ty), (bx, by), (ux, uy), op = a
        px, py = -uy, ux
        bw = 13 * SCALE / 1.6; bo = 8 * SCALE / 1.6
        d = (f"M{num(bx)} {num(by)}L{num(tx)} {num(ty)}"
             f"M{num(tx - ux * bw + px * bo)} {num(ty - uy * bw + py * bo)}L{num(tx)} {num(ty)}"
             f"L{num(tx - ux * bw - px * bo)} {num(ty - uy * bw - py * bo)}")
        out.append(f'<path d="{d}" fill="none" stroke="{BLUE}" stroke-width="{num(3.2 * SCALE)}" '
                   f'stroke-linecap="round" stroke-linejoin="round" opacity="{num(op)}"/>')
    out.append('</g>')

    if stage > 0:
        out.append(f'<rect width="{W}" height="{H}" fill="url(#vig)" opacity="{num(stage)}"/>')
    fade = smooth(seg(t, B["fade"], B["end"]))
    if fade > 0:
        out.append(f'<rect width="{W}" height="{H}" fill="#000" opacity="{num(fade)}"/>')
    out.append('</svg>')
    return "".join(out)

# ── the gates ───────────────────────────────────────────────────────────────
def head_intrusion(p):
    """Worst intrusion of any limb sample into the head ring's outer edge, in rig units, ignoring
    samples within SHOULDER_EXCL of the neck. 0.0 is clean."""
    s = skeleton(p)
    nx, ny = s["neck"]; hx, hy = s["head"]
    worst = 0.0
    for chain in ([s["neck"], s["arms"][0][0], s["arms"][0][1]], [s["neck"], s["arms"][1][0], s["arms"][1][1]],
                  [(0.0, 0.0), s["legs"][0][0], s["legs"][0][1]], [(0.0, 0.0), s["legs"][1][0], s["legs"][1][1]]):
        for (ax, ay), (bx, by) in zip(chain, chain[1:]):
            L = math.hypot(bx - ax, by - ay); n = max(1, int(math.ceil(L)))
            for k in range(n + 1):
                u = k / n; x, y = ax + (bx - ax) * u, ay + (by - ay) * u
                if math.hypot(x - nx, y - ny) < SHOULDER_EXCL:
                    continue
                worst = max(worst, RING - math.hypot(x - hx, y - hy))
    return worst

def seg_box_hit(a, b, r, box):
    """Does the segment a-b, thickened by r, touch the axis-aligned box?"""
    x0, y0, x1, y1 = box[0] - r, box[1] - r, box[2] + r, box[3] + r
    # sample the segment finely; boxes are large relative to a rig unit
    L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(L / 2))
    for k in range(n + 1):
        u = k / n; x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False

def check(poses, peaks, governed, layout, t_land_l, t_land_r, verbose=True):
    fails = []
    # 1. motion: every drawn point of the figure, frame px, camera included
    worst = max(range(N), key=lambda i: peaks[i])
    if peaks[worst] > MAX_PX_PER_FRAME + 1e-6:
        fails.append(f"motion: {peaks[worst]:.2f} px at f{worst:03d} (t={worst * DT:.2f}s) > {MAX_PX_PER_FRAME:.0f}")
    # camera-only speed, for the record: the figure can never move against the camera
    cam_peak = 0.0
    for i in range(1, N):
        cam_peak = max(cam_peak, spread(frame_pts(poses[i - 1], camera((i - 1) * DT)), frame_pts(poses[i - 1], camera(i * DT))))
    # 2. head: intrusion gate on every rendered pose
    hi = max(range(N), key=lambda i: head_intrusion(poses[i]))
    hw = head_intrusion(poses[hi])
    if hw > 0.0:
        fails.append(f"head: limb intrudes {hw:.2f} units into the ring at f{hi:03d} (t={hi * DT:.2f}s)")
    # 3. labels: no figure stroke inside a live row's text box
    r = STROKE / 2 * SCALE
    label_hits = 0
    for i in range(N):
        t = i * DT
        s = skeleton(poses[i]); hx, hy = poses[i]["hip"]
        W_ = lambda q: (hx + q[0] * SCALE, hy + q[1] * SCALE)
        segs = [(W_((0, 0)), W_(s["neck"]))]
        for j in (0, 1):
            segs += [(W_(s["neck"]), W_(s["arms"][j][0])), (W_(s["arms"][j][0]), W_(s["arms"][j][1])),
                     (W_((0, 0)), W_(s["legs"][j][0])), (W_(s["legs"][j][0]), W_(s["legs"][j][1]))]
        hc = W_(s["head"])
        for side, t_land in (("L", t_land_l), ("R", t_land_r)):
            for k in range(6):
                if t < t_land + ROW_PITCH_S * k:
                    continue
                box = layout[side][k]["box"]
                if any(seg_box_hit(a, b, r, box) for a, b in segs) or \
                   (box[0] - RING * SCALE <= hc[0] <= box[2] + RING * SCALE and box[1] - RING * SCALE <= hc[1] <= box[3] + RING * SCALE):
                    label_hits += 1
    if label_hits:
        fails.append(f"labels: figure inside a live label box on {label_hits} frame-rows")
    # 4. the aim: the forearm at fire time lies on the line to the mark
    for fire, target, name in ((B["fire_l"], TARGET_L, "left"), (B["fire_r"], TARGET_R, "right")):
        p = poses[int(round(fire * FPS))]
        nk = neck_world(p); hd = hand_world(p)
        want = math.atan2(target[0] - nk[0], target[1] - nk[1])
        got = math.atan2(hd[0] - nk[0], hd[1] - nk[1])
        err = abs(math.degrees(want - got))
        if err > 2.0:
            fails.append(f"aim {name}: forearm off the mark by {err:.1f} deg")
    # 5. the last held frame is the show's frame: no shot dressing left, all windows seated
    tl = int(round((B["fade"] - 0.05) * FPS))
    if fall_y(tl * DT, B["win_host"], WIN_HOST[1]) != WIN_HOST[1] or fall_y(tl * DT, B["win_man"], 18) != 18:
        fails.append("frame: a window is not seated on the last held frame")
    if 1.0 - smooth(seg(tl * DT, B["vig_off"], B["vig_off_end"])) > 0:
        fails.append("frame: the vignette is still on at the last held frame")
    if verbose:
        print(f"gate · motion   peak {peaks[worst]:.2f} px/frame at f{worst:03d} (t={worst * DT:.2f}s) · budget {MAX_PX_PER_FRAME:.0f} px "
              f"= min(640·dt, 12) at {FPS} fps · governor acted on {governed} of {N} frames · camera alone peaks {cam_peak:.2f} px")
        print(f"gate · head     worst intrusion {hw:.2f} units (ring {RING:.0f} = r{HEAD_R:.0f} + stroke/2, shoulder excl. {SHOULDER_EXCL:.0f}) at f{hi:03d}")
        print(f"gate · labels   {label_hits} frame-rows with figure ink inside a live text box")
        print(f"gate · aim      left {AIM_L:.1f} deg -> {TARGET_L} at t={t_land_l:.2f}s · right {AIM_R:.1f} deg -> {TARGET_R} at t={t_land_r:.2f}s")
        print(f"gate · frame    last held frame f{tl:03d}: windows seated, vignette off, hairline off")
        for f in fails:
            print("FAIL ·", f)
    return fails

# ── assembly ────────────────────────────────────────────────────────────────
def build(write=True):
    M = load_metrics()
    layout = row_layout(M)
    poses, peaks, governed = perform()
    t_land_l = arrival(B["fire_l"], poses, TARGET_L)
    t_land_r = arrival(B["fire_r"], poses, TARGET_R)
    if write:
        d = HERE / "svg"; d.mkdir(exist_ok=True)
        for old in d.glob("*.svg"):
            old.unlink()
        for i in range(N):
            (d / f"{i:05d}.svg").write_text(frame_svg(i, poses, M, layout, t_land_l, t_land_r))
        print(f"svg/  {N} frames written")
    fails = check(poses, peaks, governed, layout, t_land_l, t_land_r)
    return fails, dict(peaks=peaks, governed=governed, t_land_l=t_land_l, t_land_r=t_land_r)

def render(stats):
    subprocess.run(["node", str(HERE / "render.mjs"), "frames"], check=True, timeout=1800)
    frames = sorted((HERE / "frames").glob("*.png"))
    assert len(frames) == N, f"{len(frames)} frames rendered, wanted {N}"
    silent = HERE / "silent.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(HERE / "frames" / "%05d.png"),
                    "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", str(silent)], check=True, timeout=900)
    music = Path("/Users/arash/Downloads/artaquest/artaquest-teaser/teaser_music.wav")
    out = Path("/Users/arash/Downloads/artaquest/artaquest-teaser/ArtaQuest_teaser_v2.mp4")
    # loudnorm in two passes so the gain is LINEAR (a single-pass loudnorm pumps), then the fades
    pre = f"atrim=0:{DUR:g},asetpts=PTS-STARTPTS"
    m = subprocess.run(["ffmpeg", "-v", "info", "-i", str(music), "-af", pre + ",loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True, timeout=300).stderr
    j = json.loads(m[m.rfind("{"):m.rfind("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    af = f"{pre},{ln},afade=t=in:st=0:d=1.2,afade=t=out:st={DUR - 2.4:g}:d=2.4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(music), "-af", af,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", str(out)], check=True, timeout=600)
    # the manifest is read back OFF THE DELIVERED FILE, never from the render intent
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,nb_frames,duration,width,height,r_frame_rate",
                                       "-show_entries", "format=duration,size", "-of", "json", str(out)],
                                      capture_output=True, text=True, timeout=60).stdout)
    v = next(s for s in probe["streams"] if s["codec_type"] == "video")
    meas = subprocess.run(["ffmpeg", "-v", "info", "-i", str(out), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True, timeout=300).stderr
    lm = json.loads(meas[meas.rfind("{"):meas.rfind("}") + 1])
    peaks = stats["peaks"]; worst = max(range(N), key=lambda i: peaks[i])
    manifest = dict(
        file=str(out), sha256=hashlib.sha256(out.read_bytes()).hexdigest(), bytes=int(probe["format"]["size"]),
        duration_s=float(probe["format"]["duration"]), frames=int(v["nb_frames"]), size=f'{v["width"]}x{v["height"]}', fps=v["r_frame_rate"],
        audio=dict(source=str(music), integrated_lufs=float(lm["input_i"]), true_peak_dbtp=float(lm["input_tp"]), lra=float(lm["input_lra"]),
                   fade_in_s=1.2, fade_out_s=2.4),
        motion=dict(law="ARTA.md §3: no drawn point of the figure moves more than min(640 px/s·dt, 12 px) per frame, in frame px, camera included",
                    budget_px=MAX_PX_PER_FRAME, peak_px=round(peaks[worst], 3), peak_frame=worst, governed_frames=stats["governed"]),
        head_gate=dict(rule="no limb sample inside the ring's outer edge (r + stroke/2 = 24 units), samples within 13 units of the neck excluded"),
        exceptions=dict(arrow=f"a tool, not a drawn point of the figure: {ARROW_SPEED / FPS:.0f} world px/frame against a {ARROW_SHAFT:.0f} px shaft, so consecutive drawings overlap by half",
                        windows="slabs with mass: ease-in 0.55 s, 8 px overshoot, 0.18 s settle — no per-frame ceiling applies"),
        sample_data="fictional (the kit's own Main sample); no photographic or generated people; the seats are empty",
        lower_thirds=LOWER_THIRDS, scale=SCALE, stroke_units=STROKE,
    )
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"delivered {out}  {manifest['duration_s']:.3f}s  {manifest['frames']} frames  sha256 {manifest['sha256'][:12]}…  "
          f"{manifest['audio']['integrated_lufs']:.1f} LUFS  {manifest['audio']['true_peak_dbtp']:.1f} dBTP")

def main():
    if "--check" in sys.argv:
        fails, _ = build(write=False)
    else:
        fails, stats = build(write=True)
        if not fails and "render" in sys.argv:
            render(stats)
    if fails:
        raise SystemExit(f"{len(fails)} gate(s) failed")
    print("all gates green")

if __name__ == "__main__":
    main()
