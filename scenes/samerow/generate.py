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
lerp, seg, ease = rig.lerp, rig.seg, rig.ease
SPINE, NECK_H, HEAD_R = rig.SPINE, rig.NECK_H, rig.HEAD_R
THIGH, SHIN, UARM, LARM = rig.THIGH, rig.SHIN, rig.UARM, rig.LARM
assert (SPINE, NECK_H, HEAD_R, THIGH, SHIN, UARM, LARM) == (70, 24, 20, 52, 52, 34, 32)

SHOULDER_DROP = 7.0                           # rig units down the spine from the neck: where the arms are DRAWN from

def skeleton(p):
    """The rig's skeleton, with the arms re-rooted at a shoulder SHOULDER_DROP units down the
    spine. The rig roots them at the neck, which is also where the head ring's outer edge sits
    (NECK_H 24 = r20 + stroke/2): a horizontal pointing arm then puts its 8-unit stroke through
    the ring's bottom arc and the ring reads as sitting on a bar (reviewer 1, defect 3). Seven
    units down, a horizontal arm's top edge clears the ring by 3 units. Angles, lengths and the
    joint convention are untouched; only the root moves."""
    s = rig.skeleton(p)
    nx, ny = s["neck"]
    k = 1.0 - SHOULDER_DROP / math.hypot(nx, ny)
    sh = (nx * k, ny * k)
    f = p["face"]
    s["shoulder"] = sh
    s["arms"] = [rig._limb(sh, a[0] * f, a[1] * f, UARM, LARM) for a in (p["la"], p["ra"])]
    return s

# ── frame, clock, palette ───────────────────────────────────────────────────
W, H, FPS, DUR = 1920, 1080, 24, 16.0
N = int(round(DUR * FPS))                     # 384
DT = 1.0 / FPS
GOLD, BLUE = "#E8B923", "#1746DC"             # the pair; never a third
BG, SPACE3 = "#010C17", "#0C1E32"
INK, INK2, INK3 = "#F4F4F5", "#A6A8B0", "#8B8E98"

# ── the figure ──────────────────────────────────────────────────────────────
SCALE = 1.58                                  # rig units -> world px: 218 * 1.58 = 344 px; ring top at 641, INSIDE the host window (top 625)
STROKE = 8.0                                  # rig units, like the film's .fig
RING = HEAD_R + STROKE / 2                    # the head ring's OUTER edge, 24 units
SHOULDER_EXCL = 13.0                          # within this of the neck a limb sample is a shoulder
SHOULDER_MAX = 116                            # arta.ts point(): past this the arm folds at the elbow
ARTA_X, GROUND = 960.0, 985.0                 # the host window's bottom edge; Arta never leaves it
MAX_PX_PER_FRAME = min(640.0 * DT, 12.0)      # ARTA.md §3 at 24 fps: 12 px, no re-derivation
ARROW_SPEED, ARROW_SHAFT = 1200.0, 120.0      # world px/s, world px: 50 px/frame against a 120 px shaft
ARROW_STROKE, ARROW_BARB, ARROW_STICK = 6.0, (22.0, 13.0), 0.20   # rig units; world px (along, across); s it rests on the tick
HAIR_X0, HAIR_X1 = 560.0, 1360.0              # the hairline is a floor mark under Arta, soft-ended; it never runs under a rail
FALL, SETTLE, OVERSHOOT = 0.9, 0.15, 8.0      # a slab with mass: gravity (u^2) for FALL s, OVERSHOOT px past the seat, SETTLE s back

