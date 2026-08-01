/**
 * ARTA — the rig and the brain. No React, no DOM, no timers: pure functions and
 * one small state machine, so the same character drives the landing page, a
 * sign-up flow, an empty state, and later a game loop.
 *
 * It is deliberately the SAME rig as work 9319 ("Undefined"), the published
 * scene: identical proportions, identical joint convention, identical cadence
 * rules. The film is Arta acting; this is Arta improvising. If the two ever
 * diverge we have two mascots, which is none.
 *
 * WHO ARTA IS
 *   A stick figure with no face. That is a constraint, not an omission — with no
 *   expression to lean on, everything has to be said with posture and timing,
 *   which is why this file is mostly about weight and delay rather than shapes.
 *   Sagittarius: curious, truth-seeking, adventurous. The archer, so the
 *   signature gesture is AIMING — Arta points at the thing that matters. That
 *   gives the mascot a job (it directs attention) instead of a decoration.
 *
 * THE THREE LAWS, which keep a companion from becoming Clippy
 *   1. Arta never blocks. It does not cover content, never opens a modal, never
 *      demands a dismissal.
 *   2. Arta reacts, it does not interrupt. It answers what you do; it does not
 *      start conversations.
 *   3. Arta goes still when you are working. Typing, reading, scrolling fast —
 *      it settles. Presence is not the same as motion.
 *
 * CADENCE — smooth, deliberately UNLIKE the film
 *   The published scene holds each drawing for two frames, which is the
 *   hand-drawn cadence. Here the brief is the opposite: as smooth as the display
 *   can manage. So the sim is integrated at the real frame interval and every
 *   frame is painted — 60 Hz on a normal panel, 120 on a ProMotion one, with no
 *   fixed internal rate to beat against the refresh and no held drawings.
 *
 *   Everything that moves is therefore expressed as a RATE PER SECOND and
 *   integrated with dt, never as a per-tick delta. Exponential smoothing
 *   (1 - e^(-k·dt)) is used for every ease because it is frame-rate independent:
 *   the same motion at 60 and at 144, and correct again after a stall.
 */

// ── geometry: identical to the published scene ──────────────────────────────
export const RIG = {
  SPINE: 70, NECK: 24, HEAD_R: 20,
  THIGH: 52, SHIN: 52, UARM: 34, LARM: 32,
  /** hip height above the ground when standing */
  HIP: 104,
  /** crown to sole */
  HEIGHT: 218,
} as const;

export type XY = { x: number; y: number };

/**
 * Which way Arta faces, as a CONTINUOUS value in [-1, 1] rather than a pair of
 * states. Turning is implemented by negating every joint angle, so a boolean
 * flip moves a foot ~43 CSS px in a single frame — by a wide margin the largest
 * gradient in the whole system, and one no amount of blending can soften
 * because it is discrete. Easing the multiplier through zero instead gives a
 * real turn: the figure narrows to its own profile, passes through edge-on, and
 * opens out the other way, which is what a 2D character does when it turns.
 */
export type Face = number;

/**
 * Joint angles in degrees. 0 is straight down, positive rotates toward +x.
 * `face = -1` mirrors the whole figure by negating every angle — the only thing
 * a faceless character needs in order to turn round.
 */
export type Pose = {
  x: number;          // hip, world
  y: number;          // hip, world (ground - HIP when standing)
  lean: number;
  tilt: number;
  face: Face;
  la: [number, number];   // left arm  [shoulder, elbow]
  ra: [number, number];   // right arm
  ll: [number, number];   // left leg  [hip, knee]
  rl: [number, number];   // right leg
  sq: number;         // leg scale — a crouch shortens the stance
  bre: number;        // spine scale — the breath, which must NOT lift the feet
};

/**
 * SAFE MOTION — the hard ceiling on how fast anything may move.
 *
 * Two limits, because they bind at different frame rates and both matter:
 *
 *   MAX_PX_PER_FRAME guards against STROBING. An un-blurred line that travels
 *   much more than about twice its own stroke width between frames stops
 *   reading as movement and starts reading as a sequence of separate positions.
 *   This is the limit that binds when the frame rate is low.
 *
 *   MAX_PX_PER_SEC guards against being too fast to follow at all, which is the
 *   comfort and vestibular concern rather than the legibility one. This is the
 *   limit that binds at 120 Hz, where a per-frame budget alone would permit
 *   twice the real-world speed.
 *
 * The effective budget each frame is min(MAX_PX_PER_SEC · dt, MAX_PX_PER_FRAME),
 * measured in CSS pixels on the drawn point that moved furthest — so it covers
 * root motion, limb swing and turning together, and cannot be defeated by
 * adding a new gesture.
 */
export const SAFE = {
  MAX_PX_PER_FRAME: 12,
  MAX_PX_PER_SEC: 640,
  /** Nothing may oscillate in opacity or visibility faster than this. WCAG 2.3.1
   *  draws the seizure line at 3 Hz; the platform's calm rule is stricter, and
   *  a mascot has no reason to go near either. */
  MAX_FLASH_HZ: 2,
} as const;

