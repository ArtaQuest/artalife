#!/usr/bin/env python3
"""
"Undefined" — a 50-second looping animated SVG, in the Animation-vs-Math idiom.

One gold stick figure. White glyphs as physical props with mass. A blue threat.
The figure assembles 1 + 1 = 2, tears out the +, drags in a ÷, then swaps the
second 1 for a 0 — and the answer slot STAYS EMPTY. It taps it. Blue light gets
out. It hauls the 0 back out and sets it down on the other side instead:

    0 ÷ 1 = 0

Same two symbols, opposite order. One is undefined, one is just zero. No words.

Output is SVG + SMIL only. The publish gate (AQ\\Svg) admits a drawing rendered
in an <img>, where scripts never execute — so every pose is computed here and
sampled onto the timeline:

    serialise(None) -> scene.svg  (SMIL `values` lists)
    serialise(t)    -> one still  (same samplers, attributes baked)

...which means the contact sheet I review IS the animation, not a sibling of it.

Load-bearing style choices:
  * The figure uses calcMode="discrete" — no interpolation, so each sample IS a
    drawing. It holds on twos when calm and drops to singles on fast action,
    decided from measured joint speed (see figure_pose). Tweened limbs read as
    cheap Flash; held drawings read as animation.
  * Camera and props run 24 fps linear so pushes and drifts stay smooth.
  * A stick figure has no face, so a mirror-flip only reads as a TURN when it
    lands on a held pose. Every direction change gets a pivot beat; the lint at
    the bottom exists to catch the ones that don't.
  * vector-effect="non-scaling-stroke" throughout: the line holds a constant
    device width at 430px and at 1290px, which is the whole reason a scene beats
    a video in a feed card.
  * No <filter> is allowed, so every glow is a radialGradient halo.

Usage:  python3 generate.py             -> scene.svg + continuity lint
        python3 generate.py frames [t…] -> frames/*.svg stills for review
"""

import math, os, re, sys

# ── palette (brand: gold + blue sum to white per channel) ───────────────────
BG, GOLD, BLUE, WHITE = "#010C17", "#E8B923", "#1746DC", "#FFFFFF"

W, H = 1600, 900
CX, CY = W / 2, H / 2
GROUND = 640.0
DUR = 47.5
FPS_FIG, FPS_SMOOTH = 24, 24
STRIDE = 110.0          # px per stride; sets the walk cadence for any distance

# Glyph slots along the equation, at 160 apart rather than 140: the figure has
# to stand SOMEWHERE, and at 140 every rest position overlapped a glyph and the
# silhouette turned to mush. G* are the gap centres between slots — the figure
# only ever comes to rest on one of them.
S1, SOP, S2, SEQ, SR = 400.0, 600.0, 800.0, 1000.0, 1200.0
G1, G2, G3, G4 = 495.0, 705.0, 895.0, 1102.0
DROP = 60.0             # props fall from just above the visible top edge
CATCH = 235.0           # height above ground at which a falling prop is caught
CARRY = 150.0           # height the 0 rides at while carried

# ── beat clock ──────────────────────────────────────────────────────────────
# The film opens mid-situation: the figure is already looking at the 1. The
# three seconds a walk-on entrance would cost are spent on the void instead.
B = dict(
    one_in=0.3,
    # act one — arithmetic. The figure shoves the 1 into place; a second 1 falls;
    # the + and = arrive on their own, as a consequence.
    reach=1.3, touch=2.1, unreach=2.9, wind=3.2, push1=3.4, push_end=5.2,
    two_drop=5.3, two_land=6.5, pivot_r=6.5,
    plus=7.0, eq=7.8, pop=8.6, cheer=9.2, land_j=10.6,
    # act two — the figure edits the equation. Props FALL to it and are caught,
    # rather than sliding in across the finished equation and colliding with it.
    yank=11.2, throw=11.4, tossed=12.6,
    div_drop=13.2, div_catch=14.1, div_set=14.9,
    walk_1=15.4, pull1=16.5, toss1=17.7,
    zero_drop=18.2, zero_catch=19.1, zero_set=20.2,
    to_slot=21.0, tap=22.2, peer=23.8,
    # act three — the empty slot answers back
    crack=25.4, open_=28.4, recoil=28.6, flee=29.4,
    pivot_brace=31.2, brace=31.4, braced=31.9,
    lunge=35.0, plant=35.4, grab=35.8, lift=36.2, snap=37.0,
    # act four — 0 ÷ 1 = 0
    carry=38.3, walkc=38.9, setdown=40.4, hop=39.6, land=41.0, down=41.2,
    up=41.5, zres=41.4, back=41.8, watch=43.1, fade=45.0, end=47.5,
)

# ── easing ──────────────────────────────────────────────────────────────────
def seg(t, a, b):
    if b <= a:
        return 1.0 if t >= b else 0.0
    return max(0.0, min(1.0, (t - a) / (b - a)))

def ease(u):     return u * u * (3 - 2 * u)
def ease_out(u): return 1 - (1 - u) ** 3
def ease_in(u):  return u ** 3
def back_(u):
    s = 1.9
    return 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2
def lerp(a, b, u):  return a + (b - a) * u

def trapz(u, r=0.25):
    """Trapezoidal velocity: accelerate over the first r, cruise, decelerate over
    the last r. How a walk actually distributes distance over time."""
    if u < r:      return 0.5 * u * u / (r * (1 - r))
    if u > 1 - r:  return 1.0 - 0.5 * (1 - u) ** 2 / (r * (1 - r))
    return (u - r / 2) / (1 - r)
def ramp(t, a, b, v0, v1, f=ease):  return lerp(v0, v1, f(seg(t, a, b)))

def num(x):
    """One decimal, minimally spelled: 0.5 -> .5, -0.5 -> -.5, 12.0 -> 12.
    At a 1600-unit viewBox one decimal is ~0.04 device px in a feed card, so the
    precision is spent where it cannot be seen; dropping the leading zero is
    free."""
    s = f"{float(x):.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    if s.startswith("0."):
        s = s[1:]
    elif s.startswith("-0."):
        s = "-" + s[2:]
    return "0" if s in ("-0", "0") else s

def _j(*vals):
    """Join path numbers with the minimum separator the SVG grammar allows.

    A separator is needed when the next number starts with a digit — and ALSO
    when it starts with "." and the previous number has no "." of its own. SVG
    number tokenising is greedy: "19" followed by ".5" is the single number 19.5,
    not 19 and 0.5. Getting that wrong yields a path with an odd coordinate
    count; Chrome then rejects the ENTIRE values list and silently falls back to
    the base attribute, so the limb just stops moving and nothing reports it."""
    out, prev = "", ""
    for v in vals:
        t = num(v)
        if out and (t[0].isdigit() or (t[0] == "." and "." not in prev)):
            out += " "
        out += t
        prev = t
    return out

_TOK = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")