# ── the show's frame (final/Main.dc.html, Spec.dc.html §3 and §10) ──────────
WIN_MAN, WIN_WOMAN, WIN_HOST = (32, 18, 912, 513), (976, 18, 912, 513), (640, 625, 640, 360)
WIN_R = 16
WINDOWS = dict(cm=(WIN_MAN, 'win_man', -560.0, FALL), cw=(WIN_WOMAN, 'win_woman', -560.0, FALL),
               ch=(WIN_HOST, 'win_host', 150.0, 0.8))   # (rect, beat, start y, fall s); the host drops from BEHIND the couple
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
    aim_l=0.10, aim_l_end=1.70,               # the arm RISES from a stand: the film opens on a draw, not a held point
    fire_l=1.75,                              # the arrow leaves the hand; lands ~2.41
    turn=3.00, turn_end=4.60,                 # face -1 -> +1 AND the arm comes down: one motivated move, not a hold + a mirror
    pan=4.75, pan_end=8.25,                   # camera A -> B; his list fades as the frame edge reaches it (never sliced)
    aim_r=6.00, aim_r_end=7.60,
    fire_r=7.65,                              # lands ~8.31, on a B that has the mark 81 px inside the edge
    arm_down_r=8.55, arm_down_r_end=10.05,
    pull=9.90, pull_end=12.20,                # camera B -> C
    win_man=10.60, win_woman=10.85,           # the couple's windows fall (0.9 s), settle by 11.65 / 11.90
    vig_off=10.30, vig_off_end=11.50,
    flinch=12.05,                             # just after the second landing settles: noticing
    gold=12.35,                               # THE SAME ROW
    nod=12.75, nod_end=13.35,                 # one nod, ending on zero as the think begins
    win_host=13.05,                           # emerges from behind the couple, lands 13.85, settles 14.00
    think=13.35, think_mid=13.75, think_end=14.75,   # stand -> fold (elbow bent, forearm hanging) -> forearm up to the chin
    fade=15.75, end=16.00,                    # the payoff holds 1.0 s at full brightness, then a 0.25 s fade
)
RAIL_DRAW = 2.00                              # s for 320 px: 160 px/s, a speed you can follow
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
    """The half-way house on the road to the think: the upper arm swings OUT to the side with the
    ELBOW BENT and the forearm hanging, so the limb travels round the head rather than across it
    and never reads as a second point (a straight horizontal arm did — reviewer 1, defect 5).
    From here the forearm swings up through the left side to the chin."""
    return P(lean=-3, tilt=4, la=(18, 15), ra=(-58, 30), ll=(8, -4), rl=(-8, -8))

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

def shoulder_world(p):
    s = skeleton(p)
    return p["hip"][0] + s["shoulder"][0] * SCALE, p["hip"][1] + s["shoulder"][1] * SCALE

def aim_deg(neck, target):
    dx, dy = target[0] - neck[0], target[1] - neck[1]
    return math.degrees(math.atan2(dx, dy))

TARGET_L = (TL_L_X + RAIL_INSET + RAIL_W / 2, RAIL_TOP)            # (44, 645) his birth tick
TARGET_R = (TL_R_X + TL_W - RAIL_INSET - RAIL_W / 2, RAIL_TOP)     # (1876, 645) hers

_sh0 = shoulder_world(grounded(A_point(-95, -1)))
AIM_L = aim_deg(_sh0, TARGET_L)
AIM_R = aim_deg(_sh0, TARGET_R)

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
    """The turn, continuous (ARTA.md §3), and MOTIVATED: it starts from the left-facing point and
    ends in the right-facing stand, so the pointing arm sweeps down and across as the body turns.
    A stand mirrored through a frontal stand read as standing still while the camera moved
    (reviewer 1, defect 9); an arm coming down while the shoulders swing round cannot. The free
    arm counter-swings with a bent elbow, and the weight shifts: the rear knee lifts and bends
    (the foot comes ~8 units off the floor and replants), so the legs are never one line through
    the edge-on moment — reviewer 2's "pole with two stubs". The planted foot moves under
    3 units, so nothing skates."""
    k = smooth(u)
    p = blend_pose(POINT_L, STAND_R, k)
    sw = math.sin(math.pi * k)
    p["la"] = (p["la"][0] + 22 * sw, p["la"][1] + 14 * sw)
    p["ll"] = (p["ll"][0] + 3 * sw, p["ll"][1] - 6 * sw)
    p["rl"] = (p["rl"][0] + 20 * sw, p["rl"][1] - 44 * sw)
    p["sq"] = 1.0 - 0.03 * sw
    return grounded(p)
FOLD = grounded(A_fold()); THINK = grounded(A_think())

