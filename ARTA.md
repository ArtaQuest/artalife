# Arta — animation style guide

The canonical reference for how the mascot moves. Everything enforceable here is
enforced in `src/rig/arta.ts`; this document explains *why*, so the
numbers can be argued with rather than merely obeyed.

Arta is a stick figure with **no face**. That is a constraint, not an omission:
with no expression to lean on, everything must be said with posture and timing.
Most of this guide is therefore about weight and delay rather than shapes.

**One rig, two lives.** The mascot and the published film (work 9319, `scenes/undefined/`) share the same skeleton, the same joint convention and the same
proportions. If the two ever diverge we have two mascots, which is none.

---

## 1. Identity

| | |
|---|---|
| Character | Curious, truth-seeking, adventurous. Sagittarius — the archer |
| Signature | **Aiming.** Arta points at what matters, and an arrow flies from its hand |
| Colour | Gold `#E8B923`, in **both** themes (`--color-arta`) |
| Proportions | spine 70 · neck 24 · head r20 · thigh/shin 52 · upper/fore arm 34/32 · total 218 |
| Joint convention | Degrees. **0 is straight down**, positive rotates toward +x |

Personality is expressed as numbers, not adjectives (`TRAITS`): `curiosity`,
`restlessness`, `boldness`, `conviction`, `patience`. Change them and Arta reads
as a different character. That is the intended way to retune it.

---

## 2. The three laws

A character on every page is either a companion or an irritation, and the
difference is entirely in what it refuses to do.

1. **Never blocks.** No covering content, no dialogue, nothing to dismiss. Arta
   renders on a `pointer-events-none` layer so it *cannot* swallow a click.
2. **Reacts, never interrupts.** Arta answers what you do. It has no tips to
   volunteer and nothing to say that you did not just cause.
3. **Goes still when you work.** Typing, reading, scrolling → `busy`, and Arta
   settles. Presence and motion are different things.

---

## 3. Motion safety — the hard limit

**No drawn point may move more than `min(640 px/s · dt, 12 px)` in one frame.**

Two ceilings, because they bind at different frame rates and both matter:

- **`MAX_PX_PER_FRAME = 12`** guards against **strobing**. An un-blurred line
  that travels much more than about twice its own stroke width between frames
  stops reading as movement and becomes a sequence of separate positions. This
  binds when the frame rate is *low*.
- **`MAX_PX_PER_SEC = 640`** guards against being **too fast to follow**, which
  is the comfort and vestibular concern rather than the legibility one. This
  binds at 120 Hz, where a per-frame budget alone would silently permit twice
  the real-world speed.
- **`MAX_FLASH_HZ = 2`** — nothing may oscillate in opacity or visibility faster
  than this. WCAG 2.3.1 draws the seizure line at 3 Hz; the platform's calm rule
  is stricter, and a mascot has no business near either.

### How it is enforced

The blend factor for the whole figure is scaled back until the largest
single-point displacement fits the budget:

```
u      = 1 - e^(-k·dt)
next   = blend(pose, want, u)
moved  = max displacement over EVERY drawn point
if moved > budget:  u *= budget / moved;  next = blend(pose, want, u)
```

Scaling the whole blend — rather than clamping points individually — matters: the
figure has to stay a figure, so it slows as one body instead of having a fast
limb amputated from a slow torso. Because the measurement is over every drawn
point, it covers root motion, limb swing and turning at once, **and a gesture
added later cannot escape it**.

### The invariant is self-reporting

If the cap is ever exceeded, the component writes `data-overspeed` onto its host
element. That attribute must never appear. Measured under a worst-case stress
run (every gesture back to back, pointer whipped side to side to force repeated
turns, 595 frames): **peak 11.18 px/frame, flag never raised**.

### Turning is continuous, not a flip

Facing is implemented by negating every joint angle, so treating `face` as a
boolean moves a foot **~43 px in a single frame** — by a wide margin the largest
gradient in the system, and one no blend can soften because it is discrete.
`face` is therefore a continuous value in `[-1, 1]`. Easing it through zero gives
a real turn: the figure narrows to its own profile, passes edge-on, and opens out
the other way.

---

## 4. Cadence