const P = (o: Partial<Pose> = {}): Pose => ({
  x: 0, y: 0, lean: 0, tilt: 0, face: 1,
  la: [14, 15], ra: [-14, -15], ll: [7, -8], rl: [-7, -8], sq: 1, bre: 1, ...o,
});

const rad = (d: number) => (d * Math.PI) / 180;
const lerp = (a: number, b: number, u: number) => a + (b - a) * u;
const clamp = (v: number, lo: number, hi: number) => (v < lo ? lo : v > hi ? hi : v);
const ease = (u: number) => u * u * (3 - 2 * u);

function limb(rx: number, ry: number, a1: number, a2: number, l1: number, l2: number) {
  const r1 = rad(a1);
  const jx = rx + l1 * Math.sin(r1), jy = ry + l1 * Math.cos(r1);
  const r2 = rad(a1 + a2);
  return { jx, jy, ex: jx + l2 * Math.sin(r2), ey: jy + l2 * Math.cos(r2) };
}

export type Skeleton = {
  torso: string; armL: string; legL: string; armR: string; legR: string;
  head: { cx: number; cy: number; r: number };
  /** where the pointing hand ended up, in world coords — the arrow starts here */
  hand: XY;
};

const n1 = (v: number) => (Math.round(v * 10) / 10).toString();
const seg = (a: number, b: number, c: number, d: number, e?: number, f?: number) =>
  e === undefined ? `M${n1(a)} ${n1(b)}L${n1(c)} ${n1(d)}`
                  : `M${n1(a)} ${n1(b)}L${n1(c)} ${n1(d)}L${n1(e)} ${n1(f!)}`;

/** Resolve a pose into drawable geometry, in WORLD coordinates. */
export function skeleton(p: Pose): Skeleton {
  const f = p.face;
  const hx = p.x, hy = p.y;
  const ln = rad(p.lean * f);
  const nx = hx + RIG.SPINE * p.bre * Math.sin(ln);
  const ny = hy - RIG.SPINE * p.bre * Math.cos(ln) * p.sq;
  const hr = rad((p.lean + p.tilt) * f);
  const a0 = limb(nx, ny, p.la[0] * f, p.la[1] * f, RIG.UARM, RIG.LARM);
  const a1 = limb(nx, ny, p.ra[0] * f, p.ra[1] * f, RIG.UARM, RIG.LARM);
  const l0 = limb(hx, hy, p.ll[0] * f, p.ll[1] * f, RIG.THIGH * p.sq, RIG.SHIN * p.sq);
  const l1 = limb(hx, hy, p.rl[0] * f, p.rl[1] * f, RIG.THIGH * p.sq, RIG.SHIN * p.sq);
  return {
    torso: seg(hx, hy, nx, ny),
    armL: seg(nx, ny, a0.jx, a0.jy, a0.ex, a0.ey),
    legL: seg(hx, hy, l0.jx, l0.jy, l0.ex, l0.ey),
    armR: seg(nx, ny, a1.jx, a1.jy, a1.ex, a1.ey),
    legR: seg(hx, hy, l1.jx, l1.jy, l1.ex, l1.ey),
    head: { cx: nx + RIG.NECK * Math.sin(hr), cy: ny - RIG.NECK * Math.cos(hr), r: RIG.HEAD_R },
    hand: { x: a1.ex, y: a1.ey },
  };
}

// ── the pose library ────────────────────────────────────────────────────────
// Every entry is a still. Motion comes from the brain blending between them, so
// a new gesture is one function here and one line in the state machine.

export const stand = (): Pose => P();

export const walk = (ph: number): Pose => {
  const th = 2 * Math.PI * ph, s = Math.sin(th), c = Math.cos(th);
  return P({
    y: -2 + 3 * Math.abs(c), lean: 7,
    la: [-20 * s, 16], ra: [20 * s, 16],
    ll: [26 * s, -16 - 16 * Math.max(0, c)],
    rl: [-26 * s, -16 - 16 * Math.max(0, -c)],
  });
};

/**
 * The signature. `deg` is the ABSOLUTE aim angle: 0 down, 90 toward +x.
 *
 * The elbow bends only when it has to. Perpendicular distance from the head's
 * centre to an arm leaving the neck is 24·sin(θ), which DECREASES as the arm
 * rises — so a straight arm aimed near vertical is drawn through the skull, and
 * no shoulder angle above ~116° clears a r20 head sitting 24 above the neck.
 * (This never showed on desktop, where the target is always off to one side. On
 * a phone the call to action sits directly above Arta and the arm went straight
 * through its head.)
 *
 * So: hold the shoulder outside the head's disc and put the remainder in the
 * elbow. The FOREARM still aims at exactly `deg`, and the forearm is the part
 * that reads as pointing.
 */
const SHOULDER_MAX = 116;
export const point = (deg: number, f: Face): Pose => {
  const shoulder = clamp(deg, -SHOULDER_MAX, SHOULDER_MAX);
  return P({
    lean: 4, tilt: -6,
    la: [18, 14],
    ra: [shoulder * f, (deg - shoulder) * f],
    ll: [10, -8], rl: [-12, -8],
  });
};