def authored(t):
    """The pose Arta WANTS at t. The governor below is what it gets."""
    if t < B["aim_l"]:
        return STAND_L
    if t < B["turn"]:
        return blend_pose(STAND_L, POINT_L, smooth(seg(t, B["aim_l"], B["aim_l_end"])))
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
        k = cycles(t, B["nod"], B["nod_end"] - B["nod"], 1)
        p = A_stand(); p["tilt"] += 16 * k; p["lean"] += 3 * k
        return grounded(p)
    if t < B["think_mid"]:
        return grounded(blend_pose(A_stand(), A_fold(), smooth(seg(t, B["think"], B["think_mid"]))))
    return grounded(blend_pose(A_fold(), A_think(), smooth(seg(t, B["think_mid"], B["think_end"]))))

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
CAM_A = (1.40, 660.0, 715.0)      # his side + Arta:  world x -26..1346; his birth tick at frame x 81
CAM_B = (1.24, 1179.0, 760.0)     # her side + Arta:  world x 405..1953; her birth tick's right edge at frame x 1839 (81 px in)
CAM_C = (1.00, 960.0, 540.0)      # the frame

def camera(t):
    s, cx, cy = CAM_A
    s = lerp(s, 1.38, seg(t, 0.0, B["pan"]))                       # a creep, so A is never a still
    cx = lerp(cx, 680.0, seg(t, 0.0, B["pan"]))
    u = trapz(seg(t, B["pan"], B["pan_end"]), 0.2)
    s, cx, cy = lerp(s, CAM_B[0], u), lerp(cx, CAM_B[1], u), lerp(cy, CAM_B[2], u)
    u = smooth(seg(t, B["pull"], B["pull_end"]))
    return lerp(s, CAM_C[0], u), lerp(cx, CAM_C[1], u), lerp(cy, CAM_C[2], u)

def frame_edges(cam):
    """World x of the frame's left and right edges."""
    s, cx, _ = cam
    return cx - (W / 2) / s, cx + (W / 2) / s

def list_op(side, cam):
    """A list's opacity against the frame edge: it fades OUT over the 32 world px before the edge
    reaches its tick and back IN as the edge leaves, so the frame edge never slices a word — or a
    tick (reviewers 1 and 2: 88 frames of guillotined type in the pan and the pull). Full while
    the edge is at or outside the frame's own edge (world x 0 / 1920, where the pull ends); gone
    by the time the edge touches the tick."""
    l, r = frame_edges(cam)
    if side == "L":
        return max(0.0, min(1.0, (TL_L_X - l) / 32.0))
    return max(0.0, min(1.0, (r - (TL_R_X + TL_W - 8)) / 32.0))

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
    """One shaft in flight from the hand to the mark it was aimed at; it LANDS there, rests on the
    tick for ARROW_STICK s while the tick fades in, then goes. It used to fly on out of the frame
    and the rail began by timing alone. Returns (tip, tail, dir, opacity) in world px, or None."""
    for fire, target in ((B["fire_l"], TARGET_L), (B["fire_r"], TARGET_R)):
        age = t - fire
        if age < 0:
            continue
        p = poses[int(round(fire * FPS))]
        hx, hy = hand_world(p)
        dx, dy = target[0] - hx, target[1] - hy
        L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
        t_arr = fire + (L - 18.0) / ARROW_SPEED
        if t > t_arr + ARROW_STICK:
            continue
        d = min(L, 18.0 + ARROW_SPEED * age)                             # tip distance from the hand
        tip = (hx + ux * d, hy + uy * d)
        tail = (tip[0] - ux * ARROW_SHAFT, tip[1] - uy * ARROW_SHAFT)
        op = min(1.0, age / 0.12) * (1.0 - seg(t, t_arr + ARROW_STICK - 0.08, t_arr + ARROW_STICK))
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
def fall_y(t, t0, y_final, y_from=-560.0, dur=FALL):
    """A slab with mass: gravity (u^2) over `dur` s to OVERSHOOT px past its seat, then a SETTLE s
    ease-out back. The old cubic ease-in over 0.55 s took 200 px steps on its last frames — five
    positions of a 360 px slab (reviewer 2, defect 2); u^2 over 0.9 s keeps the last step under
    55 px, and the slab is drawn with a motion blur proportional to that step."""
    u = seg(t, t0, t0 + dur)
    if u <= 0:
        return None
    y = lerp(y_from, y_final + OVERSHOOT, u * u)
    if u >= 1.0:
        y = lerp(y_final + OVERSHOOT, y_final, ease_out(seg(t, t0 + dur, t0 + dur + SETTLE)))
    return y