def check_path(d):
    """Re-tokenise an emitted path the way a browser would and assert it says
    what it was meant to say. The compact encoding above is exactly the kind of
    thing that is wrong in one frame out of a thousand, and a browser answers a
    malformed values list by ignoring it rather than complaining."""
    want = {"M": 2, "m": 2, "L": 2, "l": 2, "H": 1, "h": 1, "V": 1, "v": 1,
            "Q": 4, "q": 4, "C": 6, "c": 6, "A": 7, "a": 7, "Z": 0, "z": 0}
    i, n = 0, len(d)
    while i < n:
        c = d[i]
        if c not in want:
            raise ValueError(f"unexpected {c!r} in path {d!r}")
        i += 1
        got = 0
        while i < n:
            m = _TOK.match(d, i)
            if not m:
                break
            got += 1
            i = m.end()
            while i < n and d[i] in " ,":
                i += 1
        k = want[c]
        if k == 0:
            if got:
                raise ValueError(f"{c} took {got} numbers in {d!r}")
        elif got == 0 or got % k:
            raise ValueError(f"{c} wants a multiple of {k} numbers, tokenised {got}: {d!r}")
    return d

def poly(*pts):  # noqa: D401
    """An absolute moveto then relative linetos. Deltas are taken between the
    ROUNDED points, so the compact form is exactly what the absolute form was —
    no accumulated drift."""
    r = [(round(x, 1), round(y, 1)) for x, y in pts]
    d = "M" + _j(r[0][0], r[0][1])
    for i in range(1, len(r)):
        d += "l" + _j(r[i][0] - r[i - 1][0], r[i][1] - r[i - 1][1])
    return check_path(d)

def num_t(x):
    s = f"{x:.5f}".rstrip("0").rstrip(".").lstrip("0") or "0"
    return s or "0"

# ── the figure: a jointed skeleton, forward-kinematic ───────────────────────
SPINE, NECK_H, HEAD_R = 70.0, 24.0, 20.0
THIGH, SHIN, UARM, LARM = 52.0, 52.0, 34.0, 32.0
HIP_Y = GROUND - THIGH - SHIN

def pose(hip, lean=0.0, tilt=0.0, face=1, la=(9, 12), ra=(-9, -12),
         ll=(3, -5), rl=(-3, -5), sq=1.0, bre=1.0):
    """Joint angles in degrees; 0 = straight down, + = toward +x. `face` = -1
    mirrors the figure by negating every angle — all a stick figure needs."""
    return dict(hip=hip, lean=lean, tilt=tilt, face=face,
                la=la, ra=ra, ll=ll, rl=rl, sq=sq, bre=bre)

def _limb(root, a1, a2, l1, l2):
    r1 = math.radians(a1)
    j = (root[0] + l1 * math.sin(r1), root[1] + l1 * math.cos(r1))
    r2 = math.radians(a1 + a2)
    return j, (j[0] + l2 * math.sin(r2), j[1] + l2 * math.cos(r2))

def skeleton(p):
    """Resolve a pose into drawable parts in figure-local coords (hip at the
    origin) — the root translate carries the world position."""
    f, sq = p["face"], p["sq"]
    lean = math.radians(p["lean"] * f)
    bre = p.get("bre", 1.0)
    neck = (SPINE * bre * math.sin(lean), -SPINE * bre * math.cos(lean) * sq)
    hr = math.radians((p["lean"] + p["tilt"]) * f)
    head = (neck[0] + NECK_H * math.sin(hr), neck[1] - NECK_H * math.cos(hr))
    arms = [_limb(neck, a[0] * f, a[1] * f, UARM, LARM) for a in (p["la"], p["ra"])]
    legs = [_limb((0.0, 0.0), a[0] * f, a[1] * f, THIGH * sq, SHIN * sq)
            for a in (p["ll"], p["rl"])]
    return dict(neck=neck, head=head, arms=arms, legs=legs)

def blend(p, q, u):
    o = {k: lerp(p.get(k, 1.0 if k == "bre" else 0.0), q.get(k, 1.0 if k == "bre" else 0.0), u)
         for k in ("lean", "tilt", "sq", "bre")}
    o["hip"] = (lerp(p["hip"][0], q["hip"][0], u), lerp(p["hip"][1], q["hip"][1], u))
    o["face"] = p["face"] if u < 0.5 else q["face"]
    for k in ("la", "ra", "ll", "rl"):
        o[k] = (lerp(p[k][0], q[k][0], u), lerp(p[k][1], q[k][1], u))
    return o

# ── pose library ────────────────────────────────────────────────────────────
def P_stand(x, face=1):
    return pose((x, HIP_Y), face=face)

def P_walk(x, ph, face=1):
    th = 2 * math.pi * ph
    return pose((x, HIP_Y - 2 + 3.0 * abs(math.cos(th))), face=face, lean=7,
                la=(-20 * math.sin(th), 16), ra=(20 * math.sin(th), 16),
                ll=(26 * math.sin(th), -16 - 16 * max(0, math.cos(th))),
                rl=(-26 * math.sin(th), -16 - 16 * max(0, -math.cos(th))))

def P_reach(x, face=1, k=1.0):
    return pose((x, HIP_Y - 1), face=face, lean=10 * k, tilt=6 * k,
                la=(20, 18), ra=(70 + 22 * k, -12 * k), ll=(16, -12), rl=(-14, -10))

def P_push(x, face=1, k=1.0):
    return pose((x, HIP_Y + 4 * k), face=face, lean=20 * k, tilt=-4,
                la=(74 + 8 * k, -6), ra=(78 + 10 * k, -8),
                ll=(34 * k, -26 * k), rl=(-26 * k, -34 * k))

def P_cheer(x, face=1):
    """Airborne. 85px on a 218px figure — a 45px hop read as a shrug."""
    return pose((x, HIP_Y - 85), face=face, tilt=-6,
                la=(146, 10), ra=(-146, -10), ll=(26, -46), rl=(-24, -44))

def P_haul(x, face=1, k=1.0):
    """Dragging something heavy: braced back, both arms low and forward."""
    return pose((x, HIP_Y + 5), face=face, lean=-16 * k, tilt=4,
                la=(62, 10), ra=(72, 6), ll=(-30 * k, -18), rl=(34 * k, -30))

def P_peer(x, face=1, k=1.0):
    return pose((x, HIP_Y + 10 * k), face=face, lean=30 * k, tilt=10 * k,
                la=(40, 60 * k), ra=(48, 56 * k), ll=(24 * k, -30 * k), rl=(-22 * k, -28 * k))

def P_brace(x, face=1, k=1.0):
    """Holding on against the pull — leaning away, arms overhead, feet planted."""
    return pose((x, HIP_Y + 8 * k), face=face, lean=-30 * k, tilt=-14 * k,
                la=(132 * k, 26), ra=(146 * k, 20), ll=(-38 * k, -20), rl=(40 * k, -34))

def P_lift(x, face=1):
    """Holding the 0 aloft — one arm up, the trophy beat."""
    return pose((x, HIP_Y - 2), face=face, lean=-6, tilt=-10,
                la=(30, 20), ra=(-158, -14), ll=(12, -10), rl=(-16, -12))