/**
 * The shoulder is held OUT at 118° rather than up at 152°, and the rocking is
 * all in the elbow. The upper arm is 34 long and the head sits 24 above the
 * neck with a radius of 20, so a raised-straight-up wave draws the forearm
 * straight through the skull. Out-and-then-up clears it by ~31.
 */
export const wave = (ph: number): Pose => P({
  lean: -3, tilt: -4,
  la: [16, 12],
  ra: [118, 46 + 20 * Math.sin(2 * Math.PI * ph)],
  ll: [6, -6], rl: [-8, -6],
});

export const cheer = (): Pose => P({
  y: -85, tilt: -6,
  la: [146, 10], ra: [-146, -10], ll: [26, -46], rl: [-24, -44],
});

export const crouch = (): Pose => P({
  y: 26, lean: 14, tilt: 6,
  la: [-34, 8], ra: [-40, 6], ll: [26, -62], rl: [-22, -58],
});

/** Weight on one leg, a hand up near the head. Thinking, without a face to do it with. */
export const think = (): Pose => P({
  y: 4, lean: -6, tilt: 8,
  la: [22, 16], ra: [-132, -52], ll: [14, -10], rl: [-20, -30],
});

/** Leaning in to read something — the truth-seeker's default posture. */
export const peer = (): Pose => P({
  y: 10, lean: 30, tilt: 10,
  la: [40, 60], ra: [48, 56], ll: [24, -30], rl: [-22, -28],
});

export const shrug = (): Pose => P({
  y: 3, tilt: 4,
  la: [64, -78], ra: [-66, 76], ll: [8, -8], rl: [-10, -8],
});

/** Sitting. Arta rests when nothing has happened for a long time. */
/**
 * Winding up to throw the line. `k` runs 0 (cocked) to 1 (released), so the
 * whole action is one pose function rather than three.
 */
export const throwRope = (k: number): Pose => P({
  y: 4 - 6 * k, lean: -18 + 34 * k, tilt: -10 + 14 * k,
  la: [24 - 10 * k, 14],
  ra: [-150 + 250 * k, -20 + 20 * k],
  ll: [-14 + 30 * k, -12], rl: [18 - 30 * k, -16],
});

/**
 * Hanging from the line, mid-travel. `sway` in [-1, 1] is the pendulum phase —
 * the legs trail behind the direction of travel, which is what sells weight on
 * a rope; a figure hanging perfectly straight reads as pasted on.
 */
export const hang = (sway: number): Pose => P({
  lean: -6 * sway, tilt: -4 * sway,
  la: [168, 6], ra: [172, -6],
  ll: [26 * sway - 8, -34], rl: [26 * sway + 10, -22],
});

export const rest = (): Pose => P({
  y: 46, lean: -8, tilt: 4,
  la: [56, 66], ra: [-52, -70], ll: [74, -96], rl: [66, -104],
});

/**
 * Every drawn joint, world coords, flat — what the speed limit is measured on.
 *
 * Straight forward kinematics into a reusable array: no path strings, no regex,
 * no allocation. The first version of this built the five `d` strings and then
 * parsed the numbers back out of them with a regex, every frame, twice — which
 * is a strange thing to do in the one function that exists to keep the hot path
 * honest.
 */
const JOINTS = 22;
function joints(p: Pose, out: number[]): number[] {
  const f = p.face, hx = p.x, hy = p.y;
  const ln = rad(p.lean * f);
  const nx = hx + RIG.SPINE * p.bre * Math.sin(ln);
  const ny = hy - RIG.SPINE * p.bre * Math.cos(ln) * p.sq;
  const hr = rad((p.lean + p.tilt) * f);
  let i = 0;
  const put = (x: number, y: number) => { out[i++] = x; out[i++] = y; };
  put(hx, hy);
  put(nx, ny);
  put(nx + RIG.NECK * Math.sin(hr), ny - RIG.NECK * Math.cos(hr));
  for (const a of [p.la, p.ra]) {
    const l = limb(nx, ny, a[0] * f, a[1] * f, RIG.UARM, RIG.LARM);
    put(l.jx, l.jy); put(l.ex, l.ey);
  }
  for (const a of [p.ll, p.rl]) {
    const l = limb(hx, hy, a[0] * f, a[1] * f, RIG.THIGH * p.sq, RIG.SHIN * p.sq);
    put(l.jx, l.jy); put(l.ex, l.ey);
  }
  return out;
}

/** Largest single-joint displacement between two joint sets, in world units. */
function spread(a: number[], b: number[]): number {
  let worst = 0;
  for (let i = 0; i < JOINTS; i += 2) {
    const dx = b[i] - a[i], dy = b[i + 1] - a[i + 1];
    const d = dx * dx + dy * dy;
    if (d > worst) worst = d;      // compare squared; one sqrt at the end
  }
  return Math.sqrt(worst);
}

