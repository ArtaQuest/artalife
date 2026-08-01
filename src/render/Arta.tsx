/**
 * ARTA — the live renderer.
 *
 * Six SVG elements, one requestAnimationFrame loop, and NO React state in that
 * loop: the frame writes attributes straight onto refs. Re-rendering a
 * component tree 24 times a second to move a stick figure would be the single
 * most expensive thing on the landing page, and it is entirely avoidable.
 *
 * It stops completely when it should, which for a character that appears on
 * every page is not an optimisation but the difference between a companion and
 * a nuisance:
 *   • prefers-reduced-motion → one static pose, no rAF at all. Arta is still
 *     THERE and still expressive; it just does not move. Commands still land:
 *     the sim is fast-forwarded to the gesture's settled state and painted once,
 *     so a reduced-motion visitor sees the arrow arrive rather than an arrow
 *     frozen at the first instant of its fade-in, which is invisible.
 *   • scrolled out of view → the loop stops (IntersectionObserver).
 *   • tab hidden → the loop stops (visibilitychange).
 *   • visitor scrolling or typing → `busy`, and Arta settles (law 3).
 *
 * Arta is gold; anything Arta wields is blue (see ARTA.md §8). Today that is
 * only the arrow, but the token is the rule, not the exception.
 *
 * The command bus lives in ../lib/arta — it is not a component.
 */
import { useEffect, useRef } from "react";
import { Brain, RIG, SAFE, onArtaCommand, type Act, type Cmd, type Floor, type XY } from "../rig/arta";

/** World is 380 tall with the ground at 340 — enough headroom for the jump,
 *  whose raised hands reach about 330 above the sole. */
const WORLD_H = 380;
const GROUND = 340;

export type ArtaProps = {
  /** Rendered height in CSS pixels. Arta occupies ~57% of it. */
  height?: number;
  /**
   * Companion mode: the stage IS the whole host box (use with a fixed,
   * full-viewport, pointer-events-none wrapper). The world then spans the
   * viewport, which is what lets Arta actually travel across a page rather than
   * fly out of a 380-unit band — a rope is pointless in a box.
   */
  fill?: boolean;
  /** Arta's own height in CSS px. Only meaningful with `fill`. */
  figure?: number;
  /** Where Arta starts, as a fraction of the stage width. */
  start?: number;
  /** How much of the stage Arta may wander across, as fractions of its width.
   *  Keeps it out of the headline when the stage is full-bleed behind text. */
  range?: [number, number];
  /** Draw the hairline Arta stands on. */
  ground?: boolean;
  className?: string;
  /** Screen-reader description. Arta is decorative unless it is doing a job. */
  label?: string;
};