def window_y(t, key):
    win, beat, y_from, dur = WINDOWS[key]
    return fall_y(t, B[beat], win[1], y_from, dur)

def window_seated(t, key):
    return window_y(t, key) == WINDOWS[key][0][1]

def lower_third_at(key):
    """When a window's lower-third rises: settled, plus the kit's 0.17 s beat."""
    _, beat, _, dur = WINDOWS[key]
    return B[beat] + dur + SETTLE + 0.17

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
    out = {"L": [], "R": [], "M": M}
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
    boxes = []
    for j, line in enumerate(lines):
        x, y = wx + 10 + 20, top + 10 + lh * j + nb
        parts.append(text_el(line, name_font, x, y, INK))
        m = M[f"name{key}{j}"]
        boxes.append((x + m["x"], y + m["y"], x + m["x"] + m["w"], y + m["y"] + m["h"]))
    st = bottom - sub_h
    parts.append(f'<rect x="{wx + 10}" y="{num(st)}" width="{num(sub_w)}" height="{sub_h}" fill="#000000" fill-opacity="0.8"/>')
    x, y = wx + 10 + 20, st + 6 + _baseline(SUB_FONT, 48)
    parts.append(text_el(sub, SUB_FONT, x, y, INK))
    m = M[f"sub{key}"]
    boxes.append((x + m["x"], y + m["y"], x + m["x"] + m["w"], y + m["y"] + m["h"]))
    return "".join(parts), boxes

# ── one frame as SVG ────────────────────────────────────────────────────────
def figure_svg(p):
    s = skeleton(p)
    hx, hy = p["hip"]
    def pl(*pts):
        return '<path d="M' + "L".join(f"{num(x)} {num(y)}" for x, y in pts) + '"/>'
    body = [pl((0, 0), s["neck"])]
    for i in (0, 1):
        body.append(pl(s["shoulder"], s["arms"][i][0], s["arms"][i][1]))
        body.append(pl((0, 0), s["legs"][i][0], s["legs"][i][1]))
    body.append(f'<circle cx="{num(s["head"][0])}" cy="{num(s["head"][1])}" r="{num(HEAD_R)}"/>')
    return (f'<g transform="translate({num(hx)} {num(hy)}) scale({SCALE})" fill="none" stroke="{GOLD}" '
            f'stroke-width="{STROKE}" stroke-linecap="round" stroke-linejoin="round">' + "".join(body) + "</g>")

def hairline_op(t):
    return (0.20 + 0.05 * math.sin(2 * math.pi * 0.08 * t)) * (1.0 - smooth(seg(t, B["win_host"] + 0.6, B["win_host"] + 0.9)))