function blend(a: Pose, b: Pose, u: number): Pose {
  return {
    x: lerp(a.x, b.x, u), y: lerp(a.y, b.y, u),
    lean: lerp(a.lean, b.lean, u), tilt: lerp(a.tilt, b.tilt, u),
    sq: lerp(a.sq, b.sq, u), bre: lerp(a.bre, b.bre, u),
    face: lerp(a.face, b.face, u),
    la: [lerp(a.la[0], b.la[0], u), lerp(a.la[1], b.la[1], u)],
    ra: [lerp(a.ra[0], b.ra[0], u), lerp(a.ra[1], b.ra[1], u)],
    ll: [lerp(a.ll[0], b.ll[0], u), lerp(a.ll[1], b.ll[1], u)],
    rl: [lerp(a.rl[0], b.rl[0], u), lerp(a.rl[1], b.rl[1], u)],
  };
}

// ── personality ─────────────────────────────────────────────────────────────
/**
 * Sagittarius, expressed as numbers rather than adjectives. Each one is a trait
 * you can actually feel; change it and Arta reads as a different character.
 */
export const TRAITS = {
  /** curious — how hard the head tracks whatever the visitor is doing (0..1) */
  curiosity: 0.85,
  /** adventurous — seconds of stillness before Arta wanders off on its own */
  restlessness: 7,
  /** bold — gesture amplitude; a timid mascot at 0.6 reads as apologetic */
  boldness: 1.0,
  /** truth-seeking — how long it holds a point once it has aimed at something */
  conviction: 2.6,
  /** how long before it sits down and rests (seconds) */
  patience: 75,
} as const;

// ── the brain ───────────────────────────────────────────────────────────────
export type Act =
  | "idle" | "walk" | "wave" | "point" | "cheer" | "think" | "peer"
  | "shrug" | "rest" | "turn"
  // rope travel: the archer's arrow carries the line, so the grapple is the
  // signature gesture doing work rather than a second mechanic bolted on
  | "throw" | "fly" | "land" | "perch" | "fall";

export type Input = {
  /** pointer in Arta's world coords, or null when the pointer is elsewhere */
  look: XY | null;
  /** true while the visitor is scrolling or typing — law 3, Arta settles */
  busy: boolean;
  /** ground line and the horizontal bounds Arta may walk within */
  ground: number;
  minX: number;
  maxX: number;
  /** world units per CSS pixel — the safe-motion limits are stated in CSS px,
   *  because that is the space the eye actually sees */
  scale: number;
  /**
   * The floors Arta may stand on: the bottom frame of every card currently on
   * screen, in world coords. Arta is never unsupported — it stands on a real
   * edge of the page or it is falling to one, and nothing else.
   */
  floors: Floor[];
};

/** A horizontal ledge: the bottom frame of a card, from x1 to x2 at y. */
export type Floor = { x1: number; x2: number; y: number };

/**
 * The floor Arta would land on from (x, feetY): the HIGHEST ledge that spans x
 * and is at or below the feet. Falls back to the stage ground, so there is
 * always an answer — a character with nowhere to stand is the bug this exists
 * to prevent.
 */
/**
 * Snap a desired x onto a real ledge. Arta may only come to REST where a card
 * actually is: the stage floor in floorUnder() is a fallback so the maths always
 * has an answer, not a licence to stand on nothing. Without this Arta idles on
 * the invisible stage bottom wherever the page happens to have no card, which
 * is exactly the hovering this whole system exists to prevent.
 */
export function nearestStand(floors: Floor[], x: number): number | null {
  let best: number | null = null, bestD = Infinity;
  for (const f of floors) {
    if (f.x2 - f.x1 < 120) continue;                 // too narrow to stand on
    const cx = Math.min(Math.max(x, f.x1 + 60), f.x2 - 60);
    const d = Math.abs(cx - x);
    if (d < bestD) { bestD = d; best = cx; }
  }
  return best;
}

export function floorUnder(floors: Floor[], x: number, feetY: number, ground: number): number {
  let best = ground;
  for (const f of floors) {
    if (x < f.x1 - 8 || x > f.x2 + 8) continue;
    if (f.y < feetY - 6) continue;          // above the feet — cannot land upward
    if (f.y < best) best = f.y;             // nearer than the current candidate
  }
  return best;
}

export type Frame = {
  sk: Skeleton;
  act: Act;
  /** set while pointing: the arrow flies from Arta's hand to here */
  arrow: { from: XY; to: XY; age: number } | null;
  /** set while throwing or travelling: the line, hand to anchor */
  rope: { from: XY; to: XY } | null;
  /** true while airborne — the caller may want to hide the ground shadow */
  airborne: boolean;
  /** true when this tick produced a NEW drawing */
  drew: boolean;
  /** the largest distance any drawn point moved this frame, in CSS px. Must
   *  never exceed SAFE.MAX_PX_PER_FRAME; surfaced so it can be asserted. */
  peakPx: number;
};

/** Longest interval integrated in one go; anything larger is sub-stepped so a
 *  stall cannot fling Arta across the stage in a single frame. */
const MAX_STEP = 1 / 45;