def P_dash(x, face=1):
    """An explosive stride out of the brace — one big pose, not a cycle."""
    return pose((x, HIP_Y + 2), face=face, lean=26, tilt=-6,
                la=(-52, 20), ra=(58, 14), ll=(46, -18), rl=(-40, -46))

def P_carry(x, ph, face=1):
    """Walking with the 0 held out in front, high enough that it clears the ÷ it
    passes over on the way. The hand ends up ~10px outside the 0's near edge."""
    th = 2 * math.pi * ph
    return pose((x, HIP_Y - 1 + 2.5 * abs(math.cos(th))), face=face, lean=-8, tilt=2,
                la=(112, 8), ra=(120, 4),
                ll=(22 * math.sin(th), -14 - 14 * max(0, math.cos(th))),
                rl=(-22 * math.sin(th), -14 - 14 * max(0, -math.cos(th))))

def P_reachup(x, face=1, k=1.0):
    """Both arms up to catch a falling glyph. The hand lands near
    (x + 25*face, GROUND - CATCH), which is where the drop is aimed."""
    return pose((x, HIP_Y - 6 * k), face=face, lean=-4 * k, tilt=-16 * k,
                la=(140 * k, 12), ra=(154 * k, 8), ll=(8, -8), rl=(-8, -8))

def P_kneel(x, face=1, k=1.0):
    return pose((x, HIP_Y + 30 * k), face=face, lean=22 * k, tilt=8 * k,
                la=(44, 40), ra=(66 + 14 * k, 20), ll=(58 * k, -86 * k), rl=(-16, -30 * k))

def P_crouch(x, face=1, k=1.0):
    """Anticipation. Nothing in animation launches from a neutral stance."""
    return pose((x, HIP_Y + 26 * k), face=face, lean=14 * k, tilt=6 * k,
                la=(-34 * k, 8), ra=(-40 * k, 6),
                ll=(26 * k, -62 * k), rl=(-22 * k, -58 * k))

def P_squash(x, face=1, k=1.0):
    """The frame after an impact — knees absorb, torso compresses."""
    return pose((x, HIP_Y + 18 * k), face=face, lean=6 * k,
                la=(30 * k, 18), ra=(-28 * k, -16),
                ll=(20 * k, -46 * k), rl=(-18 * k, -44 * k), bre=1.0 - 0.05 * k)

def P_nod(x, face=1, k=0.0):
    return pose((x, HIP_Y), face=face, tilt=16 * k, lean=3 * k)

# ── blocking: an ordered segment list; every turn lands on a held pose ───────
def walk(t, t0, t1, x0, x1, face, P=P_walk):
    u = seg(t, t0, t1)
    n = max(1, round(abs(x1 - x0) / STRIDE))
    p = P(lerp(x0, x1, trapz(u)), (u * n) % 1.0, face)
    # A walk cycle ends mid-stride with the knees bent; whatever comes next almost
    # always starts from a stand. Settle into one over the last stride so the
    # hand-off is not a 50-unit snap. (P_carry already ends on its own hold pose.)
    if P is P_walk and u > 0.86:
        p = blend(p, P_stand(x1, face), ease((u - 0.86) / 0.14))
    return p

def fig_x(t):
    return figure_pose(t)["hip"][0]

def cycles(t, t0, span, n):
    """n complete out-and-back cycles over `span`, then still. Ending ON zero
    matters: cutting a gesture off mid-swing is a one-frame pop, and the lint
    reports it as one."""
    u = seg(t, t0, t0 + span)
    return 0.0 if u >= 1.0 else math.sin(math.pi * ((u * n) % 1.0))

def tap_k(t):
    """Two taps on the empty slot, then still — the beat before the crack."""
    return cycles(t, B["tap"], 1.5, 2)

def nod_k(t):
    return cycles(t, B["watch"] + 0.2, 1.3, 2)

