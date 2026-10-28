"""Shared hardware and helpers for the Etch A Sketch plotter."""

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, TouchSensor
from pybricks.parameters import Port, Button
from pybricks.tools import wait, StopWatch

# ---- Hardware -------------------------------------------------------------
ev3 = EV3Brick()
x_motor = Motor(Port.A)        # horizontal knob
y_motor = Motor(Port.B)        # vertical knob
x_button = TouchSensor(Port.S1)
y_button = TouchSensor(Port.S2)
clock = StopWatch()

# ---- Calibration (calibrate.py, 40T gear caps, 2026-10-23) ----------------
X_SPAN_DEG = 1657    # edge to edge, average of 9 sweeps (spread 85)
Y_SPAN_DEG = 1181    # edge to edge, average of 10 sweeps (spread 47)
# (band drive was X 4361 / Y 3143)
X_BACKLASH = 28      # deg the X knob turns after a reversal before the stylus
                     # moves (L2 ladder said 30; L4 circle notches showed
                     # 30 over-corrects by ~2, so trimmed to 28)
Y_BACKLASH = 37      # same for Y (ladder 45 -> l2_check 40 -> L4 circle notches
                     # showed 40 over-corrects by ~4, so trimmed to 37)
BACKLASH_ON = True   # goto() corrects for backlash; measuring tests turn this off
SHAKE_PAUSE = False  # True: stop before drawing so I can shake the screen clean.
                     # False (default): go straight from homing to drawing; the
                     # travel line from the home corner stays on the screen.
EDGE_MARGIN = 0.05   # keep drawings 5% in from every edge, so the stylus
                     # never reaches an edge where the knob would slip

# ---- Settings -------------------------------------------------------------
JOG_SLOW = 150       # deg/s for the first part of a hold, for fine positioning
JOG_FAST = 300       # deg/s once the hold goes on longer (was 500; slower for the gears)
SLOW_MS = 800        # how long a hold stays slow
TAP_MAX_MS = 300     # a press shorter than this counts as a tap
DOUBLE_GAP_MS = 400  # second press must start this soon after the tap ends
DRAW_SPEED = 300     # deg/s along the longer axis when drawing a line
TAKEUP_SPEED = 300   # deg/s when taking up backlash (the stylus doesn't move)
PATH_ACCEL = 1000    # deg/s^2: how fast draw_path speeds up and slows down
TICK_MS = 10         # draw_path updates the motor targets this often

ARROWS = (Button.UP, Button.DOWN, Button.LEFT, Button.RIGHT)


def show(*lines):
    """Print to the PC and to the brick's screen."""
    ev3.screen.clear()
    for line in lines:
        print(line)
        ev3.screen.print(line)


class Jog:
    """Hold a touch sensor to turn a motor. Double-press flips direction."""

    def __init__(self, name, motor, button, beep_pitch):
        self.name = name
        self.motor = motor
        self.button = button
        self.beep_pitch = beep_pitch
        self.direction = 1          # 1 = clockwise, -1 = counter-clockwise
        self.was_pressed = False
        self.press_start = 0
        self.last_tap_end = None
        self.last_sign = None       # which way the motor last turned
        self.turns = []             # angle at the start and at every reversal

    def mark_turn(self):
        """Record the current angle as a turning point and report the sweep."""
        angle = self.motor.angle()
        self.turns.append(angle)
        if len(self.turns) > 1:
            sweep = abs(angle - self.turns[-2])
            print(self.name, "sweep", len(self.turns) - 1, ":", sweep, "deg")

    def sweeps(self):
        """Lengths of each travel between turning points, in degrees."""
        return [abs(b - a) for a, b in zip(self.turns, self.turns[1:])]

    def update(self, now):
        pressed = self.button.pressed()

        if pressed and not self.was_pressed:
            # Second half of a double-press? Then flip direction.
            if self.last_tap_end is not None and now - self.last_tap_end < DOUBLE_GAP_MS:
                self.direction = -self.direction
                self.last_tap_end = None
                turn = "clockwise" if self.direction == 1 else "counter-clockwise"
                print(self.name, turn)
                pitch = self.beep_pitch if self.direction == 1 else self.beep_pitch // 2
                ev3.speaker.beep(pitch, 80)
            self.press_start = now

        elif self.was_pressed and not pressed:
            quick = now - self.press_start < TAP_MAX_MS
            self.last_tap_end = now if quick else None

        if pressed:
            # Moving the other way from last time? That was a turning point.
            if self.direction != self.last_sign:
                self.mark_turn()
                self.last_sign = self.direction
            held = now - self.press_start
            speed = JOG_SLOW if held < SLOW_MS else JOG_FAST
            self.motor.run(speed * self.direction)
        else:
            self.motor.stop()

        self.was_pressed = pressed