| Context | Cadence | Why |
|---|---|---|
| **The mascot** (this rig) | Smooth, every frame, display-native | Operator brief: as smooth as the panel can manage |
| **The film** (`scenes/undefined/generate.py`) | On twos, `calcMode="discrete"` | Hand-drawn cadence; a held drawing reads as *drawn* |

These are deliberately different and both are correct for their medium. Do not
"fix" one to match the other.

Every rate in the mascot rig is expressed **per second** and integrated with
`dt`. All easing is `1 - e^(-k·dt)`, which is frame-rate independent: identical
motion at 60 and 144 Hz, and correct again after a dropped frame. A fixed
per-frame fraction is neither. Frames longer than 1/45 s are **sub-stepped**, so
a stall cannot fling Arta across the stage.

Easing constants: `k = 34` for a walk (the cycle *is* the animation, so tracking
is near-rigid), `k = 11` for a gesture (arrives softly).

---

## 5. Timing vocabulary

Real values from the shipped acts. Reuse them; a new gesture that invents its own
timing will feel like it belongs to a different character.

| Beat | Duration | Note |
|---|---|---|
| Anticipation before a launch | 0.18 s | A jump with no crouch reads as a shrug |
| Gesture settle-in | ~0.25 s | `k = 11` exponential, not a linear ramp |
| Wave | 1.7 s | Once, on arrival. **Never on a loop** |
| Aim held | 2.6 s (`conviction`) | Long enough to follow the arrow, short enough not to nag |
| Arrow flight | 0.5 s, fade at 1.1 s | |
| Turn | 0.30 s | A squash for weight; `face` eases through zero on its own |
| Idle → wander | 7 s (`restlessness`) | |
| Idle → sit down | 75 s (`patience`) | |
| Reaction delay after a UI event | 260–480 ms | Reacting on the same frame reads as *part of the UI*; a beat later reads as **noticing** |

---

## 6. Pose construction

- **Clearance.** The upper arm is 34 and the head sits 24 above the neck with
  r20. Any raised-arm pose must be checked against the skull — a wave at 152°
  draws the forearm straight through it. Out-and-then-up (shoulder ~118°, rocking
  in the elbow) clears by ~31.
- **Silhouette at mascot scale.** Arta renders ~100–135 px tall on a page, not
  ~35% of a 1600 px frame as in the film. The film's closed stance merges into a
  single stroke at that size and reads as a lollipop. The mascot's default stance
  is deliberately wider: arms ±14°, legs ±7°.
- **Staging.** Arta rests only on gap centres between page elements, never on top
  of one. Two silhouettes in the same place read as neither.
- **The breath lengthens the spine, never the legs.** Scaling the legs lifts the
  feet off the ground line.
- **A rest pose must still move.** A settled figure breathes, shifts weight and
  drifts its head, at an amplitude that falls to zero the moment it is genuinely
  moving.

---

## 7. The signature gesture

`arta.pointAt(el)` aims at a real DOM element and fires a short arrow.

**Do** use it to answer a question the visitor already has — the primary CTA, the
field that just became relevant, a check that is failing.

**Don't** use it to volunteer information, more than once per screen, or for
anything the visitor did not just cause. An archer who fires constantly is not
an archer.

The arrow is a **short shaft in flight**, not a line from hand to target. The
full-length version reads as a rope strung across the page and cuts through
whatever body copy lies between.

---

## 8. Colour and contrast

**Arta is gold. Arta's tools are blue.**

| | Token | Value | Role |
|---|---|---|---|
| The figure | `--color-arta` | `#E8B923` | Yang — the *why* |
| Anything it wields or makes | `--color-arta-tool` | `#4A72FF` | Yin — the *how* |

The figure is gold `#E8B923` in **both** themes — the mascot is one recognisable
character, and a character that changes colour with the canvas is two.

Tools are blue, which is the brand pair doing narrative work rather than
decorating: the gold figure acts, the blue instrument is what it acts *with*.
Today the only tool is the arrow; the token is the rule, not the exception, so a
bow, a pen or a lamp added later is blue without further discussion.

The tool blue is `--color-yin-light` rather than canonical `#1746DC` because a
tool must read on **both** canvases, and canonical yin measures only ~2.0:1 on
the dark cosmos — the exact mirror of gold's problem on white. `#4A72FF` is
~4.0:1 on the cosmos and ~4.6:1 on white, so one value serves both.