def _blocking():
    """The figure's performance, as an ordered list of (start, fn) segments.
    Built through helpers rather than written flat, so the three rules that make
    it read as animation are enforced instead of remembered:

      hold(a, b, P, Q) — every action starts and ends on a settled pose. A shove
                         or a haul that begins at full extension throws a 70°
                         arm in a single drawing.
      turn(t, x, …)    — a mirror flip lands BETWEEN two held, near-symmetric
                         poses. Flip a dash or a haul and the figure looks like
                         it inverted; flip a stand and it looks like it turned.
      rest only on G*  — the gap centres. A figure standing on a glyph is two
                         silhouettes in one place and reads as neither.
    """
    S = []
    def at(t, fn):
        S.append((t, fn))

    def hold(t0, t1, pa, pb, f=ease):
        at(t0, lambda t: blend(pa, pb, f(seg(t, t0, t1))))

    def turn(t, x, old, new, d=0.22):
        at(t - d, lambda tt: P_stand(x, old))
        at(t, lambda tt: P_stand(x, new))

    # ── act one ──────────────────────────────────────────────────────────────
    at(0.0, lambda t: P_stand(G2, -1))
    hold(B["reach"], B["touch"], P_stand(G2, -1), P_reach(G2, -1), ease_out)
    at(B["touch"], lambda t: P_reach(G2, -1))
    hold(B["unreach"], B["wind"], P_reach(G2, -1), P_stand(G2, -1))
    hold(B["wind"], B["push1"], P_stand(G2, -1), P_push(G2, -1, 0.25))
    at(B["push1"], lambda t: blend(P_push(G2, -1, 0.25), P_push(G1, -1, 1.0),
                                   ease(seg(t, B["push1"], B["push_end"]))))
    hold(B["push_end"], B["push_end"] + 0.6, P_push(G1, -1, 1.0), P_stand(G1, -1))
    turn(B["pivot_r"], G1, -1, 1)                    # the second 1 lands behind it
    hold(B["cheer"] - 0.34, B["cheer"], P_stand(G1, 1), P_crouch(G1, 1))   # anticipation
    at(B["cheer"], lambda t: blend(P_crouch(G1, 1), P_cheer(G1, 1),
                                   math.sin(math.pi * seg(t, B["cheer"], B["land_j"]))))
    hold(B["land_j"], B["land_j"] + 0.16, P_crouch(G1, 1), P_squash(G1, 1))  # impact
    hold(B["land_j"] + 0.16, B["land_j"] + 0.55, P_squash(G1, 1), P_stand(G1, 1))

    # ── act two: reach right for the +, hurl it up and over the equation ─────
    hold(B["yank"], B["throw"], P_stand(G1, 1), P_reach(G1, 1), ease_out)
    hold(B["throw"], B["tossed"], P_reach(G1, 1), P_push(G1, 1, 0.6), ease_out)
    hold(B["tossed"], B["tossed"] + 0.45, P_push(G1, 1, 0.6), P_stand(G1, 1))
    hold(B["div_drop"], B["div_catch"], P_stand(G1, 1), P_reachup(G1, 1))
    hold(B["div_catch"], B["div_set"], P_reachup(G1, 1), P_kneel(G1, 1))
    hold(B["div_set"], B["div_set"] + 0.5, P_kneel(G1, 1), P_stand(G1, 1))
    at(B["walk_1"], lambda t: walk(t, B["walk_1"], B["pull1"] - 0.35, G1, G2, 1))
    hold(B["pull1"] - 0.35, B["pull1"], P_stand(G2, 1), P_reach(G2, 1), ease_out)
    hold(B["pull1"], B["toss1"], P_reach(G2, 1), P_push(G2, 1, 0.6), ease_out)
    hold(B["toss1"], B["toss1"] + 0.45, P_push(G2, 1, 0.6), P_stand(G2, 1))
    hold(B["zero_drop"], B["zero_catch"], P_stand(G2, 1), P_reachup(G2, 1))
    hold(B["zero_catch"], B["zero_set"], P_reachup(G2, 1), P_kneel(G2, 1))
    hold(B["zero_set"], B["zero_set"] + 0.5, P_kneel(G2, 1), P_stand(G2, 1))

    # ── act three ────────────────────────────────────────────────────────────
    at(B["to_slot"], lambda t: walk(t, B["to_slot"], B["tap"], G2, G4, 1))
    at(B["tap"], lambda t: blend(P_stand(G4, 1), P_reach(G4, 1), tap_k(t)))
    hold(B["peer"], B["peer"] + 1.2, P_stand(G4, 1), P_peer(G4, 1))
    hold(B["recoil"], B["flee"] - 0.35, P_peer(G4, 1), P_stand(G4, 1), ease_out)
    turn(B["flee"], G4, 1, -1)
    at(B["flee"], lambda t: walk(t, B["flee"], B["pivot_brace"] - 0.22, G4, G2, -1))
    turn(B["pivot_brace"], G2, -1, 1)
    hold(B["brace"], B["braced"], P_stand(G2, 1), P_brace(G2, 1))
    at(B["braced"], lambda t: P_brace(lerp(G2, G2 + 75,
                              ease(seg(t, B["braced"], B["lunge"])))
                              + 4.0 * math.sin(2 * math.pi * 3.1 * t), 1))
    hold(B["lunge"], B["plant"], P_brace(G2 + 75, 1), P_dash(G3, 1))
    hold(B["plant"], B["grab"] - 0.22, P_dash(G3, 1), P_stand(G3, 1))
    turn(B["grab"], G3, 1, -1)
    hold(B["grab"], B["lift"], P_stand(G3, -1), P_kneel(G3, -1))
    hold(B["lift"], B["snap"], P_kneel(G3, -1), P_lift(G3, -1), ease_out)
    at(B["snap"], lambda t: P_lift(G3, -1))

    # ── act four ─────────────────────────────────────────────────────────────
    hold(B["carry"], B["walkc"], P_lift(G3, -1), P_carry(G3, 0.0, -1))
    at(B["walkc"], lambda t: walk(t, B["walkc"], B["setdown"], G3, G1, -1, P=P_carry))
    hold(B["setdown"], B["down"], P_carry(G1, 0.0, -1), P_kneel(G1, -1))
    hold(B["down"], B["up"], P_kneel(G1, -1), P_stand(G1, -1))
    at(B["back"], lambda t: walk(t, B["back"], B["watch"] - 0.22, G1, 300, -1))
    turn(B["watch"], 300, -1, 1)
    at(B["watch"] + 0.2, lambda t: P_nod(300, 1, nod_k(t)))
    S.sort(key=lambda e: e[0])
    return S

SEGMENTS = _blocking()

def _pose_at(t):
    fn = SEGMENTS[0][1]
    for t0, f in SEGMENTS:
        if t >= t0:
            fn = f
        else:
            break
    return fn(t)

def _world_pts(p):
    s, (hx, hy) = skeleton(p), p["hip"]
    pts = [s["neck"], s["head"]] + [j for lm in s["arms"] + s["legs"] for j in lm]
    return [(hx + x, hy + y) for x, y in pts]

TWOS = 1.0 / 12.0
SINGLES_ABOVE = 26.0    # px any joint may travel between drawings before it strobes

def figure_pose(t):
    """Twos where the figure is calm, singles where it is fast.

    Holding a drawing for two frames is the Flash cadence and it is what makes
    hand-drawn animation read as drawn. But a 2.8-stride/second walk on twos is
    only four drawings per cycle — the legs scribble. So the choice is made from
    the measured motion rather than fixed: quantise to 12 fps, and drop to 24 the
    moment any joint would travel more than SINGLES_ABOVE between drawings. The
    run-length compressor makes the held frames free, so twos cost nothing."""
    q = math.floor(t / TWOS) * TWOS
    a, b = _world_pts(_pose_at(q)), _world_pts(_pose_at(min(DUR, q + TWOS)))
    far = max(max(abs(p[0] - r[0]), abs(p[1] - r[1])) for p, r in zip(a, b))
    tt = t if far > SINGLES_ABOVE else q
    return _idle(_pose_at(tt), tt, 1.0 - min(1.0, far / 20.0))

def _idle(p, t, calm):
    """A MOVING hold. On discrete twos a settled pose is one drawing held for
    seconds — a literally frozen frame, which is the single clearest tell of
    cheap animation. So a held figure breathes, shifts its weight and drifts its
    head, at an amplitude that falls to zero the moment it is actually moving.

    The breath lengthens the SPINE rather than lifting the hip: scaling the legs
    would raise the feet off the ground line."""
    if calm <= 0.02:
        return p
    w = 2 * math.pi * 0.42 * t
    o = dict(p)
    o["bre"] = p.get("bre", 1.0) * (1.0 + 0.026 * calm * math.sin(w))
    o["lean"] = p["lean"] + 1.5 * calm * math.sin(2 * math.pi * 0.13 * t + 0.7)
    o["tilt"] = p["tilt"] + 2.0 * calm * math.sin(w * 0.5 + 2.2)
    sway = 1.6 * calm * math.sin(w * 0.77 + 1.4)
    o["la"] = (p["la"][0] + sway, p["la"][1])
    o["ra"] = (p["ra"][0] - sway, p["ra"][1])
    return o

# ── glyphs: stroked paths, cap height 140, baseline y=0, centred on x=0 ─────
GLYPH = {
    "1":    [("path", {"d": "M-24-106 6-140 6 0"})],
    "plus": [("path", {"d": "M-34-70H34M0-104V-36"})],
    "eq":   [("path", {"d": "M-34-88H34M-34-52H34"})],
    "2":    [("path", {"d": "M-32-104Q-32-140 0-140 32-140 32-104 32-74-30 0H32"})],
    "div":  [("path", {"d": "M-34-70H34"}),
             ("circle", {"cx": "0", "cy": "-102", "r": "8", "fill": WHITE, "stroke": "none"}),
             ("circle", {"cx": "0", "cy": "-38", "r": "8", "fill": WHITE, "stroke": "none"})],
    "0":    [("ellipse", {"cx": "0", "cy": "-70", "rx": "30", "ry": "70"})],
}