x_jog = Jog("X", x_motor, x_button, beep_pitch=1000)
y_jog = Jog("Y", y_motor, y_button, beep_pitch=1500)


def jog_until_arrow():
    """Let me jog with the touch sensors until I press an arrow on the brick."""
    while not any(b in ev3.buttons.pressed() for b in ARROWS):
        now = clock.time()
        x_jog.update(now)
        y_jog.update(now)
        wait(10)
    x_motor.stop()
    y_motor.stop()
    ev3.speaker.beep(1200, 100)
    while ev3.buttons.pressed():   # wait for release
        wait(10)


def wait_for_touch():
    """Wait for a press and release of either touch sensor (no motor moves)."""
    while not (x_button.pressed() or y_button.pressed()):
        wait(10)
    while x_button.pressed() or y_button.pressed():
        wait(10)
    ev3.speaker.beep(1200, 100)


def wait_for_go():
    """Wait for a press and release of a touch sensor OR a brick arrow.
    (Not the centre button: that's Pybricks' stop button.)"""
    def pressed():
        return (x_button.pressed() or y_button.pressed() or
                any(b in ev3.buttons.pressed() for b in ARROWS))
    while not pressed():
        wait(10)
    while pressed():
        wait(10)
    ev3.speaker.beep(1200, 100)


# Which motor direction moves the stylus right / up.
# Gears (dir_check.py): X clockwise = RIGHT, Y clockwise = DOWN.
# (Band drive was the opposite: x_sign -1, y_sign 1.)
x_sign = 1
y_sign = -1
APPROACH = 60    # deg: come at a start point from this far back, to take up backlash
                 # (was 150 with bands; gears need ~2.6x fewer degrees for the same travel)


# Backlash bookkeeping, in screen degrees (right, up):
# pos  = where the stylus is (where we last sent it).
# take = slack currently taken up: the backlash after moving right/up,
#        0 after moving left/down (homing always ends moving left/down).
# Motor angle = sign * (pos + take).
pos = [0, 0]
take = [0, 0]


def home():
    """Jog to the bottom-left corner, press an arrow. That point is (0, 0).
    Finish with each knob moving TOWARD the corner (left, down)."""
    show("HOME", "Jog to BOTTOM-LEFT", "corner, stop at", "the edges.",
         "Then press an arrow.")
    jog_until_arrow()
    x_motor.reset_angle(0)
    y_motor.reset_angle(0)
    pos[0], pos[1] = 0, 0
    take[0], take[1] = 0, 0
    print("Homed. Right = motor sign", x_sign, " Up = motor sign", y_sign,
          " Backlash correction:", "ON" if BACKLASH_ON else "OFF")


def goto(x, y, speed=DRAW_SPEED):
    """Straight line to screen position (x, y): degrees right and up from home.
    If an axis reverses, first turn its knob through the backlash (the stylus
    stays put), then draw the line."""
    backlash = (X_BACKLASH, Y_BACKLASH) if BACKLASH_ON else (0, 0)
    new_take = [take[0], take[1]]
    for i, target in ((0, x), (1, y)):
        if target > pos[i]:
            new_take[i] = backlash[i]     # moving right/up
        elif target < pos[i]:
            new_take[i] = 0               # moving left/down
    if new_take != take:
        move_to(x_sign * (pos[0] + new_take[0]), y_sign * (pos[1] + new_take[1]),
                TAKEUP_SPEED)
    move_to(x_sign * (x + new_take[0]), y_sign * (y + new_take[1]), speed)
    pos[0], pos[1] = x, y
    take[0], take[1] = new_take[0], new_take[1]


def screen_pos():
    """Current stylus position in screen degrees (right, up), allowing for
    the slack taken up."""
    return (x_sign * x_motor.angle() - take[0],
            y_sign * y_motor.angle() - take[1])


def pause_for_shake():
    """Beep and wait while I shake the screen clean, then a touch sensor or
    an arrow to carry on. Does nothing unless SHAKE_PAUSE is True."""
    if not SHAKE_PAUSE:
        return
    ev3.speaker.beep(800, 200)
    show("Shake the screen", "clean, then press", "a touch sensor", "or an ARROW.",
         "(Not the centre:", "it stops the program)")
    wait_for_go()


