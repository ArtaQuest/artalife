# "Two lives" — the ArtaQuest channel teaser

Twenty-two seconds, 1920 × 1080, 24 fps. Arta walks in, stands where the show's host
stands, and aims at one side of the screen and then the other while a life draws itself
down each edge as a gold rail of years. At the end both rails reach the same row and
Arta aims up at the name.

**One rig.** Every joint comes from `../undefined/generate.py` — the same skeleton,
proportions, joint convention, walk cycle and motion-safety law as the published film
and the live mascot. This scene adds a performance, not a character.

**What is different is the medium.** The published scene is an SVG that holds each
drawing on twos; the figure here does the same, at 12 Hz, while the rails and the type
run at 24. A teaser is a video, so the frames rasterise with PIL instead of serialising
as SMIL.

**The rest of the frame is the show's, not this repo's.** The two timeline rails sit at
the coordinates the episode frame puts them at, and the lines are set on the show's own
lower-third — a 10 px blue bar and a black 80 % plate. Those numbers come from the
ArtaQuest YouTube kit's editor spec, section 3.

The rails carry no name, no date of birth and no birthplace. A teaser shows the shape of
two lives that meet and keep going; the episode frame carries the record.

```sh
python3 generate.py --check     # geometry and the motion-safety law, before any render
python3 generate.py             # frames/00000.png … 00527.png
python3 generate.py --frames 60 300 504
```

`--check` is a gate, not a report: it fails if any drawn point moves more than 640 units
a second (53 a drawing on twos, scaled to this frame), or if Arta is not standing on the
ground. It caught a 122 px teleport and a figure planted 39 px underground before a
single frame was rendered.

Fonts (Montserrat 700/800, Inter 500/600) are fetched into `fonts/` and are not
committed; neither are the frames. The video and its music are assembled by the public
Kaggle notebook in ArtaQuest/artamusic (`stages/artaquest_teaser.py`).