# ── document model ──────────────────────────────────────────────────────────
class Raw:
    def __init__(self, s): self.s = s

class El:
    """`anim` maps attribute -> f(t). `xform` is a list of (kind, f(t)) rendered
    as nested groups, so animateTransform never composes with a sibling."""
    def __init__(self, tag, attrs=None, anim=None, xform=None, children=None,
                 calc="linear", fps=FPS_SMOOTH):
        self.tag, self.attrs = tag, dict(attrs or {})
        self.anim, self.xform = dict(anim or {}), list(xform or [])
        self.children, self.calc, self.fps = list(children or []), calc, fps

    def add(self, *c):
        self.children.extend(c)
        return self

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))

LINT = []

def track(fn, fps, discrete, tag):
    """Sample f(t) over the loop, record it for the lint, run-length compress.
    The loop closes because f(0) == f(DUR) by construction."""
    n = int(round(DUR * fps))
    idx = range(n) if discrete else range(n + 1)
    vals = [fn(i / fps) for i in idx]
    if len(set(vals)) <= 1:
        return None
    LINT.append((tag, fps, vals))
    times = [i / n for i in idx]
    keep = [0]
    if discrete:
        # holds until the next keyTime — keep only genuine changes
        for i in range(1, len(vals)):
            if vals[i] != vals[keep[-1]]:
                keep.append(i)
    else:
        # linear interpolates across a gap, so a run may only be collapsed when
        # it is genuinely constant on both sides
        for i in range(1, len(vals) - 1):
            if not (vals[i] == vals[i - 1] == vals[i + 1]):
                keep.append(i)
        keep.append(len(vals) - 1)
    return (";".join(vals[i] for i in keep),
            ";".join(num_t(times[i]) for i in keep))

def emit(el, out, t, path="svg"):
    if isinstance(el, Raw):
        out.append(el.s)
        return
    opens = []
    for kind, fn in el.xform:
        if t is None:
            tr = track(fn, el.fps, el.calc == "discrete", f"{path}/@{kind}")
            if tr is None:
                out.append(f'<g transform="{kind}({fn(0.0)})">')
            else:
                out.append("<g>")
                out.append(f'<animateTransform attributeName="transform" type="{kind}"'
                           f' values="{tr[0]}" keyTimes="{tr[1]}" dur="{num(DUR)}s"'
                           f' calcMode="{el.calc}" repeatCount="indefinite"/>')
        else:
            out.append(f'<g transform="{kind}({fn(t)})">')
        opens.append("</g>")

    a, smil = dict(el.attrs), []
    for k, fn in el.anim.items():
        if t is None:
            tr = track(fn, el.fps, el.calc == "discrete", f"{path}/@{k}")
            if tr is None:
                a[k] = fn(0.0)
            else:
                a.setdefault(k, fn(0.0))
                smil.append(f'<animate attributeName="{k}" values="{tr[0]}"'
                            f' keyTimes="{tr[1]}" dur="{num(DUR)}s"'
                            f' calcMode="{el.calc}" repeatCount="indefinite"/>')
        else:
            a[k] = fn(t)

    sub = []
    for i, c in enumerate(el.children):
        emit(c, sub, t, f"{path}/{el.tag}[{i}]")
    at = "".join(f' {k}="{esc(v)}"' for k, v in a.items())
    if smil or sub:
        out.append(f"<{el.tag}{at}>")
        out.extend(smil)
        out.extend(sub)
        out.append(f"</{el.tag}>")
    else:
        out.append(f"<{el.tag}{at}/>")
    out.extend(reversed(opens))

# ── choreography: props ─────────────────────────────────────────────────────
def fade(t, a, b_):  return ease(seg(t, a, b_))
def stage(t):        return fade(t, 0.0, 1.0) * (1.0 - fade(t, B["fade"], B["end"] - 0.5))
def pop_in(t, t0, d=0.5):  return ease_out(seg(t, t0, t0 + d))

def pop_scale(t, t0):
    u = seg(t, t0, t0 + 0.55)
    return 0.25 + 0.75 * back_(u) if u < 1 else 1.0

def fall(t, t0, t1, y1):
    """A prop falls in from above the frame, accelerating. Dropping props in is
    what let the fetch-walks go: nothing has to travel across the equation and
    collide with the glyphs already standing in it."""
    u = seg(t, t0, t1)
    return lerp(DROP, y1, u ** 1.6)

def bounce(t, t0, span=0.36, h=46.0):
    u = seg(t, t0, t0 + span)
    return -h * math.sin(math.pi * u) * (1 - u) if u < 1.0 else 0.0

def hurl(t, t0, t1, x0, x1, h):
    """Thrown up and over the equation, clearing the glyphs still standing in
    it, and out of frame."""
    u = ease_in(seg(t, t0, t1))
    return lerp(x0, x1, u), GROUND - h * math.sin(math.pi * u) + 30 * u

def impact(t, t0, span=0.34, amt=0.20):
    """Compress on contact, overshoot, settle."""
    u = seg(t, t0, t0 + span)
    if u <= 0.0 or u >= 1.0:
        return (1.0, 1.0)
    k = amt * math.sin(math.pi * u) * math.cos(math.pi * u * 1.7)
    return (1.0 + k, 1.0 - k)

def drop_stretch(yfn, t, k=1.0 / 1100.0, cap=0.5):
    """Stretch along the fall, proportional to measured speed. This is the only
    motion blur available — <filter> is not allowed — and it is what animators
    draw anyway."""
    v = abs(yfn(t + 1.0 / 48.0) - yfn(t)) * 48.0
    e = min(cap, v * k)
    return (1.0 / (1.0 + 0.55 * e), 1.0 + e)

def mul2(*pairs):
    sx = sy = 1.0
    for a, b in pairs:
        sx, sy = sx * a, sy * b
    return (sx, sy)

def suck(t, x):
    """How far a glyph at world x is dragged toward the slot while the void is
    open. Zero before it opens and after it snaps shut."""
    k = ease(seg(t, B["open_"], B["lunge"])) * (1.0 - ease_out(seg(t, B["lunge"], B["snap"])))
    return (SR - x) * 0.40 * k

# the first 1: starts in the middle, is shoved left to make room, is dragged by
# the void, then hops right into S2 when the 0 comes to take its place
def g1_x(t):
    x = lerp(SOP, S1, ease(seg(t, B["push1"], B["push_end"]))) + suck(t, S1)
    return lerp(x, S2, ease(seg(t, B["hop"], B["land"])))

def g1_y(t):
    return GROUND - 190.0 * math.sin(math.pi * seg(t, B["hop"], B["land"]))

def g1_rot(t):
    """A tilt, not a spin: a rotating 1 stops looking like a 1."""
    return -12.0 * math.sin(math.pi * seg(t, B["hop"], B["land"]))