def move_to(x, y, speed=DRAW_SPEED):
    """Straight line to (x, y) in motor degrees: both axes finish together."""
    dx = abs(x - x_motor.angle())
    dy = abs(y - y_motor.angle())
    longest = max(dx, dy)
    if longest < 1:
        return
    # Scale each axis's speed so they arrive at the same moment.
    x_speed = max(speed * dx / longest, 10)
    y_speed = max(speed * dy / longest, 10)
    x_motor.run_target(x_speed, x, wait=False)
    y_motor.run_target(y_speed, y, wait=False)
    while not (x_motor.done() and y_motor.done()):
        wait(5)


# ---- Continuous drawing -----------------------------------------------------

def _needed_take(x, y, from_x, from_y):
    """Slack each axis must have taken up to move from (from_x, from_y) to (x, y)."""
    backlash = (X_BACKLASH, Y_BACKLASH) if BACKLASH_ON else (0, 0)
    new_take = [take[0], take[1]]
    for i, target, start in ((0, x, from_x), (1, y, from_y)):
        if target > start:
            new_take[i] = backlash[i]
        elif target < start:
            new_take[i] = 0
    return new_take


def _distance_at(t, length, speed):
    """Distance along a stretch after t seconds: speed up, cruise, slow down."""
    ramp = speed / PATH_ACCEL                  # seconds to reach full speed
    if length < speed * ramp:                  # too short to reach full speed
        ramp = (length / PATH_ACCEL) ** 0.5
        speed = PATH_ACCEL * ramp
    cruise = (length - speed * ramp) / speed   # seconds at full speed
    if t < ramp:
        return 0.5 * PATH_ACCEL * t * t
    if t < ramp + cruise:
        return 0.5 * speed * ramp + speed * (t - ramp)
    t_end = t - ramp - cruise
    if t_end < ramp:
        return length - 0.5 * PATH_ACCEL * (ramp - t_end) ** 2
    return length


def _follow(points, speed):
    """Glide through points (screen deg, starting at pos) without stopping.
    No axis may reverse within points; take stays as it is."""
    # Cumulative distance to each point
    dist = [0.0]
    px, py = pos[0], pos[1]
    for x, y in points:
        dist.append(dist[-1] + ((x - px) ** 2 + (y - py) ** 2) ** 0.5)
        px, py = x, y
    length = dist[-1]
    if length < 0.5:
        return
    path = [(pos[0], pos[1])] + list(points)
    timer = StopWatch()
    k = 0                                      # current segment
    while True:
        s = _distance_at(timer.time() / 1000, length, speed)
        while k < len(points) - 1 and dist[k + 1] < s:
            k += 1
        seg = dist[k + 1] - dist[k]
        f = 0 if seg == 0 else min(1, (s - dist[k]) / seg)
        x = path[k][0] + f * (path[k + 1][0] - path[k][0])
        y = path[k][1] + f * (path[k + 1][1] - path[k][1])
        x_motor.track_target(x_sign * (x + take[0]))
        y_motor.track_target(y_sign * (y + take[1]))
        if s >= length:
            break
        wait(TICK_MS)
    # Let both motors settle on the last point, then hold there.
    for _ in range(30):
        ex = abs(x_motor.angle() - x_sign * (x + take[0]))
        ey = abs(y_motor.angle() - y_sign * (y + take[1]))
        if ex < 2 and ey < 2:
            break
        wait(TICK_MS)
    x_motor.hold()
    y_motor.hold()
    pos[0], pos[1] = points[-1][0], points[-1][1]


def draw_path(points, speed=DRAW_SPEED):
    """Draw through a list of (x, y) screen points without stopping between
    them. Only pauses where a knob reverses, to take up its backlash."""
    stretch = []
    last_x, last_y = pos[0], pos[1]
    for x, y in points:
        new_take = _needed_take(x, y, last_x, last_y)
        if new_take != take:
            _follow(stretch, speed)            # draw up to the reversal
            stretch = []
            # Turn the reversing knob through its slack; the stylus stays put.
            move_to(x_sign * (pos[0] + new_take[0]), y_sign * (pos[1] + new_take[1]),
                    TAKEUP_SPEED)
            take[0], take[1] = new_take[0], new_take[1]
        stretch.append((x, y))
        last_x, last_y = x, y
    _follow(stretch, speed)