export class Brain {
  private pose: Pose;
  private act: Act = "idle";
  private t = 0;             // seconds inside the current act
  private clock = 0;         // seconds since construction
  private lastDraw: Skeleton;
  private idleFor = 0;
  private phase = 0;         // walk cycle phase, accumulated over distance
  private targetX: number | null = null;
  private aim: XY | null = null;
  private aimAt = 0;
  private queue: Array<{ act: Act; at?: XY; x?: number }> = [];
  private glanceUntil = 0;
  private glanceDir = 1;
  private nextGlance = 4;
  /**
   * The INTENDED facing, always exactly 1 or -1. `pose.face` is the continuous
   * value easing toward it.
   *
   * These have to be separate. Comparing a desired side against `pose.face`
   * — a float mid-ease that is essentially never exactly ±1 — made the turn
   * re-trigger before it could finish, and the base pose carried the default
   * face of 1, so idle dragged Arta back to facing right every frame. Between
   * them Arta was pinned in the `turn` act forever, pulsing its squash at
   * 1.2 Hz. That was the shake.
   */
  private facing: Face = 1;
  private seed = 0x2f6e2b1;
  private peakPx = 0;
  private goal: XY | null = null;
  private vy = 0;                     // vertical speed while falling, world units/s
  private anchor: XY | null = null;   // where the line is hooked
  private flyFrom: XY = { x: 0, y: 0 };
  private flyDur = 1;
  private jNow: number[] = new Array(JOINTS).fill(0);
  private jNext: number[] = new Array(JOINTS).fill(0);

  /** Deterministic noise. Math.random would make Arta unreproducible, and the
   *  first thing you want when a behaviour looks wrong is to see it again. */
  private rnd(): number {
    this.seed = (this.seed * 1664525 + 1013904223) >>> 0;
    return this.seed / 0x100000000;
  }

  constructor(x: number, ground: number) {
    this.pose = P({ x, y: ground - RIG.HIP });
    this.lastDraw = skeleton(this.pose);
  }

  /**
   * THE PLANNER. Given somewhere to be, decide how to get there.
   *
   * A walk only moves along the ground, so it can never answer a scroll — which
   * is vertical. A thrown line can, and the archer already throws things, so the
   * grapple is the existing gesture doing work rather than a new mechanic.
   *
   * Short and level → walk. Far or vertical → rope. Either way Arta takes the
   * time it takes: it must never teleport, and it must never keep up perfectly.
   * Arriving late is the character, not a shortfall.
   */
  travelTo(goal: XY) {
    if (this.act === "throw" || this.act === "fly" || this.act === "land") return;
    const dx = goal.x - this.pose.x, dy = goal.y - this.pose.y;
    if (Math.abs(dy) < 70 && Math.abs(dx) < 420) {
      if (Math.abs(dx) > 40) this.command("walk", { x: goal.x });
      return;
    }
    // Hook the line ABOVE the destination, so the arrival is a descent onto it
    // rather than a slide into it.
    this.anchor = { x: goal.x, y: goal.y - 150 };
    this.goal = goal;
    this.facing = dx >= 0 ? 1 : -1;
    this.enter("throw");
  }

  /**
   * Be there, now. The reduced-motion answer to travel: with no loop running,
   * time only advances when something is commanded, so a flight of up to 3.2s
   * would strand Arta hanging on a rope forever. Someone who asked for no
   * motion wants the destination, not the journey.
   */
  placeAt(goal: XY, ground: number) {
    this.queue.length = 0;
    this.anchor = null;
    this.goal = null;
    this.act = "idle";
    this.t = 0;
    this.pose = { ...this.pose, x: goal.x, y: Math.min(goal.y, ground - RIG.HIP) };
  }

  /** Ask Arta to do something. Queued, never interrupting mid-gesture. */
  command(act: Act, opts: { at?: XY; x?: number } = {}) {
    if (this.queue.length > 3) this.queue.shift();
    this.queue.push({ act, ...opts });
  }

  get current(): Act { return this.act; }

  /**
   * Apply an act immediately, bypassing the queue and the do-not-interrupt rule.
   *
   * For the reduced-motion path only. There, time advances ONLY when something
   * is commanded, so an act can never reach its own timeout — a wave stays the
   * current act forever, `settled` stays false, and every later command sits in
   * the queue and is never seen again. There is also no gesture in flight to
   * protect when nothing is animating, so queueing buys nothing.
   */
  force(act: Act, opts: { at?: XY; x?: number } = {}) {
    this.queue.length = 0;
    this.enter(act, opts);
  }

  private enter(act: Act, opts: { at?: XY; x?: number } = {}) {
    this.act = act;
    this.t = 0;
    if (opts.at) { this.aim = opts.at; this.aimAt = this.clock; }
    if (opts.x !== undefined) this.targetX = opts.x;
  }

  /** Advance the simulation. dt in SECONDS. Returns the frame to draw.
   *  Integrated at the caller's real frame interval — no fixed internal rate, so
   *  nothing beats against the display refresh. */
  step(dt: number, input: Input): Frame {
    let left = Math.min(Math.max(dt, 0), 0.25);   // a backgrounded tab must not fast-forward
    if (left <= 0) left = MAX_STEP;               // first frame, and the still() path
    let drew = false;
    while (left > 1e-6) {
      const h = Math.min(left, MAX_STEP);
      left -= h;
      this.tick(h, input);
      drew = true;
    }
    if (drew) this.lastDraw = skeleton(this.pose);
    return {
      sk: this.lastDraw,
      act: this.act,
      rope: this.anchor && (this.act === "throw" || this.act === "fly")
        ? { from: this.lastDraw.hand, to: this.anchor } : null,
      airborne: this.act === "fly",
      arrow: this.act === "point" && this.aim
        ? { from: this.lastDraw.hand, to: this.aim, age: this.clock - this.aimAt }
        : null,
      drew,
      peakPx: this.peakPx,
    };
  }