def frame_svg(frame, poses, M, layout, t_land_l, t_land_r):
    t = frame * DT
    cam = camera(t)
    s, cx, cy = cam
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
           '<defs>',
           f'<radialGradient id="amb" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="{SPACE3}" stop-opacity="0.85"/>'
           f'<stop offset="0.55" stop-color="{SPACE3}" stop-opacity="0.35"/><stop offset="1" stop-color="{SPACE3}" stop-opacity="0"/></radialGradient>',
           '<radialGradient id="vig" cx="0.5" cy="0.5" r="0.5"><stop offset="0.50" stop-color="#000" stop-opacity="0"/>'
           '<stop offset="0.82" stop-color="#000" stop-opacity="0.16"/><stop offset="1" stop-color="#000" stop-opacity="0.42"/></radialGradient>',
           f'<linearGradient id="hair" gradientUnits="userSpaceOnUse" x1="{num(HAIR_X0)}" y1="0" x2="{num(HAIR_X1)}" y2="0">'
           f'<stop offset="0" stop-color="{INK3}" stop-opacity="0"/><stop offset="0.25" stop-color="{INK3}" stop-opacity="1"/>'
           f'<stop offset="0.75" stop-color="{INK3}" stop-opacity="1"/><stop offset="1" stop-color="{INK3}" stop-opacity="0"/></linearGradient>']
    for k, (wx, wy, ww, wh) in (("cm", WIN_MAN), ("cw", WIN_WOMAN), ("ch", WIN_HOST)):
        out.append(f'<clipPath id="{k}"><rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="{WIN_R}"/></clipPath>')
    # the host emerges from BEHIND the couple's windows: nothing of it is drawn above their bottom edge
    out.append(f'<clipPath id="below"><rect x="-2000" y="{WIN_MAN[1] + WIN_MAN[3]}" width="6000" height="3000"/></clipPath>')
    blur = {}
    for key in WINDOWS:
        y0, y1 = window_y(t - DT, key), window_y(t, key)
        v = 0.0 if y0 is None or y1 is None else abs(y1 - y0)
        if v > 6.0:
            blur[key] = v
            out.append(f'<filter id="mb_{key}" x="-5%" y="-40%" width="110%" height="180%">'
                       f'<feGaussianBlur stdDeviation="0 {num(v / 3.0)}"/></filter>')
    out.append('</defs>')
    out.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
    out.append(f'<g transform="translate({W / 2} {H / 2}) scale({num(s)}) translate({num(-cx)} {num(-cy)})">')

    # the ambient and the hairline belong to the shot; both are gone when the shot becomes the frame.
    # The hairline is a soft-ended floor mark under Arta (HAIR_X0..HAIR_X1): it never runs under a
    # rail, so a sixth row rising from +24 px is never struck through by it (reviewer 1, defect 4).
    stage = 1.0 - smooth(seg(t, B["vig_off"], B["vig_off_end"]))
    if stage > 0:
        out.append(f'<ellipse cx="{ARTA_X}" cy="820" rx="760" ry="520" fill="url(#amb)" opacity="{num(stage)}"/>')
    hair = hairline_op(t)
    if hair > 0:
        out.append(f'<line x1="{num(HAIR_X0)}" y1="{GROUND}" x2="{num(HAIR_X1)}" y2="{GROUND}" stroke="url(#hair)" stroke-width="1.5" opacity="{num(hair)}"/>')

    # the windows, behind everything; the host first (beneath the couple) and clipped below them
    for key, lt in (("ch", None), ("cm", ("M",) + LT_MAN), ("cw", ("W",) + LT_WOMAN)):
        y = window_y(t, key)
        if y is None:
            continue
        wx, wy, ww, wh = WINDOWS[key][0]
        f = f' filter="url(#mb_{key})"' if key in blur else ""
        rect = f'<rect x="{wx}" y="{num(y)}" width="{ww}" height="{wh}" rx="{WIN_R}" fill="{SPACE3}"{f}/>'
        out.append(f'<g clip-path="url(#below)">{rect}</g>' if key == "ch" else rect)
        if lt and LOWER_THIRDS:
            op, dy = rise(t, lower_third_at(key))
            if op > 0:
                nf = NAME_FONT_2 if len(lt[1]) > 1 else NAME_FONT_1
                svg, _ = lower_third(M, WINDOWS[key][0], lt[0], lt[1], lt[2], nf)
                out.append(f'<g clip-path="url(#{key})"><g opacity="{num(op)}" transform="translate(0 {num(dy)})">' + svg + '</g></g>')

    # the rails
    for side, rows, x0, t_land in (("L", ROWS_L, TL_L_X, t_land_l), ("R", ROWS_R, TL_R_X, t_land_r)):
        st = rail_state(t, t_land, side)
        lop = list_op(side, cam)
        if not st["visible"] or lop <= 0:
            continue
        out.append(f'<g opacity="{num(lop)}">')
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
        out.append('</g>')

    out.append(figure_svg(poses[frame]))

    a = arrow_at(t, poses)
    if a:
        (tx, ty), (bx, by), (ux, uy), op = a
        px, py = -uy, ux
        bw, bo = ARROW_BARB
        d = (f"M{num(bx)} {num(by)}L{num(tx)} {num(ty)}"
             f"M{num(tx - ux * bw + px * bo)} {num(ty - uy * bw + py * bo)}L{num(tx)} {num(ty)}"
             f"L{num(tx - ux * bw - px * bo)} {num(ty - uy * bw - py * bo)}")
        out.append(f'<path d="{d}" fill="none" stroke="{BLUE}" stroke-width="{num(ARROW_STROKE * SCALE)}" '
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
    for chain in ([s["shoulder"], s["arms"][0][0], s["arms"][0][1]], [s["shoulder"], s["arms"][1][0], s["arms"][1][1]],
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
            segs += [(W_(s["shoulder"]), W_(s["arms"][j][0])), (W_(s["arms"][j][0]), W_(s["arms"][j][1])),
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
    # 4. the aim: the whole arm at fire time lies on the line from the shoulder to the mark
    for fire, target, name in ((B["fire_l"], TARGET_L, "left"), (B["fire_r"], TARGET_R, "right")):
        p = poses[int(round(fire * FPS))]
        nk = shoulder_world(p); hd = hand_world(p)
        want = math.atan2(target[0] - nk[0], target[1] - nk[1])
        got = math.atan2(hd[0] - nk[0], hd[1] - nk[1])
        err = abs(math.degrees(want - got))
        if err > 2.0:
            fails.append(f"aim {name}: forearm off the mark by {err:.1f} deg")
    # 5. the last held frame is the show's frame: no shot dressing left, all THREE windows seated,
    #    and the whole figure (stroke included) inside the host's window — Arta in the host's chair
    tl = int(round((B["fade"] - 0.05) * FPS))
    for key in WINDOWS:
        if not window_seated(tl * DT, key):
            fails.append(f"frame: window {key} is not seated on the last held frame")
    if 1.0 - smooth(seg(tl * DT, B["vig_off"], B["vig_off_end"])) > 0:
        fails.append("frame: the vignette is still on at the last held frame")
    if hairline_op(tl * DT) > 0:
        fails.append("frame: the hairline is still on at the last held frame")
    hx0, hy0, hw_, hh_ = WIN_HOST
    fig_x0 = fig_y0 = 1e9; fig_x1 = fig_y1 = -1e9
    for i in range(int(round(B["win_host"] * FPS)), N):                # from the host's fall to the end
        s = skeleton(poses[i]); ox, oy = poses[i]["hip"]
        for (x, y) in world_pts(poses[i]):
            fig_x0, fig_x1 = min(fig_x0, x - r), max(fig_x1, x + r)
            fig_y0, fig_y1 = min(fig_y0, y - r), max(fig_y1, y + r)
        hc = (ox + s["head"][0] * SCALE, oy + s["head"][1] * SCALE)
        fig_x0, fig_x1 = min(fig_x0, hc[0] - RING * SCALE), max(fig_x1, hc[0] + RING * SCALE)
        fig_y0 = min(fig_y0, hc[1] - RING * SCALE)
    if fig_y0 < hy0 or fig_x0 < hx0 or fig_x1 > hx0 + hw_ or fig_y1 > hy0 + hh_ + r + 0.5:
        fails.append(f"host: the figure leaves the host window (x {fig_x0:.0f}..{fig_x1:.0f}, y {fig_y0:.0f}..{fig_y1:.0f}) "
                     f"against ({hx0}, {hy0}, {hx0 + hw_}, {hy0 + hh_})")
    # 6. every mark is INSIDE the frame when its arrow lands, with a margin (reviewer 2, defect 1)
    for t_land, target, name in ((t_land_l, TARGET_L, "left"), (t_land_r, TARGET_R, "right")):
        fx, fy = to_frame(camera(t_land), *target)
        if not (24 <= fx <= W - 24 and 24 <= fy <= H - 24):
            fails.append(f"arrival {name}: the mark is at frame ({fx:.0f}, {fy:.0f}) when the arrow lands at t={t_land:.2f}s")
    # 7. no visible type is cut by the frame edge, ever: every live text box (rows and lower-thirds)
    #    at effective opacity > 0.02 lies wholly inside the frame (reviewers 1 and 2)
    edge_cuts = 0
    for i in range(N):
        t = i * DT; cam = camera(i * DT)
        boxes = []
        for side, t_land in (("L", t_land_l), ("R", t_land_r)):
            lop = list_op(side, cam)
            if t < t_land or lop <= 0.02:
                continue
            for k in range(6):
                op, _ = rise(t, t_land + ROW_PITCH_S * k + (0.08 if k == 0 else 0.0))
                if op * lop > 0.02:
                    boxes.append((f"{side}{k}", layout[side][k]["box"]))
        if LOWER_THIRDS:
            for key, lt in (("cm", ("M",) + LT_MAN), ("cw", ("W",) + LT_WOMAN)):
                op, _ = rise(t, lower_third_at(key))
                if op > 0.02:
                    nf = NAME_FONT_2 if len(lt[1]) > 1 else NAME_FONT_1
                    _, bx = lower_third(layout["M"], WINDOWS[key][0], lt[0], lt[1], lt[2], nf)
                    boxes += [(key, b) for b in bx]
        for name, (x0, y0, x1, y1) in boxes:
            fx0, fy0 = to_frame(cam, x0, y0); fx1, fy1 = to_frame(cam, x1, y1)
            if fx0 < 0 or fx1 > W or fy0 < 0 or fy1 > H:
                edge_cuts += 1
                if edge_cuts <= 3:
                    fails.append(f"edge: text {name} cut by the frame at f{i:03d} (frame x {fx0:.0f}..{fx1:.0f}, y {fy0:.0f}..{fy1:.0f})")
    if edge_cuts > 3:
        fails.append(f"edge: {edge_cuts} frame-boxes of type cut by the frame edge in all")
    # 8. no slab takes a step over 60 frame px while it falls, and the couple's windows are never
    #    overdrawn by the host: the host is drawn first AND clipped below their bottom edge
    step_worst, step_key, step_frame = 0.0, "", 0
    for key in WINDOWS:
        for i in range(1, N):
            y0, y1 = window_y((i - 1) * DT, key), window_y(i * DT, key)
            if y0 is not None and y1 is not None and abs(y1 - y0) > step_worst:
                step_worst, step_key, step_frame = abs(y1 - y0), key, i
    if step_worst > 60.0:
        fails.append(f"windows: slab {step_key} steps {step_worst:.0f} px at f{step_frame:03d}")
    if verbose:
        print(f"gate · motion   peak {peaks[worst]:.2f} px/frame at f{worst:03d} (t={worst * DT:.2f}s) · budget {MAX_PX_PER_FRAME:.0f} px "
              f"= min(640·dt, 12) at {FPS} fps · governor acted on {governed} of {N} frames · camera alone peaks {cam_peak:.2f} px")
        print(f"gate · head     worst intrusion {hw:.2f} units (ring {RING:.0f} = r{HEAD_R:.0f} + stroke/2, shoulder excl. {SHOULDER_EXCL:.0f}) at f{hi:03d}")
        print(f"gate · labels   {label_hits} frame-rows with figure ink inside a live text box")
        print(f"gate · aim      left {AIM_L:.1f} deg -> {TARGET_L} at t={t_land_l:.2f}s · right {AIM_R:.1f} deg -> {TARGET_R} at t={t_land_r:.2f}s")
        print(f"gate · frame    last held frame f{tl:03d}: {len(WINDOWS)} windows seated, vignette off, hairline off; "
              f"figure x {fig_x0:.0f}..{fig_x1:.0f} y {fig_y0:.0f}..{fig_y1:.0f} inside the host window {WIN_HOST}")
        for t_land, target, name in ((t_land_l, TARGET_L, "left"), (t_land_r, TARGET_R, "right")):
            fx, fy = to_frame(camera(t_land), *target)
            print(f"gate · arrival  {name} mark at frame ({fx:.0f}, {fy:.0f}) at t={t_land:.2f}s, {min(fx, W - fx):.0f} px from the nearer edge")
        print(f"gate · edge     {edge_cuts} frame-boxes of visible type cut by the frame edge")
        print(f"gate · windows  largest slab step {step_worst:.0f} px ({step_key} at f{step_frame:03d}); host drawn beneath the couple, clipped below y={WIN_MAN[1] + WIN_MAN[3]}")
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
        figure=dict(shoulder_drop_units=SHOULDER_DROP, note="the arms are drawn from a shoulder 7 rig units down the spine; the rig's angles and lengths are unchanged"),
        exceptions=dict(arrow=f"a tool, not a drawn point of the figure: {ARROW_SPEED / FPS:.0f} world px/frame against a {ARROW_SHAFT:.0f} px shaft, so consecutive drawings overlap by half",
                        windows=f"slabs with mass: gravity (u^2) over {FALL} s ({WINDOWS['ch'][3]} s for the host, from behind the couple), "
                                f"{OVERSHOOT:.0f} px overshoot, {SETTLE} s settle; steps capped at 60 px and motion-blurred; no per-frame ceiling applies"),
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