**Recorded honestly:** gold measures **~1.8:1 on the white light canvas**, below
the 3:1 WCAG floor for a non-text graphic, so on light Arta reads as a soft mark
rather than a crisp one. Arta is never the sole carrier of information, so this
is not a blocking failure — but do not add a state that only Arta's colour
communicates. If it ever needs fixing without giving up gold, the lever is a
luminance-only deepening on light (hue stays gold), which is exactly what
`--ico-gold` exists to do for the topic icons.

Never a third accent. Blue is the antagonist's colour in the film, not Arta's.

---

## 9. Accessibility

- **`prefers-reduced-motion`** → one static pose and **zero animation frames ever
  scheduled**. Arta is still there and can still point; the sim is fast-forwarded
  0.6 s so a commanded gesture is shown at rest. Absence is the lazy answer to
  that setting, and painting at t=0 shows the arrow at opacity 0 — invisible.
- Arta is `aria-hidden` unless it is doing a job, in which case it takes a
  `label` describing what it is doing, not what it looks like.
- Arta never carries information alone. Everything it points at is also reachable
  and readable without it.

---

## 10. Performance budget

Measured, not asserted:

| Condition | Frames | Attribute writes |
|---|---|---|
| On screen, calm | 60/s | 362/s |
| Scrolled out of view | **0** | **0** |
| Tab hidden | **0** | **0** |
| `prefers-reduced-motion` | **0** | **0** |

**No React state in the animation loop** — the frame writes attributes onto refs.
Re-rendering a component tree 60 times a second to move a stick figure would be
the most expensive thing on the page and is entirely avoidable.

Whether the loop should run is **recomputed from the element's real rect**, never
remembered. A cached visibility flag is a one-way door: one bad reading and Arta
is dead for the rest of the visit.

---

## 11. Adding a gesture

1. Add a pose function to the library in `arta.ts`. Check clearance (§6).
2. Add the act to the `Act` union and one `case` in the state machine, with a
   timeout. Every act must end by itself.
3. Add one line to the `arta` bus in `Arta.tsx`.
4. Add it to the stage on `/arta` so it is inspectable.
5. Run the stress harness and confirm `data-overspeed` never appears.

An act **must not** be able to start from a non-settled pose without a
transition, and **must not** rely on being interrupted to end.

---

## 12. Verification

Nothing here is believed without measurement. Run:

```
node tools/arta-audit.mjs [url]   # AQ_CDP=… against any Chrome with a debug port
```

It exits with the number of failed checks, so CI can gate on it. Fifteen checks
in five groups — cost, calm, head, speed, reduced; current baseline, all passing:

| Check | Measured |
|---|---|
| Runs on screen | 60 rAF/s, 360 attr/s |
| Stops off screen / tab hidden | 0 / 0 |
| Settles into an act | `idle`, 0 changes in 5 s |
| Head oscillation at rest | 0.4 Hz — the breath, and nothing else |
| Head reversals: still / sweeping / realistic hand | 0.5 / 0.8 / 0.5 per second |
| Peak per-frame movement | 12.4 px sampled, `data-overspeed` never raised |
| Reduced motion | 0 frames, 5/5 limbs drawn, arrow at 0.8, on stage |
| Probes saw motion | asserted separately, so a dead probe cannot read as calm |

**A skip is not a pass, and the tally must say so.** The run prints
`14/14 asserted checks passed, 1 skipped (…)`, naming what went unmeasured. It
used to print `15/15` for a run in which two checks measured nothing. A check
with nothing to measure gets three outcomes, not two: genuinely inapplicable
(the fixed companion layer cannot leave the viewport, so `stops off screen` is
N/A and `stops when tab hidden` carries that law), no control on this page
(SKIP, with the page that does have one named), or **a probe that should have
worked and did not — which is a FAIL**, because a broken probe reporting PASS is
the whole failure mode this suite exists to catch.

Run it against **production** too, not just the dev server — the clamp
convergence bug above passed every local run and failed on the first prod run.

**A shake is direction reversals, not amplitude.** The speed limit in §3 cannot
catch one — a head can reverse eight times a second while never exceeding a
fraction of the per-frame budget. Measure reversals, and measure them under a
*realistic* hand (slow drift plus a few px of tremor), not a mouse being shaken
on purpose. Following a deliberate 2.6 Hz input is correct behaviour; the audit
reports that case without asserting on it.

