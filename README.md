# artalife

Arta is a stick figure with no face who lives on the web. This repository is
where Arta is **made**: the rig, the physics, the pose library, the films, and
the tests that keep them honest.

It is deliberately separate from any site that shows Arta. **Generation and
integration are different pipelines.** This one has no idea a website exists.

## What comes out

| Artifact | Description |
|---|---|
| `dist/scenes/*.svg` | Finished films — self-contained SVG + SMIL, no script, safe inside an `<img>`. |
| `src/rig/arta.ts` | The live rig: skeleton, pose library, planner, motion-safety clamp. Pure TypeScript. |
| `src/render/Arta.tsx` | A reference renderer. Consumers may use it or write their own. |

A consuming site copies what it wants. Nothing here imports from, or knows the
URL of, anything downstream.

## One rig, two lives

The figure in a rendered film and the figure improvising on a page are the
**same skeleton** — identical proportions, identical joint convention, identical
pose library. If they ever diverge there are two mascots, which is none.

- `scenes/<name>/generate.py` bakes a timeline into an SVG. Python standard
  library only: no installs, no network, no clock, no randomness, so the same
  drawing comes out of any machine. Verified byte-identical across macOS and
  Linux.
- `src/rig/arta.ts` runs the same character live, deciding frame by frame.

## Build

```bash
python3 scenes/undefined/generate.py          # -> scene.svg + a continuity lint
node tools/arta-audit.mjs <url>               # 15 behavioural checks in a real browser
```

The audit needs a Chrome with a debug port; point it anywhere with `AQ_CDP`.
Prefer a throwaway headless instance — it cannot be throttled and never touches
a browser you are using.

## The rules

[ARTA.md](ARTA.md) is the canonical animation style guide: the character, the
three laws that keep a companion from becoming a nuisance, the hard motion-safety
ceiling, the timing vocabulary, and a list of anti-patterns every one of which
was a real mistake made here.

The short version:

- **No drawn point may move more than `min(640 px/s · dt, 12 px)` in one frame.**
  Two ceilings, because strobing binds at low frame rates and comfort binds at
  high ones. Enforced in the rig, not just described.
- **Arta never blocks, never interrupts, and goes still when you are working.**
- **`prefers-reduced-motion` means one static pose and zero animation frames** —
  still present, still able to point. Absence is the lazy answer to that setting.
- **Arta stands on something.** A real ledge, or it is falling to one, or it is
  on the rope. Never hovering.

## Credits

Arta stars in *Undefined* (`dist/scenes/undefined.svg`), a fifty-second silent
film about the one division you are not allowed to do.

## Licence

Not yet chosen. Published openly so the work can be read and checked; no
permission to reuse has been granted, so treat it as all rights reserved until a
`LICENSE` file says otherwise.