def g1_scale(t):
    w = 1.0
    if B["reach"] <= t < B["wind"] + 0.4:
        u = seg(t, B["touch"] - 0.3, B["wind"] + 0.4)
        w = 1.0 + 0.07 * math.sin(2 * math.pi * 4.4 * (t - B["touch"] + 0.3)) * (1 - u)
    return mul2((w, w), impact(t, B["land"], 0.34, 0.18))

def g1_op(t):  return fade(t, B["one_in"], B["one_in"] + 1.0)

# the second 1: falls in, bounces, is later ripped out and hurled up and right
def g2_x(t):  return hurl(t, B["pull1"], B["toss1"] + 0.9, S2, 1820.0, 300.0)[0]

def g2_y(t):
    if t < B["pull1"]:
        return fall(t, B["two_drop"], B["two_land"], GROUND) + bounce(t, B["two_land"])
    return hurl(t, B["pull1"], B["toss1"] + 0.9, S2, 1820.0, 300.0)[1]

def g2_rot(t):  return 300.0 * ease_in(seg(t, B["pull1"], B["toss1"] + 0.9))

def g2_sc(t):
    return mul2(drop_stretch(g2_y, t), impact(t, B["two_land"], 0.40, 0.26))

def g2_op(t):
    return fade(t, B["two_drop"], B["two_drop"] + 0.2) * \
        (1.0 - fade(t, B["toss1"] + 0.3, B["toss1"] + 0.9))

# the +: arrives on its own once the gap exists, then is hurled up and over
def plus_x(t):  return hurl(t, B["throw"], B["tossed"] + 1.1, SOP, 1820.0, 330.0)[0]
def plus_y(t):  return hurl(t, B["throw"], B["tossed"] + 1.1, SOP, 1820.0, 330.0)[1]
def plus_rot(t):  return 430.0 * ease_in(seg(t, B["throw"], B["tossed"] + 1.1))
def plus_op(t):
    return pop_in(t, B["plus"]) * (1.0 - fade(t, B["tossed"] + 0.4, B["tossed"] + 1.1))

# the ÷ and the 0 both FALL into the figure's raised hands and are then planted
def caught_x(t, t_drop, t_catch, t_set, gap, slot):
    hand = gap + 25.0
    return lerp(hand, slot, ease(seg(t, t_catch, t_set)))

def caught_y(t, t_drop, t_catch, t_set):
    y = fall(t, t_drop, t_catch, GROUND - CATCH)
    return lerp(y, GROUND, ease(seg(t, t_catch, t_set)))

def div_x(t):   return caught_x(t, B["div_drop"], B["div_catch"], B["div_set"], G1, SOP)
def div_y(t):   return caught_y(t, B["div_drop"], B["div_catch"], B["div_set"])
def div_sc(t):
    return mul2(drop_stretch(div_y, t), impact(t, B["div_catch"], 0.26, 0.12),
                impact(t, B["div_set"], 0.30, 0.15))

def div_op(t):  return fade(t, B["div_drop"], B["div_drop"] + 0.2)

def zero_x(t):
    x = caught_x(t, B["zero_drop"], B["zero_catch"], B["zero_set"], G2, S2) + suck(t, S2)
    x = lerp(x, G3 - 7.0, ease_out(seg(t, B["lift"], B["snap"])))   # held aloft
    x = lerp(x, fig_x(t) - 96.0, ease(seg(t, B["snap"], B["walkc"])))  # rides in the hands
    return lerp(x, S1, ease(seg(t, B["setdown"], B["down"])))

def zero_y(t):
    y = caught_y(t, B["zero_drop"], B["zero_catch"], B["zero_set"])
    up = ease_out(seg(t, B["lift"], B["snap"])) * (1.0 - ease(seg(t, B["setdown"], B["down"])))
    return lerp(y, GROUND - CARRY, up)

def zero_rot(t):
    return 18.0 * math.sin(math.pi * seg(t, B["lift"], B["down"]))

def zero_sc(t):
    return mul2(drop_stretch(zero_y, t), impact(t, B["zero_catch"], 0.26, 0.12),
                impact(t, B["zero_set"], 0.30, 0.15), impact(t, B["down"], 0.32, 0.13))

def zero_op(t):  return fade(t, B["zero_drop"], B["zero_drop"] + 0.2)

def zero_blue(t):
    """The 0 catches the void's colour while it is the divisor, and only then."""
    return fade(t, B["crack"], B["open_"]) * (1.0 - fade(t, B["lift"], B["snap"]))

def eq_x(t):  return SEQ + suck(t, SEQ)

# what appears in the result slot: a 2, then a 1, then — after the swap — a 0
def res2_op(t):
    return pop_in(t, B["pop"], 0.4) * (1.0 - fade(t, B["yank"], B["tossed"]))

def res1_op(t):
    return pop_in(t, B["div_set"] + 0.3, 0.45) * (1.0 - fade(t, B["pull1"], B["pull1"] + 0.5))

def res0_op(t):  return pop_in(t, B["zres"], 0.5)

def halo(t):
    return 0.9 * max(math.sin(math.pi * seg(t, B["pop"] - 0.1, B["pop"] + 0.9)),
                     math.sin(math.pi * seg(t, B["div_set"] + 0.2, B["div_set"] + 1.1)),
                     math.sin(math.pi * seg(t, B["zres"] - 0.1, B["zres"] + 1.3)))

def slot_op(t):
    """Visible from the moment the 2 is torn away until an answer exists again.
    This dashed empty box, and how long it stays empty, IS the film."""
    v = pop_in(t, B["tossed"], 0.6) * (1.0 - fade(t, B["div_set"] + 0.15, B["div_set"] + 0.6))
    v = max(v, pop_in(t, B["pull1"] + 0.2, 0.5) * (1.0 - fade(t, B["zres"] - 0.5, B["zres"])))
    if B["tap"] <= t < B["crack"]:
        v = min(1.0, v + 0.4 * abs(math.sin(2 * math.pi * 1.2 * (t - B["tap"]))))
    return v

# ── the void ────────────────────────────────────────────────────────────────
def void_r(t):
    r = 10.0 + 52.0 * ease_out(seg(t, B["crack"], B["open_"]))
    r += 250.0 * ease(seg(t, B["open_"], B["braced"] + 1.6))
    return max(0.0, r * (1.0 - ease_in(seg(t, B["lift"], B["snap"]))))

def void_op(t):
    o = 0.55 * ease_out(seg(t, B["crack"], B["open_"]))
    o += 0.30 * ease(seg(t, B["open_"], B["braced"] + 1.0))
    o *= 1.0 - ease_in(seg(t, B["lift"], B["snap"]))
    return max(0.0, min(1.0, o * (1.0 + 0.06 * math.sin(2 * math.pi * 2.3 * t))))