**A failing test is sometimes the test's fault.** Six false failures in this
build: `svg path` matched the deliberately-empty arrow, and later the rope; the
off-screen test scrolled the window while the SPA scrolls an inner container; a
per-frame delta was sampled twice inside one discrete step; a rect was read
before a smooth-scroll had finished; reusing a URL made the navigation
fragment-only, so nothing remounted; and a guard matched "409 processed", which
was a file counter, not an HTTP status. Check the probe before believing the
failure — but check it *quickly*, because real bugs hide behind that excuse.

**The far worse failure is a green run built from nothing.** One 13/13 was
entirely zeros: a reused tab leaked scroll position and media emulation into
the next phase, and navigating to an identical URL never reloaded, so the whole
run measured a reduced-motion Arta that was scrolled out of view and reported
perfect health. Every probe that *can* measure nothing now has a companion check
asserting it saw something — `head · probe actually saw motion`,
`speed · probe actually saw motion` — and a check with no control to drive says
**SKIPPED** rather than passing vacuously. A pass whose evidence is zero is not
a pass; it is an untested claim wearing one.

Two thresholds in the audit are deliberately looser than the law they guard, and
both say why in the source: the sampled peak-px bound (a separate rAF can see
two sim frames as one) and the head reversal limit (the breath, weight shift and
tilt drift are three independent oscillations that legitimately sum to ~2/s).

---

## 12b. Rope travel, and Arta everywhere

Arta is a single page-level companion, not three per-page stages: one fixed
layer, present everywhere, following the reader.

**Rope is the travel tool, and it unifies with the signature.** Sagittarius
fires an arrow; the arrow carries the line. The grapple is not a second mechanic
bolted on, it is the gesture Arta already has, doing work. The rope is blue
because it is a tool (§8) — the existing rule, not a new one.

**Rope solves what walking cannot.** Scrolling is vertical and a walker only
travels horizontally, so a walk-only companion can never actually follow the
reader. A line thrown to an anchor gives Arta the vertical axis.

**Travel is planned, not lerped.** `Brain.travelTo` picks a goal, then chooses:
short and level → walk; far or vertical → rope. The rope run is
`throw → fly → land`, and the swing is a **pendulum, not a zip-line between two
pins** — a straight interpolation to the anchor is the tell that there is no
rope, only a tween. Arta takes the time it takes, must never teleport, and must
never keep up perfectly: arriving late is the character. A reader who jumps a
long way legitimately leaves Arta behind to make its own way there.

**Arta stands on something.** Gravity is real: `Floor` ledges are read from the
page, `floorUnder` finds the surface beneath the feet and `fall` runs until it
is reached. Hovering is not a state the rig can be in — if Arta is not on a
ledge it is falling to one, or it is on the rope.

Two things this must not break. The §3 speed ceiling applies to a swing exactly
as it does to a step. And **reduced motion cannot travel** — no loop runs, so a
rope trip would strand Arta hanging forever; that path relocates instead
(`Brain.placeAt`).

**Getting onto a ledge overhead** used to be impossible, and the reason was
that relocation asked the wrong question. `nearestStand` answers "which ledge is
closest horizontally", so Arta walked to the spot beneath a card, arrived no
higher than it started, failed the same on-a-card test and set off again.
`nearestPerch` returns a POINT and prices the trip in 2D, charging 1.8x for
height — climbing is not strolling — and anything overhead goes by rope.

**Wandering has to stay on a surface too.** The restless walk picked a random x
across the whole stage and went to the horizontally nearest ledge, which from
the top of a card means walking off the end of it. Arta fell, climbed back,
walked off again, and spent 25 seconds of every 60 in the air. It now strolls
along the ledge it is on and now and then ropes across to a different one.
Walking off a ledge is not exploring, it is falling.

**Measured**, on a page whose ledges are all overhead: on a real ledge 4% → 92%
of settled time, airborne 25 s → 3.6 s per minute, worst gap while settled
24.2 px → 1.4 px.

---

## 12c. The gait, and why it is solved rather than posed

Arta's legs are the one place in the rig where joint angles are an OUTPUT.

