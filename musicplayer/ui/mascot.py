import math
import enum
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib


class GazeTarget(enum.Enum):
    CENTER     = ( 0.00,  0.00)
    RIGHT      = ( 0.55,  0.00)
    FAR_RIGHT  = ( 0.65,  0.25)
    DOWN_RIGHT = ( 0.30,  0.55)
    DOWN       = ( 0.00,  0.55)


def _rgb(hex_color: str):
    """Convert '#RRGGBB' to (r, g, b) floats."""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


class MascotWidget(Gtk.DrawingArea):
    """The Deck: reel-to-reel mascot with animated eyes, spinning reels,
    and stereo VU bar meters. Colours adapt to the active theme."""

    _PEAK_DECAY = 0.022

    # Default to Technics Blue palette
    _DEFAULT_BG     = '#091422'
    _DEFAULT_BORDER = '#1E5099'
    _DEFAULT_ACCENT = '#378ADD'

    def __init__(self):
        super().__init__()
        self._gaze_x    = 0.0
        self._gaze_y    = 0.0
        self._tgt_x     = 0.0
        self._tgt_y     = 0.0
        self._eye_timer = None

        self._reel_angle = 0.0
        self._spinning   = False
        self._spin_timer = None

        self._vu_left    = 0.0
        self._vu_right   = 0.0
        self._peak_left  = 0.0
        self._peak_right = 0.0
        self._vu_timer   = None

        self._apply_palette(self._DEFAULT_BG, self._DEFAULT_BORDER, self._DEFAULT_ACCENT)
        self.set_draw_func(self._draw, None)

    # ------------------------------------------------------------------ #
    # public API

    def set_theme_colors(self, bg: str, border: str, accent: str, eye: str = None):
        self._apply_palette(bg, border, accent, eye)
        self.queue_draw()

    def set_gaze(self, target: GazeTarget):
        tx, ty = target.value
        if abs(tx - self._tgt_x) < 0.02 and abs(ty - self._tgt_y) < 0.02:
            return
        self._tgt_x = tx
        self._tgt_y = ty
        if not self._eye_timer:
            self._eye_timer = GLib.timeout_add(16, self._animate_eyes)

    def set_spinning(self, spinning: bool):
        self._spinning = spinning
        if spinning and not self._spin_timer:
            self._spin_timer = GLib.timeout_add(40, self._animate_reels)
        elif not spinning and self._spin_timer:
            GLib.source_remove(self._spin_timer)
            self._spin_timer = None
            self.queue_draw()

    def set_vu_levels(self, left_db: float, right_db: float):
        min_db = -60.0
        self._vu_left  = max(0.0, min(1.0, (left_db  - min_db) / abs(min_db)))
        self._vu_right = max(0.0, min(1.0, (right_db - min_db) / abs(min_db)))
        if self._vu_left  > self._peak_left:  self._peak_left  = self._vu_left
        if self._vu_right > self._peak_right: self._peak_right = self._vu_right
        if not self._vu_timer:
            self._vu_timer = GLib.timeout_add(50, self._decay_peaks)
        self.queue_draw()

    def reset_vu(self):
        self._vu_left = self._vu_right = 0.0
        self._peak_left = self._peak_right = 0.0
        self.queue_draw()

    # ------------------------------------------------------------------ #
    # palette

    def _apply_palette(self, bg: str, border: str, accent: str, eye: str = None):
        self._c_bg         = _rgb(bg)
        self._c_border     = _rgb(border)
        self._c_accent     = _rgb(accent)
        self._c_eye_socket = _rgb(eye) if eye else self._c_accent
        # reel fill: bg lightened a bit
        self._c_reel   = tuple(min(1.0, c * 2.2) for c in self._c_bg)
        # accent dimmed for trough
        self._c_trough = tuple(c * 0.25 for c in self._c_accent)
        # peak dot: accent brightened
        self._c_peak   = tuple(min(1.0, c * 1.4) for c in self._c_accent)

    # ------------------------------------------------------------------ #
    # animation

    def _animate_eyes(self):
        dx = self._tgt_x - self._gaze_x
        dy = self._tgt_y - self._gaze_y
        if abs(dx) < 0.015 and abs(dy) < 0.015:
            self._gaze_x = self._tgt_x
            self._gaze_y = self._tgt_y
            self._eye_timer = None
            self.queue_draw()
            return GLib.SOURCE_REMOVE
        self._gaze_x += dx * 0.18
        self._gaze_y += dy * 0.18
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _animate_reels(self):
        self._reel_angle = (self._reel_angle + 0.08) % (2 * math.pi)
        self.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _decay_peaks(self):
        changed = False
        if self._peak_left  > 0:
            self._peak_left  = max(0.0, self._peak_left  - self._PEAK_DECAY)
            changed = True
        if self._peak_right > 0:
            self._peak_right = max(0.0, self._peak_right - self._PEAK_DECAY)
            changed = True
        if changed:
            self.queue_draw()
        if self._peak_left == 0.0 and self._peak_right == 0.0:
            self._vu_timer = None
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    # ------------------------------------------------------------------ #
    # drawing

    def _draw(self, _area, cr, w, h, _data):
        # Scale so the body fills ~90% of height, centred horizontally
        s  = min(w, h) / 90.0
        cx = w / 2
        cy = h / 2

        # Outer body
        bw, bh = 90*s, 72*s
        self._rrect(cr, cx - bw/2, cy - bh/2, bw, bh, 8*s)
        cr.set_source_rgb(*self._c_bg)
        cr.fill_preserve()
        cr.set_source_rgb(*self._c_border)
        cr.set_line_width(2*s)
        cr.stroke()

        # Reels (upper half)
        reel_y = cy - 12*s
        for rx in (cx - 22*s, cx + 22*s):
            self._draw_reel(cr, rx, reel_y, 16*s, s)

        # Face panel (lower half)
        fp_w, fp_h = 60*s, 26*s
        self._rrect(cr, cx - fp_w/2, cy + 2*s, fp_w, fp_h, 4*s)
        r, g, b = self._c_bg
        cr.set_source_rgb(r*0.7, g*0.7, b*0.7)
        cr.fill_preserve()
        cr.set_source_rgba(*self._c_border, 0.5)
        cr.set_line_width(1*s)
        cr.stroke()

        # Eyes
        eye_y = cy + 12*s
        for ex in (cx - 10*s, cx + 10*s):
            self._draw_eye(cr, ex, eye_y, 6*s, 3*s, s)

        # VU bars (mouth)
        self._draw_vu(cr, cx, cy, s)

    def _draw_reel(self, cr, cx, cy, r, s):
        cr.arc(cx, cy, r, 0, 2*math.pi)
        cr.set_source_rgb(*self._c_reel)
        cr.fill_preserve()
        cr.set_source_rgb(*self._c_border)
        cr.set_line_width(1.5*s)
        cr.stroke()
        for i in range(3):
            a = self._reel_angle + i * (2*math.pi / 3)
            cr.move_to(cx + math.cos(a)*5*s, cy + math.sin(a)*5*s)
            cr.line_to(cx + math.cos(a)*(r-2*s), cy + math.sin(a)*(r-2*s))
            cr.set_source_rgb(*self._c_accent)
            cr.set_line_width(1.5*s)
            cr.stroke()
        cr.arc(cx, cy, 4*s, 0, 2*math.pi)
        cr.set_source_rgb(*self._c_bg)
        cr.fill()
        cr.arc(cx, cy, 1.5*s, 0, 2*math.pi)
        cr.set_source_rgb(*self._c_accent)
        cr.fill()

    def _draw_eye(self, cr, cx, cy, socket_r, pupil_r, s):
        travel = socket_r - pupil_r - 0.5*s
        cr.arc(cx, cy, socket_r, 0, 2*math.pi)
        cr.set_source_rgb(*self._c_eye_socket)
        cr.fill()
        px = cx + self._gaze_x * travel
        py = cy + self._gaze_y * travel
        cr.arc(px, py, pupil_r, 0, 2*math.pi)
        cr.set_source_rgb(0.02, 0.04, 0.07)
        cr.fill()
        cr.arc(px - pupil_r*0.3, py - pupil_r*0.3, pupil_r*0.35, 0, 2*math.pi)
        cr.set_source_rgba(1, 1, 1, 0.6)
        cr.fill()

    def _draw_vu(self, cr, cx, cy, s):
        bar_w      = 5*s
        bar_gap    = 3*s
        bar_bottom = cy + 34*s
        bar_max_h  = 12*s

        for side, level, peak in (
            (-1, self._vu_left,  self._peak_left),
            ( 1, self._vu_right, self._peak_right),
        ):
            bx = cx - bar_gap/2 - bar_w if side == -1 else cx + bar_gap/2

            bar_h = max(1.5*s, level * bar_max_h)

            # Trough
            cr.rectangle(bx, bar_bottom - bar_max_h, bar_w, bar_max_h)
            cr.set_source_rgba(*self._c_trough, 0.8)
            cr.fill()

            # Level fill -- theme accent colour
            cr.rectangle(bx, bar_bottom - bar_h, bar_w, bar_h)
            cr.set_source_rgb(*self._c_accent)
            cr.fill()

            # Peak dot
            if peak > 0.02:
                peak_y = bar_bottom - peak * bar_max_h - 1.5*s
                cr.rectangle(bx, peak_y, bar_w, 1.5*s)
                cr.set_source_rgb(*self._c_peak)
                cr.fill()

    @staticmethod
    def _rrect(cr, x, y, w, h, r):
        cr.new_path()
        cr.arc(x+r,     y+r,     r, math.pi,       3*math.pi/2)
        cr.arc(x+w-r,   y+r,     r, 3*math.pi/2,   0)
        cr.arc(x+w-r,   y+h-r,   r, 0,              math.pi/2)
        cr.arc(x+r,     y+h-r,   r, math.pi/2,      math.pi)
        cr.close_path()