def _cracks():
    """Six fractures radiating from the empty slot: each walks outward along its
    own bearing with small perpendicular jogs. Built from SR/GROUND so they can
    never drift away from the thing they are cracking out of."""
    out = []
    for ang, ln in [(155, 205), (200, 235), (248, 180), (292, 195), (340, 165), (25, 210)]:
        a = math.radians(ang)
        dx, dy = math.cos(a), math.sin(a)
        px, py = -dy, dx
        x, y = SR, GROUND - 70
        d = f"M{num(x)} {num(y)}"
        for frac, jog in ((0.44, 0.09), (0.30, -0.15), (0.26, 0.07)):
            nx, ny = x + (dx * frac + px * jog) * ln, y + (dy * frac + py * jog) * ln
            d += "l" + _j(round(nx, 1) - round(x, 1), round(ny, 1) - round(y, 1))
            x, y = nx, ny
        out.append(d)
    return out

CRACKS = _cracks()

def crack_off(t, i):
    return 100.0 * (1.0 - ease_out(seg(t, B["crack"] + 0.07 * i,
                                       B["crack"] + 0.9 + 0.08 * i)))

def crack_op(t):
    return fade(t, B["crack"], B["crack"] + 0.3) * \
        (1.0 - fade(t, B["lift"] - 0.2, B["snap"]))

# ── the camera ──────────────────────────────────────────────────────────────
def cam_scale(t):
    """Framing, not just movement. At the old scale the content was 24% of the
    frame height with dead space above and below; a Becker frame runs nearer 35%,
    which is what makes a stick figure feel like a character rather than a mark."""
    s = ramp(t, 0.0, B["touch"], 1.75, 1.60)                       # in close on the 1
    s = lerp(s, 1.42, ease(seg(t, B["plus"], B["cheer"])))         # reveal the whole line
    s = lerp(s, 1.45, ease(seg(t, B["yank"], B["div_drop"])))
    s = lerp(s, 2.00, ease(seg(t, B["tap"], B["crack"] + 1.0)))    # push in on the empty slot
    s = lerp(s, 1.05, ease(seg(t, B["open_"], B["braced"] + 1.5)))  # yank out for the void
    s = lerp(s, 1.45, ease(seg(t, B["snap"], B["walkc"] + 1.4)))
    s = lerp(s, 1.30, ease(seg(t, B["setdown"], B["watch"] + 1.0)))
    return s

def cam_center(t):
    x = ramp(t, 0.0, B["touch"], 560.0, 600.0)
    x = lerp(x, 520.0, ease(seg(t, B["push1"], B["push_end"])))
    x = lerp(x, 800.0, ease(seg(t, B["pivot_r"], B["cheer"])))      # the whole equation
    # Act two holds on 800 with the whole line in frame: every edit the figure
    # makes has to be visible AT THE SAME TIME as the slot that answers it.
    x = lerp(x, 1170.0, ease(seg(t, B["tap"], B["crack"])))
    x = lerp(x, 1000.0, ease(seg(t, B["open_"], B["braced"])))
    x = lerp(x, 740.0, ease(seg(t, B["snap"], B["walkc"] + 1.4)))
    y = 530.0
    y = lerp(y, 555.0, ease(seg(t, B["tap"], B["crack"])))
    y = lerp(y, 500.0, ease(seg(t, B["open_"], B["braced"])))
    q = 1.0 - ease(seg(t, B["crack"] + 0.8, B["open_"] + 0.6))
    if B["crack"] <= t < B["open_"] + 0.6:                         # the quake
        x += 11.0 * q * math.sin(2 * math.pi * 7.3 * t)
        y += 8.0 * q * math.sin(2 * math.pi * 9.1 * t + 1.1)
    if B["snap"] <= t < B["snap"] + 0.5:                           # the collapse hit
        k = 1.0 - seg(t, B["snap"], B["snap"] + 0.5)
        x += 16.0 * k * math.sin(2 * math.pi * 11.0 * t)
    return x, y

def cam_translate(t):
    s = cam_scale(t)
    qx, qy = cam_center(t)
    return f"{num(CX / s - qx)} {num(CY / s - qy)}"

# ── assembly ────────────────────────────────────────────────────────────────
def mix(c1, c2, u):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b_ = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(lerp(a[i], b_[i], u)) for i in range(3))

def grad(gid, stops):
    g = El("radialGradient", {"id": gid, "cx": "0.5", "cy": "0.5", "r": "0.5"})
    for off, col, op in stops:
        g.add(El("stop", {"offset": off, "stop-color": col, "stop-opacity": op}))
    return g

def _sc(fn, t):
    """A scale track may return a scalar or an (sx, sy) pair — squash needs the
    pair, and it deforms about the glyph's BASELINE, which is where a landing
    actually compresses from."""
    if fn is None:
        return "1"
    v = fn(t)
    return f"{num(v[0])} {num(v[1])}" if isinstance(v, tuple) else num(v)

def prop(name, x, y=None, rot=None, sc=None, op=None, col=None):
    inner = El("g", {"class": "gl"})
    if col:
        inner.anim["stroke"] = col
    for tag, at in GLYPH[name]:
        inner.add(El(tag, at))
    g = El("g", {}, xform=[
        ("translate", lambda t: f"{num(x(t))} {num((y or (lambda _: GROUND))(t))}"),
        ("rotate", lambda t: num((rot or (lambda _: 0.0))(t))),
        ("scale", lambda t: _sc(sc, t)),
    ], children=[inner])
    return El("g", {}, anim={"opacity": lambda t: num(op(t))}, children=[g]) if op else g

def figure_el():
    def part(get):
        return lambda t: get(skeleton(figure_pose(t)))

    def s2(a, b): return poly(a, b)
    def s3(a, b, c): return poly(a, b, c)

    kw = dict(calc="discrete", fps=FPS_FIG)
    g = El("g", {"class": "fig"}, xform=[("translate", lambda t: "%s %s" % (
        num(figure_pose(t)["hip"][0]), num(figure_pose(t)["hip"][1])))], **kw)
    g.add(El("path", {}, anim={"d": part(lambda s: s2((0.0, 0.0), s["neck"]))}, **kw))
    for i in (0, 1):
        g.add(El("path", {}, anim={"d": (lambda i: part(
            lambda s: s3(s["neck"], s["arms"][i][0], s["arms"][i][1])))(i)}, **kw))
        g.add(El("path", {}, anim={"d": (lambda i: part(
            lambda s: s3((0.0, 0.0), s["legs"][i][0], s["legs"][i][1])))(i)}, **kw))
    g.add(El("circle", {"r": num(HEAD_R)}, anim={
        "cx": part(lambda s: num(s["head"][0])),
        "cy": part(lambda s: num(s["head"][1]))}, **kw))
    return g