A walk is judged almost entirely on one thing: does the planted foot stay
planted. The first version drove both legs as sinusoids in antiphase and let the
root advance at a constant speed, with nothing tying the two together — and they
disagreed by a lot. Through what should have been the left leg's stance the foot
slid 47 px forward and 19 px back across the ground. No foot was ever planted,
which is why the figure read as gliding, and it had been that way from the first
day because joint angles are the easy thing to animate and contact is the thing
that matters.

So the FOOT PATH is authored and the joints are solved by two-link IK:

- **Stance** — the foot does not move in the world, so relative to the advancing
  root it slides straight back at exactly the root's speed. That identity is the
  whole design.
- **Swing** — a cubic Hermite whose end slopes MATCH the stance velocity, so the
  foot is still travelling backwards as it leaves the ground and again as it
  lands. Anything else changes the foot's velocity in a single frame, and that
  showed up as a knee whipping at 810 px/s just after toe-off. Lift is `sin²`,
  flat at both ends, for the same reason.
- **Hip height** — each foot says `h ≤ lift + √(REACH² − dx²)` and the lower
  answer wins, so the hip rides a circular arc over the planted foot: the
  compass gait, and the reason the knee does not pop mid-stance.
- **Stance fraction above 0.5** — the overlap is double support, and double
  support is the entire difference between a walk and a run.

`WALK.CYCLE` is read by the brain rather than copied into it. Phase and ground
travel are one contract; two copies of a number is two chances to break it.

**Measured:** planted-foot drift 40.9 px → 0.00 px in the pose, and ≤ 1.8 px
live at 30, 60 and 144 Hz.

---

## 12d. Speed is chosen to fit the budget, not clipped by it

Those are different things, and the difference is visible.

The gait's fastest point (the knee, just after toe-off) travels ~3.6× the root
speed. At 210 px/s that is over the ceiling, so the clamp fired — and a clamped
walk is a walk whose POSE is slowed while its phase keeps its own time, which is
to say a walk whose legs cycle faster than its body travels. That is skating,
and it measured 28 px of drift per stance at 30 Hz.

So the walk asks the frame what it can afford and picks a speed that fits:
`min(210, budget / dt / PEAK_RATIO)`. Above about 45 Hz that is 168 px/s and
frame-rate independent; below it Arta genuinely walks slower, which is the
correct answer, because the anti-strobe ceiling is a fact about perception and
not a budget to be spent.

**Any act that moves the body fast must do this.** Being clipped afterwards is
never as good as not asking for too much.

---

## 13. Anti-patterns

Every one of these was actually done here, found by looking, and fixed.

- **Spending the per-frame ceiling once per SUB-STEP.** `step()` sub-steps at
  1/45 s, and the clamp lived inside the sub-step, so a 30 Hz frame — which
  sub-steps twice — was handed the budget twice and painted 13.2 px against a
  12 px limit. Invisible at 60 and 144 Hz, where one frame is one sub-step,
  which is exactly why it survived every earlier run. A limit about what the
  viewer sees between two painted frames has to be computed per painted frame.
- **Defining a moving target RELATIVE to the current pose.** The walk set
  `want.x = pose.x + stepD` every frame. Against an exponential ease that is not
  a lag, it is a speed DIVISION: the body only ever covers `u` of each step, so
  Arta walked at 90 px/s instead of 210 at 60 Hz — and at 44 px/s at 144 Hz,
  frame-rate-dependent motion inside a rig whose whole doctrine is frame-rate
  independence. Integrate the position and hand the ease an ABSOLUTE target;
  tracking a ramp then has a constant position lag and zero velocity error.
- **A `min` over a set whose membership changes.** Hip height was the minimum
  over the feet currently DOWN, and that set changes four times a cycle, so `h`
  stepped 1.3 px at each change. A knee near full extension is worth about six
  degrees per pixel of reach, so a 1.3 px step threw it 3.6 px sideways in one
  frame. Let each member relax its own constraint continuously (a raised foot
  loosens by exactly its lift) and the set disappears along with the pop.