export default function Arta({
  height = 220, start = 0.5, range = [0.08, 0.92], ground = true, className, label,
  fill = false, figure = 132,
}: ArtaProps) {
  // Destructured to stable primitives: a `[a, b]` literal prop is a new array
  // every render, so using it directly in the dependency array would re-run the
  // whole effect — tearing down and rebuilding the loop — on every parent render.
  const [rangeLo, rangeHi] = range;

  const host = useRef<HTMLDivElement | null>(null);
  const svg = useRef<SVGSVGElement | null>(null);
  const torso = useRef<SVGPathElement | null>(null);
  const armL = useRef<SVGPathElement | null>(null);
  const legL = useRef<SVGPathElement | null>(null);
  const armR = useRef<SVGPathElement | null>(null);
  const legR = useRef<SVGPathElement | null>(null);
  const head = useRef<SVGCircleElement | null>(null);
  const arrow = useRef<SVGPathElement | null>(null);
  const rope = useRef<SVGPathElement | null>(null);

  useEffect(() => {
    const el = host.current, root = svg.current;
    if (!el || !root) return;

    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    // In companion mode the scale is set by how tall ARTA should be, and the
    // world grows to whatever the host box is. In band mode the world is a fixed
    // 380 tall and the scale is set by the band's height.
    const scale = fill ? RIG.HEIGHT / figure : WORLD_H / height;
    let vw = Math.max(240, el.clientWidth * scale);
    let wh = fill ? Math.max(320, el.clientHeight * scale) : WORLD_H;
    let gnd = fill ? wh - 52 : GROUND;
    const brain = new Brain(vw * start, gnd);

    // ── the floors ────────────────────────────────────────────────────────
    // Arta stands on the bottom frame of a real card, never on nothing. Read at
    // 4 Hz rather than per frame: these are layout reads, and the page does not
    // reflow sixty times a second. Only in companion mode — inside a band there
    // are no cards to stand on, so the band's own floor is the answer.
    let floors: Floor[] = [];
    let floorsAt = 0;
    const readFloors = (): Floor[] => {
      if (!fill) return [];
      const r = root.getBoundingClientRect();
      if (!r.width || !r.height) return [];
      const sx = vw / r.width, sy = wh / r.height;
      const out: Floor[] = [];
      for (const c of document.querySelectorAll(".rounded-card, [data-floor]")) {
        const b = c.getBoundingClientRect();
        if (b.width < 90) continue;                       // too narrow to stand on
        if (b.bottom < r.top - 40 || b.bottom > r.bottom + 40) continue;
        out.push({ x1: (b.left - r.left) * sx, x2: (b.right - r.left) * sx,
                   y: (b.bottom - r.top) * sy });
      }
      return out;
    };

    let look: XY | null = null;      // smoothed
    let rawLook: XY | null = null;   // as reported
    let busyUntil = 0;
    let lastCheck = 0;
    let raf = 0;
    let prev = 0;

    const setBox = () => {
      vw = Math.max(240, el.clientWidth * scale);
      wh = fill ? Math.max(320, el.clientHeight * scale) : WORLD_H;
      gnd = fill ? wh - 52 : GROUND;
      root.setAttribute("viewBox", `0 0 ${vw.toFixed(0)} ${wh.toFixed(0)}`);
      const g = root.querySelector("line");
      if (g) { g.setAttribute("y1", gnd.toFixed(0)); g.setAttribute("y2", gnd.toFixed(0)); }
    };
    setBox();

    /** Screen point → Arta's world. Everything external arrives through here. */
    const toWorld = (cx: number, cy: number): XY => {
      const r = root.getBoundingClientRect();
      if (!r.width || !r.height) return { x: 0, y: 0 };
      return { x: ((cx - r.left) / r.width) * vw, y: ((cy - r.top) / r.height) * wh };
    };

    let shownAct = "";
    const paint = (f: ReturnType<Brain["step"]>) => {
      const s = f.sk;
      // The current act, on the DOM. Costs one attribute write per state change
      // and makes the whole state machine observable from the outside — which is
      // the only reason the reduced-motion arrow bug was findable at all.
      if (f.act !== shownAct) { shownAct = f.act; el.setAttribute("data-act", f.act); }
      // Self-reporting invariant: this attribute must never appear. It is the
      // cheapest possible way to notice a future gesture outrunning the limit.
      if (f.peakPx > SAFE.MAX_PX_PER_FRAME + 0.5) el.setAttribute("data-overspeed", f.peakPx.toFixed(1));
      torso.current?.setAttribute("d", s.torso);
      armL.current?.setAttribute("d", s.armL);
      legL.current?.setAttribute("d", s.legL);
      armR.current?.setAttribute("d", s.armR);
      legR.current?.setAttribute("d", s.legR);
      head.current?.setAttribute("cx", s.head.cx.toFixed(1));
      head.current?.setAttribute("cy", s.head.cy.toFixed(1));
      // ── the rope ──────────────────────────────────────────────────────────
      // Drawn with a sag rather than as a straight segment: a line under a
      // hanging figure is a catenary, and a taut chord reads as a wire.
      const rp = rope.current;
      if (rp) {
        if (!f.rope) rp.setAttribute("opacity", "0");
        else {
          const { from, to } = f.rope;
          const mx = (from.x + to.x) / 2, my = (from.y + to.y) / 2;
          const span = Math.hypot(to.x - from.x, to.y - from.y);
          const sag = f.airborne ? Math.min(26, span * 0.05) : Math.min(46, span * 0.09);
          rp.setAttribute("d",
            `M${from.x.toFixed(1)} ${from.y.toFixed(1)}Q${mx.toFixed(1)} ${(my + sag).toFixed(1)} ${to.x.toFixed(1)} ${to.y.toFixed(1)}`);
          rp.setAttribute("opacity", "0.85");
        }
      }
      const a = arrow.current;
      if (!a) return;
      if (!f.arrow) { a.setAttribute("opacity", "0"); return; }
      const { from, to, age } = f.arrow;
      // Sagittarius fires an ARROW — a short shaft that travels from the hand to
      // the target and fades. The first version drew the whole hand-to-target
      // line, which reads as a rope strung across the page and cuts through the
      // body copy on its way. A short thing in flight says "that one, over
      // there" without connecting two points with a wire.
      const dx = to.x - from.x, dy = to.y - from.y;
      const len = Math.hypot(dx, dy) || 1;
      const ux = dx / len, uy = dy / len;
      // Fly only as far as the stage. A target below the fold has a world y well
      // outside the viewBox — measured at y 2024 in an 813-tall stage — so the
      // arrow was drawn correctly and entirely off-canvas: the act reported
      // `point`, the opacity read 0.8, and the viewer saw nothing at all. The
      // gesture communicates a DIRECTION, and clamping the flight to the edge
      // leaves the direction untouched. Infinity is the honest answer for a ray
      // parallel to an edge pair, and `len` bounds it in any case.
      const exit = (o: number, d: number, lo: number, hi: number) =>
        d > 1e-6 ? (hi - o) / d : d < -1e-6 ? (lo - o) / d : Infinity;
      const M = 14;                                              // stage inset
      const reach = Math.max(46, Math.min(len, exit(from.x, ux, M, vw - M), exit(from.y, uy, M, wh - M)));
      const shaft = Math.min(58, reach * 0.4);
      const u = Math.min(1, age / 0.5);
      const t0 = 22 + Math.max(0, reach - shaft - 22) * (u * (2 - u));   // ease-out flight
      const ax = from.x + ux * t0, ay = from.y + uy * t0;
      const bx = ax + ux * shaft, by = ay + uy * shaft;
      const px = -uy, py = ux;                                   // barb direction
      const fade = Math.min(1, age / 0.12) * (1 - Math.max(0, Math.min(1, (age - 1.1) / 0.6)));
      a.setAttribute("d",
        `M${ax.toFixed(1)} ${ay.toFixed(1)}L${bx.toFixed(1)} ${by.toFixed(1)}` +
        `M${(bx - ux * 13 + px * 8).toFixed(1)} ${(by - uy * 13 + py * 8).toFixed(1)}` +
        `L${bx.toFixed(1)} ${by.toFixed(1)}` +
        `L${(bx - ux * 13 - px * 8).toFixed(1)} ${(by - uy * 13 - py * 8).toFixed(1)}`);
      a.setAttribute("opacity", (0.8 * fade).toFixed(2));
    };

    // ── reduced motion: one pose, no loop, still directable ─────────────────
    // Fast-forward 0.6s of simulation so a commanded gesture is shown at rest.
    // Painting at t=0 would show the arrow at the very start of its fade-in,
    // which is opacity 0 — the gesture would silently never appear.
    const still = () => {
      const inp = { look: null, busy: true, ground: gnd, scale, floors: readFloors(),
                    minX: vw * rangeLo, maxX: Math.max(vw * rangeLo + 60, vw * rangeHi) };
      let f = brain.step(0, inp);
      for (let i = 0; i < 6; i++) f = brain.step(0.1, inp);
      paint(f);
    };

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      const dt = prev ? (now - prev) / 1000 : 0;
      prev = now;
      // Low-pass the pointer before the head chases it, HARD.
      //
      // A shake is direction reversals, not distance, so the speed limit in the
      // rig cannot catch this one. Measured with a jittering pointer, a 62 ms
      // filter let the head reverse 8.6 times a second — more often than the
      // stimulus itself, which is amplification, not tracking. A real hand
      // tremors and a real mouse sensor is noisy, so anything fast enough to
      // follow a genuine glance is also fast enough to follow the noise.
      //
      // 250 ms instead. The head then reads as following with weight, which is
      // what a look actually is; the dead zone above stops sensor noise from
      // entering at all.
      if (!rawLook) look = null;
      else if (!look) look = { ...rawLook };
      else {
        const g = 1 - Math.exp(-4 * dt);
        look = { x: look.x + (rawLook.x - look.x) * g, y: look.y + (rawLook.y - look.y) * g };
      }
      if (now - floorsAt > 250) { floors = readFloors(); floorsAt = now; }
      const f = brain.step(dt, {
        look, busy: now < busyUntil, ground: gnd, scale, floors,
        minX: vw * rangeLo, maxX: Math.max(vw * rangeLo + 60, vw * rangeHi),
      });
      paint(f);   // every frame: the brief is smoothness, not the drawn cadence
    };

    const startLoop = () => {
      if (raf || reduce?.matches) return;
      prev = 0;
      raf = requestAnimationFrame(frame);
    };
    const stopLoop = () => { if (raf) cancelAnimationFrame(raf); raf = 0; };

    // ── inputs ──────────────────────────────────────────────────────────────
    // Dead zone: below this the pointer has not really moved, it has wobbled.
    // Stated in CSS px so it means the same thing at every stage size.
    const DEAD = 4 * scale;
    const onMove = (e: PointerEvent) => {
      const p = toWorld(e.clientX, e.clientY);
      if (!rawLook || Math.hypot(p.x - rawLook.x, p.y - rawLook.y) > DEAD) rawLook = p;
    };
    const onLeave = () => { rawLook = null; look = null; };
    const onScroll = () => { busyUntil = performance.now() + 450; sync(); };
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)) busyUntil = performance.now() + 1200;
    };

    const onCmd = (c: Cmd) => {
      // With no loop running there is no gesture in flight to protect, and an
      // act can never time out — so a queued command would never be dequeued.
      const apply = reduce?.matches
        ? (a: Act, o?: { at?: XY; x?: number }) => brain.force(a, o)
        : (a: Act, o?: { at?: XY; x?: number }) => brain.command(a, o);
      if (c.el) {
        const r = c.el.getBoundingClientRect();
        const p = toWorld(r.left + r.width / 2, r.top + r.height / 2);
        if (c.act === "walk") apply("walk", { x: p.x });
        // "throw" as a COMMAND means "travel there" — the planner decides
        // whether that is a walk or a rope.
        else if (c.act === "throw") {
          // Clamp into the stage. A target below the fold has a world y outside
          // the viewport, and an unclamped goal sends Arta rappelling into the
          // void at speed — correct physics, useless behaviour.
          const cl = (v: number, lo: number, hi: number) => (v < lo ? lo : v > hi ? hi : v);
          const goal = {
            x: cl(p.x, vw * rangeLo, Math.max(vw * rangeLo + 60, vw * rangeHi)),
            y: cl(p.y, 120, gnd),
          };
          if (reduce?.matches) brain.placeAt(goal, gnd);
          else brain.travelTo(goal);
        }
        else apply(c.act, { at: p });
      } else {
        apply(c.act);
      }
      if (reduce?.matches) still();
    };

    /*
      Whether the loop should be running is RECOMPUTED from the element's real
      rect, never remembered. A cached `visible` flag was the previous design and
      it was a one-way door: any observer callback that reported a partial entry
      list latched it to false, and Arta stayed dead for the rest of the visit
      even while plainly on screen. Recomputing is self-healing — a wrong answer
      lasts one check instead of forever.

      The rect read is throttled to 4/second; it is a layout read and scroll
      fires far more often than that, while a quarter second of extra loop is
      invisible.
    */
    const shouldRun = () => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.bottom > -80 && r.top < window.innerHeight + 80;
    };
    const sync = (force = false) => {
      const t = performance.now();
      if (!force && t - lastCheck < 250) return;
      lastCheck = t;
      if (!document.hidden && !reduce?.matches && shouldRun()) startLoop(); else stopLoop();
    };
    // Recovery must not be purely event-driven. A burst of scroll events can
    // stop the loop, have the remainder of the burst swallowed by the throttle
    // above, and then no further event ever arrives to start it again — Arta
    // frozen for the rest of the visit. A slow heartbeat closes that hole for
    // the cost of one rect read twice a second, and it is the ONLY thing that
    // recovers a state nothing else will observe.
    const beat = window.setInterval(() => sync(true), 500);
    const io = new IntersectionObserver(() => sync(true), { rootMargin: "80px" });
    const onVis = () => sync(true);
    const ro = new ResizeObserver(() => { setBox(); sync(true); });

    io.observe(el);
    ro.observe(el);
    const unsubscribe = onArtaCommand(onCmd);
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerleave", onLeave);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("keydown", onKey, { passive: true });
    document.addEventListener("visibilitychange", onVis);
    const onReduce = () => { if (reduce?.matches) { stopLoop(); still(); } else sync(true); };
    reduce?.addEventListener?.("change", onReduce);

    if (reduce?.matches) still(); else sync(true);

    return () => {
      stopLoop();
      window.clearInterval(beat);
      io.disconnect(); ro.disconnect();
      unsubscribe();
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("visibilitychange", onVis);
      reduce?.removeEventListener?.("change", onReduce);
    };
  }, [height, start, rangeLo, rangeHi, fill, figure]);

  return (
    <div ref={host} className={className} style={fill ? undefined : { height }} data-arta>
      <svg
        ref={svg}
        className="block h-full w-full overflow-visible"
        viewBox={`0 0 600 ${WORLD_H}`}
        preserveAspectRatio="xMidYMax meet"
        role={label ? "img" : "presentation"}
        aria-label={label}
        aria-hidden={label ? undefined : true}
      >
        {ground && (
          <line
            x1="0" y1={GROUND} x2="4000" y2={GROUND}
            className="stroke-line" strokeWidth="1.5" vectorEffect="non-scaling-stroke"
          />
        )}
        {/* The line. Blue, because it is a tool (ARTA.md §8). */}
        <path
          ref={rope} data-arta-rope opacity="0" fill="none" stroke="currentColor" strokeWidth="2.5"
          strokeLinecap="round" vectorEffect="non-scaling-stroke" className="text-arta-tool"
        />
        <path
          ref={arrow} data-arta-arrow opacity="0"
          fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          vectorEffect="non-scaling-stroke" className="text-arta-tool"
        />
        <g
          fill="none" stroke="currentColor" strokeWidth="7"
          strokeLinecap="round" strokeLinejoin="round"
          vectorEffect="non-scaling-stroke" className="text-arta"
        >
          <path ref={torso} vectorEffect="non-scaling-stroke" />
          <path ref={armL} vectorEffect="non-scaling-stroke" />
          <path ref={legL} vectorEffect="non-scaling-stroke" />
          <path ref={armR} vectorEffect="non-scaling-stroke" />
          <path ref={legR} vectorEffect="non-scaling-stroke" />
          <circle ref={head} r={RIG.HEAD_R} vectorEffect="non-scaling-stroke" />
        </g>
      </svg>
    </div>
  );
}