  private tick(dt: number, input: Input): void {
    this.clock += dt;
    this.t += dt;
    const settled = this.act === "idle" || this.act === "rest" || this.act === "perch";

    // ── law 3: while the visitor works, Arta stops having ideas ─────────────
    if (input.busy && settled) this.idleFor = 0;
    else if (settled) this.idleFor += dt;
    else this.idleFor = 0;

    // ── take the next command, but only from a settled pose. Interrupting a
    //    gesture halfway is what makes a mascot look glitchy rather than alive.
    if (this.queue.length && (settled || this.t > 2.2)) {
      const q = this.queue.shift()!;
      this.enter(q.act, q);
    }

    // ── what does Arta want to be doing? ────────────────────────────────────
    let want: Pose;
    // Gravity is not optional. The support under Arta is whatever ledge is
    // beneath its feet right now — a card's bottom frame, or the stage floor.
    const feet = this.pose.y + RIG.HIP;
    const support = floorUnder(input.floors, this.pose.x, feet, input.ground);
    const base = P({ x: this.pose.x, y: support - RIG.HIP });

    // Unsupported and not on a line? Then Arta is falling, and says so.
    const onLine = this.act === "fly" || this.act === "throw" || this.act === "perch";
    if (!onLine && this.act !== "fall" && support - feet > 26) {
      this.vy = 0;
      this.enter("fall");
    }

    switch (this.act) {
      case "walk": {
        const tx = clamp(this.targetX ?? this.pose.x, input.minX, input.maxX);
        const d = tx - this.pose.x;
        const dir: Face = d >= 0 ? 1 : -1;
        if (Math.abs(d) < 4) { this.enter("idle"); want = base; break; }
        const speed = 210 * TRAITS.boldness;            // px/s
        const stepD = Math.min(Math.abs(d), speed * dt) * Math.sign(d);
        this.phase = (this.phase + Math.abs(stepD) / 110) % 1;
        want = walk(this.phase);
        want.x = this.pose.x + stepD;
        want.y = input.ground - RIG.HIP + want.y;
        this.facing = dir;
        break;
      }
      case "wave": {
        want = wave((this.t / 0.55) % 1);
        want.x = base.x; want.y = base.y;
        if (this.t > 1.7) this.enter("idle");
        break;
      }
      case "point": {
        const a = this.aim ?? { x: this.pose.x + 100, y: base.y };
        const nx = this.pose.x, ny = base.y - RIG.SPINE;
        const f: Face = a.x >= nx ? 1 : -1;
        const deg = (Math.atan2(a.x - nx, a.y - ny) * 180) / Math.PI;
        want = point(deg, f);
        want.x = base.x; want.y = base.y; this.facing = f;
        if (this.t > TRAITS.conviction) this.enter("idle");
        break;
      }
      case "cheer": {
        // crouch, launch, land — anticipation and recovery, or it reads as a shrug
        const u = this.t / 1.35;
        want = u < 0.18 ? blend(base, crouch(), ease(u / 0.18))
             : u < 0.86 ? blend(crouch(), cheer(), Math.sin(Math.PI * ((u - 0.18) / 0.68)))
             : blend(crouch(), base, ease((u - 0.86) / 0.14));
        want.x = base.x; want.y = base.y + want.y;
        if (this.t > 1.35) this.enter("idle");
        break;
      }
      case "think":
      case "peer":
      case "shrug": {
        const src = this.act === "think" ? think() : this.act === "peer" ? peer() : shrug();
        want = { ...src, x: base.x, y: base.y + src.y };
        if (this.t > (this.act === "shrug" ? 1.6 : 3.2)) this.enter("idle");
        break;
      }
      case "rest": {
        const r = rest();
        want = { ...r, x: base.x, y: base.y + r.y };
        if (!input.busy && input.look) this.enter("idle");   // it wakes when noticed
        break;
      }
      case "throw": {
        // wind up, release. The line is drawn from the hand by the renderer.
        want = throwRope(clamp(this.t / 0.42, 0, 1));
        want.x = this.pose.x; want.y = base.y;
        if (this.t >= 0.42) {
          this.flyFrom = { x: this.pose.x, y: this.pose.y };
          const a = this.anchor ?? { x: this.pose.x, y: base.y };
          const d = Math.hypot(a.x - this.flyFrom.x, a.y - this.flyFrom.y);
          // Deliberately unhurried: ~340 px/s, floor 0.55s so a short hop still
          // reads as a swing, ceiling 3.2s so a long one is not a commute.
          this.flyDur = clamp(d / 340, 0.55, 3.2);
          this.enter("fly");
        }
        break;
      }
      case "fly": {
        const a = this.anchor ?? { x: this.pose.x, y: base.y };
        const u = clamp(this.t / this.flyDur, 0, 1);
        // Ease out of the launch and into the arrival, and sag through the
        // middle: a rope is a pendulum, not a zip-line between two pins.
        const e = ease(u);
        const sag = Math.sin(Math.PI * u) * Math.min(90, this.flyDur * 40);
        want = hang(Math.cos(Math.PI * u) * 0.8);
        want.x = lerp(this.flyFrom.x, a.x, e);
        want.y = lerp(this.flyFrom.y, a.y, e) + sag;
        // Land only if the destination is near the ground. If it is high up,
        // Arta stays on the line — hanging beside the thing you are reading is
        // the whole reason a mascot owns a rope.
        if (u >= 1) this.enter((this.goal?.y ?? base.y) > base.y - 110 ? "land" : "perch");
        break;
      }
      case "land": {
        /*
         * Absorb the arrival, from WHEREVER Arta actually is.
         *
         * Two defects found by reading this against the acts that reach it. It
         * blended from `hang(0)`, but `fall` also lands here and a figure that
         * walked off a ledge was never hanging — it snapped into a hang for one
         * frame first. And it steered x toward `this.goal`, which is only set by
         * a rope trip: after a plain fall the goal was whatever an earlier
         * traversal had left there, so touchdown yanked Arta sideways across the
         * page. Both vanish once landing simply means "absorb, here".
         */
        const u = clamp(this.t / 0.4, 0, 1);
        const fy = floorUnder(input.floors, this.pose.x, this.pose.y + RIG.HIP, input.ground);
        want = blend(crouch(), P(), ease(u));
        want.x = this.pose.x;
        want.y = fy - RIG.HIP + (crouch().y * (1 - ease(u)));
        if (u >= 1) { this.anchor = null; this.goal = null; this.enter("idle"); }
        break;
      }
      case "fall": {
        // Gravity, with a terminal speed the frame-to-frame ceiling can absorb.
        this.vy = Math.min(this.vy + 2200 * dt, 900);
        const ny = this.pose.y + this.vy * dt;
        const land = floorUnder(input.floors, this.pose.x, ny + RIG.HIP, input.ground) - RIG.HIP;
        want = P({ x: this.pose.x, y: Math.min(ny, land), lean: -6, tilt: -8,
                   la: [128, 18], ra: [-124, -16], ll: [18, -26], rl: [-16, -30] });
        if (ny >= land) { this.vy = 0; this.enter("land"); }
        break;
      }
      case "perch": {
        const a = this.anchor ?? { x: this.pose.x, y: this.pose.y };
        want = hang(0.35 * Math.sin(2 * Math.PI * 0.26 * this.clock));
        want.x = a.x; want.y = a.y;
        break;
      }
      case "turn": {
        // Just the squash. The facing itself is already set, and `face` eases
        // continuously through zero on its own — the act exists to give the
        // turn a little weight, not to drive it.
        want = { ...base, sq: 1 - 0.06 * Math.sin(Math.PI * clamp(this.t / 0.3, 0, 1)) };
        if (this.t >= 0.3) this.enter("idle");
        break;
      }
      default: {
        want = base;
        // curious: with nothing to look at, Arta looks around anyway. The glance
        // has to LAST — a one-tick tilt is invisible, which is what the first
        // version of this did.
        if (this.idleFor > this.nextGlance && !input.look && !input.busy) {
          this.nextGlance = this.idleFor + 5 + 4 * this.rnd();
          this.glanceUntil = this.clock + 1.1 + 0.8 * this.rnd();
          this.glanceDir = this.rnd() < 0.5 ? -1 : 1;
        }
        if (this.clock < this.glanceUntil) {
          const u = Math.sin(Math.PI * clamp((this.glanceUntil - this.clock) / 1.1, 0, 1));
          want.tilt += 14 * this.glanceDir * u * TRAITS.curiosity;
        }
        // adventurous: stillness eventually turns into a few steps
        if (this.idleFor > TRAITS.restlessness && !input.busy) {
          const span = input.maxX - input.minX;
          const wish = input.minX + span * (0.15 + 0.7 * this.rnd());
          const to = nearestStand(input.floors, wish) ?? wish;
          this.idleFor = 0;
          if (Math.abs(to - this.pose.x) > 60) this.enter("walk", { x: to });
        }
        // Standing on the fallback floor is not standing on anything. If there
        // is a real ledge to be on, go and be on it.
        if (input.floors.length && this.idleFor > 1.2) {
          const onCard = input.floors.some(
            (f) => this.pose.x >= f.x1 && this.pose.x <= f.x2 && Math.abs(f.y - (this.pose.y + RIG.HIP)) < 30);
          const to = onCard ? null : nearestStand(input.floors, this.pose.x);
          if (to !== null && Math.abs(to - this.pose.x) > 24) { this.enter("walk", { x: to }); break; }
        }
        // and eventually it sits down
        if (this.idleFor > TRAITS.patience) this.enter("rest");
        break;
      }
    }

    // Whatever the act decided, the target facing is the one Arta intends. The
    // pose library's default of 1 must never leak through as a command to turn
    // right, which is precisely what it was doing.
    want.face = this.facing;

    // ── overlays, applied to whatever the act decided ───────────────────────
    const moving = this.act === "walk" || this.act === "cheer"
                || this.act === "fly" || this.act === "throw" || this.act === "land";

    // look at the pointer: head first, a little torso. This one behaviour does
    // more for "alive" than every gesture in the library put together.
    if (input.look && !moving) {
      const nx = this.pose.x, ny = this.pose.y - RIG.SPINE;
      const dx = input.look.x - nx, dy = input.look.y - ny;
      const a = (Math.atan2(dx, -dy) * 180) / Math.PI;      // 0 = straight up
      const k = TRAITS.curiosity * (input.busy ? 0.35 : 1);
      want.tilt += clamp(a * 0.22, -26, 26) * k * want.face;
      want.lean += clamp(a * 0.05, -6, 6) * k * want.face;
      // face the pointer, but only from a settled pose (law: flip on a hold)
      const side: Face = dx >= 0 ? 1 : -1;
      if (this.act === "idle" && side !== this.facing && Math.abs(dx) > 40) {
        this.facing = side;
        this.enter("turn");
      }
    }

    // breath and weight shift, at an amplitude that falls to zero under motion
    const calm = moving ? 0 : 1;
    if (calm > 0) {
      const w = 2 * Math.PI * 0.42 * this.clock;
      want.bre *= 1 + 0.026 * calm * Math.sin(w);
      want.lean += 1.5 * calm * Math.sin(2 * Math.PI * 0.13 * this.clock + 0.7);
      want.tilt += 2.0 * calm * Math.sin(w * 0.5 + 2.2);
      const sway = 1.6 * calm * Math.sin(w * 0.77 + 1.4);
      want.la = [want.la[0] + sway, want.la[1]];
      want.ra = [want.ra[0] - sway, want.ra[1]];
    }

    // ── ease toward it, frame-rate independently ────────────────────────────
    // 1 - e^(-k·dt) is the same motion at 60 Hz and at 144, and recovers
    // correctly from a dropped frame; a fixed per-frame fraction does neither.
    // A walk tracks its cycle almost rigidly (the cycle IS the animation); a
    // gesture arrives softly.
    const k = this.act === "walk" ? 34 : 11;
    let u = 1 - Math.exp(-k * dt);
    let next = blend(this.pose, want, u);

    // ── the speed limit ─────────────────────────────────────────────────────
    // Scale the whole blend back rather than clamping points individually: the
    // figure has to stay a figure, so it slows down as one body instead of
    // having a fast limb amputated from a slow torso. Because the measurement
    // is over every drawn point, this covers root motion, limb swing and
    // turning at once, and a gesture added later cannot escape it.
    const budgetPx = Math.min(SAFE.MAX_PX_PER_SEC * dt, SAFE.MAX_PX_PER_FRAME);
    const budget = budgetPx * input.scale;
    joints(this.pose, this.jNow);
    let moved = spread(this.jNow, joints(next, this.jNext));
    // ITERATE. `u *= budget / moved` assumes displacement is linear in the blend
    // factor, and it is not — the pose blends linearly but the skeleton resolves
    // through sin/cos, so one correction step can still overshoot. It did: the
    // rig raised its own overspeed flag at 12.6 px against a 12 px ceiling on
    // production, where the frame timing differs from the dev machine's. Each
    // pass overshoots less, so three converge comfortably, and the last one is
    // hard-capped so the invariant holds even in a pathological case.
    for (let i = 0; i < 3 && moved > budget && moved > 1e-6; i++) {
      u *= budget / moved;
      next = blend(this.pose, want, u);
      moved = spread(this.jNow, joints(next, this.jNext));
    }
    if (moved > budget && moved > 1e-6) {
      u *= (budget / moved) * 0.9;
      next = blend(this.pose, want, u);
      moved = spread(this.jNow, joints(next, this.jNext));
    }
    this.peakPx = moved / input.scale;
    this.pose = next;
  }
}

