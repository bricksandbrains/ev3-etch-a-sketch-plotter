"""Slip check, drawn on the screen: X first, then Y.

For each axis:
  1. Arrive at a reference angle, always from the same side.
  2. Draw a tick UP from there (or LEFT, for the Y test).
  3. Swing that knob back and forth CYCLES times.
  4. Return to the exact same reference angle, from the same side.
  5. Draw a tick DOWN (or RIGHT).
No slip: the two ticks form one straight line.
Slip: there is a sideways step between them. Its size is the slip.
Arriving from the same side both times means backlash cancels out.
"""

from plotter import (X_SPAN_DEG, Y_SPAN_DEG, APPROACH, show, home, goto,
                     pause_for_shake, screen_pos)
import plotter
plotter.BACKLASH_ON = False   # this test measures the raw machine

CYCLES = 5      # back-and-forth swings per axis (was 10; compare slip PER cycle)
SPEED = 100     # deg/s for every move (slow first run with the gears; bands used 300)

# Distances as fractions of the screen, so they stay the same physical size
# whatever the coupling ratio (these match the band runs: 1000 / 400 band deg).
X_SWING = X_SPAN_DEG * 0.23   # X swing each side of the reference
Y_SWING = Y_SPAN_DEG * 0.32   # Y swing each side of the reference
X_TICK = X_SPAN_DEG * 0.09    # horizontal tick length (Y test)
Y_TICK = Y_SPAN_DEG * 0.13    # vertical tick length (X test)

# Reference points (screen degrees from the bottom-left corner)
x_ref, x_line = X_SPAN_DEG * 0.50, Y_SPAN_DEG * 0.70   # X test, upper middle
y_ref, y_line = Y_SPAN_DEG * 0.50, X_SPAN_DEG * 0.85   # Y test, right side


def go(x, y):
    """Every move in this test runs at SPEED."""
    goto(x, y, SPEED)


def x_test():
    go(x_ref, x_line + Y_TICK)        # top of the first tick
    go(x_ref, x_line)                 # tick 1, drawn down to the line
    for n in range(CYCLES):
        show("X swing " + str(n + 1) + " of " + str(CYCLES))
        go(x_ref + X_SWING, x_line)
        go(x_ref - X_SWING, x_line)
    go(x_ref, x_line)                 # back to reference, moving right
    _, y = screen_pos()
    go(x_ref, y - Y_TICK)             # tick 2, continuing down


def y_test():
    go(y_line - X_TICK, y_ref)        # left end of the first tick
    go(y_line, y_ref)                 # tick 1, drawn right to the line
    for n in range(CYCLES):
        show("Y swing " + str(n + 1) + " of " + str(CYCLES))
        go(y_line, y_ref + Y_SWING)
        go(y_line, y_ref - Y_SWING)
    go(y_line, y_ref)                 # back to reference, moving up
    x, _ = screen_pos()
    go(x + X_TICK, y_ref)             # tick 2, continuing right


home()

# Travel to the start of the X test, arriving moving right (as at the end).
go(x_ref - APPROACH, x_line + Y_TICK)
go(x_ref, x_line + Y_TICK)
pause_for_shake()

show("SLIP CHECK", "X test...")
x_test()

show("Y test...")
# Arrive at the Y test start moving up, the same way the Y test ends.
go(y_line - X_TICK, y_ref - APPROACH)
y_test()

show("Done.", "Do the tick pairs", "line up, or is there", "a step between them?")

print("")
print("=== SLIP CHECK RESULTS ===")
print("CYCLES =", CYCLES, " SPEED =", SPEED)
print("X_SWING =", round(X_SWING), " Y_SWING =", round(Y_SWING),
      " X_TICK =", round(X_TICK), " Y_TICK =", round(Y_TICK))
print("X test: vertical ticks at x =", round(x_ref), " line y =", round(x_line))
print("Y test: horizontal ticks at y =", round(y_ref), " line x =", round(y_line))
print("For each pair: one straight line (no slip), or a step? Measure the step in mm.")
print("Scale: about", round(X_SPAN_DEG / 150), "deg per mm, if the screen is ~150 mm wide.")
print("For reference, my rubber-band drive lost about 22-27 deg per cycle on X and 7-21 on Y; the gear caps lost about 0.")