- **Believing a sum of sines will not repeat.** Idle weight shift was three
  sines. Spacing them by the golden ratio — the most irrational number there is,
  so the latest possible near-repeat — still left the head 99% self-similar
  after 50 seconds, because the Fibonacci convergents of φ are precisely where a
  near-repeat lands. Shifting your weight is not oscillation anyway: it is
  deciding to stand differently, holding it, and deciding again. Seeded drift,
  re-targeted on a random interval, never repeats and reverses direction LESS
  often than a sine.
- **Easing every joint at one rate.** A shoulder leads, an elbow trails, a head
  arrives last, and that ordering is most of what separates animation from
  interpolation. `1 - (1-u)^f` is the same ease at `f` times the rate, so
  per-channel follow costs one `pow` and stays frame-rate independent. Do NOT
  drag a leg: its angles are an IK solution for a planted foot, and a leg that
  lags its solution is a foot that slides.
- **Measuring motion off the rendered path strings.** They round to 0.1 px, so a
  probe that samples finely enough measures the ROUNDING and reports nonsense —
  in one run, a peak speed of 99× the root speed. Sample at real frame steps, or
  read the numbers before they are formatted.
- **A pose that lowers the hip without shortening the legs to match.** `crouch`
  dropped the hip 26 px while its knee bend only shortened the legs by 15, so
  the feet finished 11 px UNDER the surface. `floorUnder` then read that ledge
  as being above the feet, discarded it, found nothing else beneath, and Arta
  fell through the floor it had just landed on — on every rope trip, for as long
  as the pose existed. `footDrop(pose)` exists so no act has to hand-tune this:
  the hip goes at `surface - footDrop`, and that is true for any pose.
- **A point test against a moving body.** The fall looked up its support from
  where the feet would be at the END of the step, and `floorUnder` discards
  ledges above the feet — so a ledge crossed WITHIN one step was discarded as
  though Arta were already past it. Feet at 488 one frame, 507 the next, and a
  card at 500 that never existed. Test from the START of the step and it is a
  swept test.
- **Hooking the rope somewhere that does not exist.** The anchor is 150 above
  the destination, which for a card near the top of the page put it at y = -14:
  Arta flew off the top of its own viewBox. Take whatever headroom there is.
- **Blending an ABSOLUTE pose against a RELATIVE one, then adding the base
  again.** `base` is `support - RIG.HIP`; every library pose carries an offset.
  `cheer` blended the two and then added `base.y`, asking for twice the support
  height — on the shipped mount, a hip target 800 CSS px below the floor, for
  the anticipation and again for the recovery. Only the speed clamp contained
  it, and a clamp is a rate, not a veto, so Arta visibly sank and climbed back
  on every successful sign-in. Blend relative against relative.
- **Targeting the stage floor from an act that runs on a ledge.** The walk set
  `want.y = input.ground - RIG.HIP + …`, discarding the support resolved fifty
  lines earlier. On a card the first walking frame aimed a card's height too
  low, the feet went under the ledge, `floorUnder` discarded it as being above
  them, and the act became `fall` — so Arta could never walk on a card at all,
  and the bug was invisible on any page without one, because there the support
  IS the ground.
- **Scaling the legs to squash.** `turn` used `sq`, which multiplies THIGH and
  SHIN, so a 6% squash lifted both feet clear of the ledge for the whole turn:
  a figure that hops slightly whenever it changes direction. Squash the spine.
- **A state that is none of the three permitted ones.** `perch` put the hip on
  the rope's hook, which left the drawn grip 135 units above it holding nothing,
  150 above whatever Arta had travelled to see, with no line drawn and no exit
  condition — and it was the DEFAULT branch out of a flight. Deleted. A rope
  trip now ends through the same contact code as a step off a lip.
- **Resetting a counter before deciding whether to act on it.** `idleFor` was
  zeroed whenever restlessness fired, before the distance test that decides
  whether a walk actually starts, so it never exceeded 7 s and
  `TRAITS.patience` (75 s) was unreachable: `rest()`, a fully authored pose,
  had never once been drawn. Patience also measured the wrong clock — Arta has
  an idea every 7 seconds, so its own stillness can never reach 75. Sitting
  down is a response to an empty ROOM. Measure the visitor.
- **Gating a behaviour on the PRESENCE of a pointer.** The idle glance required
  `!input.look`, and `look` is non-null from the first mousemove to the last, so
  on any ordinary desktop visit it never fired. Gate on the pointer being
  STILL: a hand resting on a mouse is not a hand using one.