// ── the command bus ─────────────────────────────────────────────────────────
/**
 * Any component can direct Arta without prop-drilling or context:
 *     import { arta } from "artalife/rig/arta";
 *     arta.pointAt(buttonEl);   arta.cheer();   arta.peer();
 *
 * It lives here rather than beside the renderer because it is not a component;
 * exporting a non-component from a component module also disables fast refresh
 * for that module.
 */
export type Cmd = { act: Act; at?: XY; x?: number; el?: Element | null };

const listeners = new Set<(c: Cmd) => void>();
export function onArtaCommand(fn: (c: Cmd) => void): () => void {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}
const send = (c: Cmd) => listeners.forEach((f) => f(c));

export const arta = {
  /** The signature gesture: aim at a real element on the page. */
  pointAt: (el: Element | null) => send({ act: "point", el }),
  /** Go there. The planner picks walking or the rope; see Brain.travelTo. */
  travelTo: (el: Element | null) => send({ act: "throw", el }),
  walkTo: (el: Element | null) => send({ act: "walk", el }),
  wave: () => send({ act: "wave" }),
  cheer: () => send({ act: "cheer" }),
  think: () => send({ act: "think" }),
  peer: () => send({ act: "peer" }),
  shrug: () => send({ act: "shrug" }),
  idle: () => send({ act: "idle" }),
};
