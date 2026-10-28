# EV3 Etch A Sketch plotter: two-tick slip test

Code from the Bricks and Brains video where a LEGO Mindstorms EV3 turns both knobs of an Etch A Sketch to draw. This repo has the **two-tick slip test** from the video's challenge, plus the small plotter library it runs on.

*Not affiliated with or endorsed by the makers of Etch A Sketch, LEGO or Pybricks.*

## The challenge

I couldn't stop rubber bands from slipping on the knobs; only 3D-printed gear caps fixed it. If you can make a band drive hold, prove it with this test and post your result in the video's comments.

## What the test does

For each axis (X first, then Y):

1. Moves to a reference point, always arriving from the same side, so backlash cancels out.
2. Draws a short tick.
3. Swings that knob back and forth several times (`CYCLES`, default 5).
4. Returns to the exact same reference point, from the same side.
5. Draws a second tick continuing the first.

**No slip:** the two ticks form one straight line.
**Slip:** there's a sideways step between them, and the size of the step is how much the drive lost.

## What you need

- A LEGO Mindstorms EV3 running [Pybricks](https://pybricks.com) firmware (I used firmware 4.1.0).
- Two EV3 motors: **X knob on port A**, **Y knob on port B**.
- Two touch sensors on **ports S1 and S2**, used to jog the stylus by hand. Hold one to turn its motor, and double-press to flip direction.
- A way to turn the knobs: the gear caps, band caps or your own design. The caps are on Thingiverse and Printables (links in the video description).

## Running it

1. Install the Pybricks command-line tool (`pb`) and connect to your brick: `pb connect --hub <your brick's name>`.
2. Run the test: `pb run slip_check.py`. Upload `plotter.py` with it if your setup needs that.
3. On the brick, jog the stylus to the **bottom-left corner** with the touch sensors, finishing with each knob moving toward the corner. Then press an **arrow** button (not the centre button, which is Pybricks' stop button).
4. Watch the ticks, then read the results printed at the end.

## Settings to check in `plotter.py`

These values are for **my** build (40-tooth gear caps). Yours will differ:

| Setting | Mine | What it is |
|---|---|---|
| `X_SPAN_DEG` / `Y_SPAN_DEG` | 1657 / 1181 | Motor degrees from edge to edge. The test sizes its moves from these, so rough values are fine. |
| `x_sign` / `y_sign` | 1 / -1 | Which motor direction moves the stylus right and up. Flip them if your lines go the wrong way. |
| `X_BACKLASH` / `Y_BACKLASH` | 28 / 37 | Slack corrected when a knob reverses. The slip test switches this off. |
| `APPROACH` | 60 | How far back the stylus starts so the slack is already taken up. |

With a band drive, you'll need far more degrees per mm. My bands took about 4361 / 3143 degrees edge to edge, versus 1657 / 1181 with the gears.

## Licence

MIT. See `LICENSE`. The 3D-printed caps are released separately under CC BY 4.0.