- **An envelope that spends its randomness on silence.** The glance drove
  `sin(pi * clamp((end - now) / 1.1, 0, 1))` over a duration randomised up to
  1.9 s, and the clamp pins the argument at 1 — so `sin(pi) = 0` for the whole
  excess. A 1.9 s glance was 0.8 s of nothing followed by the same 1.1 s move.
- **Treating a finger as a cursor.** On a touch device a pointer exists only
  while something is pressed, so head-tracking was driven exclusively by the
  drag and scroll that law 3 says must silence Arta — and because a non-null
  look also suppresses the glance, a phone visitor got the stare and none of
  the character. A tap is a scroll: give it the same quiet window. A pen keeps
  tracking, because a stylus hovers.
- **Labelling the decoration.** `aria-label="Arta, the ArtaQuest mascot"` was
  passed unconditionally, so a screen-reader user met a stick figure at the end
  of every page and it led nowhere. Arta is `aria-hidden` unless it is doing a
  job, and the label then says what it is DOING.
- **Editing markup with a regex.** Removing that label with
  `re.sub(r'\s*label="[^"]*"', ...)` matched the mobile navigation's
  `aria-label="Quick navigation"` first and turned it into `aria-`. Caught only
  by reading the diff. Match the whole element, or edit the exact string.
- **A raised arm through the skull.** Wave at 152° from the shoulder.
- **The arrow as a rope.** Drawing hand→target as one line across the page.
- **A lollipop.** Reusing the film's closed stance at mascot scale.
- **A latched visibility flag.** Loop stopped on a scroll and never restarted.
- **A jammed command queue.** Under reduced motion nothing advances time, so an
  act never reaches its own timeout, `settled` stays false, and every later
  command sits in the queue forever. Reduced motion must **force**, not queue.
- **A gesture painted at t=0.** Its fade-in opacity is 0, so it never appears.
- **Standing on a glyph.** Two silhouettes in one place read as neither.
- **A frozen hold.** A settled pose with no breath is a still image, and the
  clearest tell of cheap animation there is.
- **Correcting a non-linear constraint with one linear step.** The speed clamp
  scaled the blend factor by `budget / moved` once, which assumes displacement is
  linear in that factor. The pose blends linearly but the skeleton resolves
  through sin/cos, so a single correction can still land above the ceiling — and
  it did, at 12.6 px against a 12 px limit, on **production**, where the frame
  timing differs from the dev machine's. Iterate to convergence. A limit that is
  only approximately enforced is a limit that is merely described.
- **One landing for two ways of arriving.** `land` blended out of `hang(0)`
  because a rope trip ends hanging — but a figure that simply walked off a ledge
  also lands, and it snapped into a hang for one frame on the way down. The same
  act also steered x toward `this.goal`, which after a plain fall is whatever an
  earlier trip left behind, yanking Arta sideways on touchdown. An act that two
  different histories can enter must be written for the state it is *in*, not
  for the one it usually came from. Landing means absorb, here — nothing else.

- **Comparing an intent against its own easing value.** The turn trigger tested
  the desired side against `pose.face`, a float mid-ease that is essentially
  never exactly ±1, while the base pose carried the library default of `face: 1`
  and dragged Arta back to facing right every frame. Between them Arta was
  pinned in the `turn` act forever, pulsing its squash at 1.2 Hz — a permanent
  visible shake. **Intent and interpolation must be separate fields**: `facing`
  is exactly ±1 and is what decisions compare against; `pose.face` is the
  continuous value easing toward it and is only ever drawn.

---

## 14. What this repository emits

`artalife` is the GENERATION side. It owns the character and produces artifacts;
it knows nothing about any site that shows them.

| Output | What it is |
|---|---|
| `dist/scenes/*.svg` | Finished films. Self-contained SVG + SMIL, no script, safe in an `<img>`. |
| `src/rig/arta.ts` | The live rig — pure TypeScript, no React, no DOM, no timers. |
| `src/render/Arta.tsx` | A reference renderer for the rig. Consumers may use it or write their own. |

A consumer copies the artifacts it wants and does its own integration. Nothing in
here should ever import from, or know the URL of, a consuming site — the moment
it does, the two pipelines are one again.