def build():
    root = El("svg", {
        "xmlns": "http://www.w3.org/2000/svg", "viewBox": f"0 0 {W} {H}",
        "width": str(W), "height": str(H), "role": "img",
        "aria-label": "A stick figure builds one plus one equals two, swaps the plus for "
                      "a division sign, then divides by zero. The answer slot stays empty. "
                      "It puts the zero on the other side instead: zero divided by one "
                      "equals zero.",
    })
    root.add(El("title").add(Raw("Undefined")),
             El("desc").add(Raw(
                 "Fifty seconds, looping. A gold figure assembles 1 + 1 = 2 from white "
                 "glyphs, tears out the plus, drags in a division sign, then swaps the "
                 "second 1 for a 0. The result slot never fills, because division by zero "
                 "is undefined rather than infinite. Blue light escapes the empty slot "
                 "until the figure hauls the 0 back out and sets it down on the other side "
                 "of the division sign, where 0 divided by 1 is simply 0.")))

    defs = El("defs")
    defs.add(grad("voidg", [("0", BLUE, "0.95"), ("0.42", BLUE, "0.44"),
                            ("0.76", BLUE, "0.11"), ("1", BLUE, "0")]))
    defs.add(grad("popg", [("0", WHITE, "0.8"), ("0.5", WHITE, "0.2"), ("1", WHITE, "0")]))
    defs.add(grad("vign", [("0.42", "#000000", "0"), ("0.76", "#000000", "0.28"),
                           ("1", "#000000", "0.7")]))
    root.add(defs)

    root.add(El("style").add(Raw(
        ".gl{fill:none;stroke:%s;stroke-width:9;stroke-linecap:round;stroke-linejoin:round;"
        "vector-effect:non-scaling-stroke}"
        ".fig{fill:none;stroke:%s;stroke-width:8;stroke-linecap:round;stroke-linejoin:round;"
        "vector-effect:non-scaling-stroke}"
        ".hair{fill:none;stroke:%s;stroke-width:1.5;vector-effect:non-scaling-stroke}"
        ".crk{fill:none;stroke:%s;stroke-width:2.5;stroke-linecap:round;"
        "vector-effect:non-scaling-stroke}" % (WHITE, GOLD, WHITE, BLUE))))

    root.add(El("rect", {"x": "0", "y": "0", "width": str(W), "height": str(H), "fill": BG}))

    world = El("g")
    cam = El("g", {}, xform=[("scale", lambda t: num(cam_scale(t)))], children=[
        El("g", {}, xform=[("translate", cam_translate)], children=[world])])
    # one opacity for the whole stage: black at t=0 and t=DUR, so the loop is seamless
    root.add(El("g", {}, anim={"opacity": lambda t: num(stage(t))}, children=[cam]))

    world.add(El("g", {"class": "hair"}, anim={"opacity": lambda t: num(
        0.10 + 0.05 * math.sin(2 * math.pi * 0.08 * t))}, children=[
        El("line", {"x1": "-600", "y1": num(GROUND), "x2": "2200", "y2": num(GROUND)})]))

    world.add(El("circle", {"cx": num(SR), "cy": num(GROUND - 70), "fill": "url(#voidg)",
                            "mix-blend-mode": "screen"},
                anim={"r": lambda t: num(void_r(t)), "opacity": lambda t: num(void_op(t))}))

    cr = El("g", {"class": "crk"}, anim={"opacity": lambda t: num(crack_op(t))})
    for i, d in enumerate(CRACKS):
        cr.add(El("path", {"d": d, "pathLength": "100", "stroke-dasharray": "100"},
                  anim={"stroke-dashoffset": (lambda i: lambda t: num(crack_off(t, i)))(i)}))
    world.add(cr)

    world.add(prop("1", g1_x, g1_y, g1_rot, g1_scale, op=g1_op))
    world.add(prop("1", g2_x, g2_y, g2_rot, g2_sc, op=g2_op))
    world.add(prop("plus", plus_x, plus_y, plus_rot, op=plus_op))
    world.add(prop("div", div_x, div_y, sc=div_sc, op=div_op))
    world.add(prop("0", zero_x, zero_y, zero_rot, zero_sc, op=zero_op,
                   col=lambda t: mix(WHITE, BLUE, zero_blue(t))))
    world.add(prop("eq", eq_x, op=lambda t: pop_in(t, B["eq"])))

    world.add(El("g", {}, anim={"opacity": lambda t: num(halo(t))}, children=[
        El("circle", {"cx": num(SR), "cy": num(GROUND - 70), "r": "160",
                      "fill": "url(#popg)"})]))
    world.add(prop("2", lambda t: SR, sc=lambda t: pop_scale(t, B["pop"]), op=res2_op))
    world.add(prop("1", lambda t: SR, sc=lambda t: pop_scale(t, B["div_set"] + 0.3), op=res1_op))
    world.add(prop("0", lambda t: SR, sc=lambda t: pop_scale(t, B["zres"]), op=res0_op))

    world.add(El("g", {}, anim={"opacity": lambda t: num(slot_op(t))}, children=[
        El("rect", {"x": num(SR - 40), "y": num(GROUND - 144), "width": "80",
                    "height": "144", "rx": "8", "class": "hair",
                    "stroke-dasharray": "9 11", "stroke-width": "2"})]))

    world.add(figure_el())
    root.add(El("rect", {"x": "0", "y": "0", "width": str(W), "height": str(H),
                         "fill": "url(#vign)"}))
    return root

def serialise(t=None):
    out = []
    emit(build(), out, t)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + "".join(out) + "\n"

# ── continuity lint: catch teleports and pops a contact sheet would hide ────
NUMS = re.compile(r"-?\d+(?:\.\d+)?")

def lint():
    worst = []
    for tag, fps, vals in LINT:
        if not NUMS.search(vals[0]):
            continue
        pk, pi = 0.0, 0
        for i in range(1, len(vals)):
            a = [float(x) for x in NUMS.findall(vals[i - 1])]
            b_ = [float(x) for x in NUMS.findall(vals[i])]
            if len(a) != len(b_):
                pk, pi = 9e9, i
                break
            d = max((abs(x - y) for x, y in zip(a, b_)), default=0.0)
            if d > pk:
                pk, pi = d, i
        worst.append((pk, tag.split("/")[-1], pi / fps, tag))
    worst.sort(reverse=True)
    print("  worst per-frame jumps (units/frame) — a teleport or a pop shows up here:")
    for k, short, at, tag in worst[:9]:
        print(f"    {k:8.1f}  t={at:5.2f}s  {short:16s} {tag[-42:]}")

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    svg = serialise(None)
    open(os.path.join(here, "scene.svg"), "w").write(svg)
    print(f"scene.svg  {len(svg):,} bytes  {DUR:g}s loop  {len(LINT)} animated tracks")
    lint()
    if len(sys.argv) > 1 and sys.argv[1] == "frames":
        d = os.path.join(here, "frames")
        os.makedirs(d, exist_ok=True)
        for old in os.listdir(d):
            os.remove(os.path.join(d, old))
        times = [float(x) for x in sys.argv[2:]] or [i * 2.0 for i in range(25)]
        for t in times:
            open(os.path.join(d, f"f{t:06.2f}.svg"), "w").write(serialise(t))
        print(f"frames/    {len(times)} stills")

if __name__ == "__main__":
    main()
