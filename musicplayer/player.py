import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import enum


class PlayState(enum.Enum):
    STOPPED = 0
    PLAYING = 1
    PAUSED  = 2


class Player:
    """GStreamer playbin with real-time level analysis and gapless playback.

    All callbacks fire on the GLib main thread.
    on_level(left_db, right_db) fires ~every 80 ms while playing.
    on_track_started() fires when a gapless transition completes.
    """

    _LEVEL_INTERVAL_NS = 80 * Gst.MSECOND   # 80 ms in nanoseconds

    def __init__(self, on_state_changed=None, on_position=None,
                 on_error=None, on_track_ended=None, on_level=None,
                 on_track_started=None):
        Gst.init(None)
        self._playbin         = None
        self._state           = PlayState.STOPPED
        self._duration_ns     = 0
        self._current         = None
        self._pos_timer       = None
        self._next_uri        = None
        self._gapless_pending = False

        self._on_state_changed = on_state_changed
        self._on_position      = on_position
        self._on_error         = on_error
        self._on_track_ended   = on_track_ended
        self._on_level         = on_level
        self._on_track_started = on_track_started
        self._volume           = 1.0

    # ------------------------------------------------------------------ #

    def play(self, file_path):
        self._stop_pipeline()
        self._current         = file_path
        self._duration_ns     = 0
        self._next_uri        = None
        self._gapless_pending = False

        self._playbin = Gst.ElementFactory.make('playbin', 'player')
        self._playbin.set_property('uri', Gst.filename_to_uri(file_path))
        self._playbin.set_property('volume', self._volume)

        # Insert audio-level analyser if the plugin is available
        level_filter = self._make_level_filter()
        if level_filter:
            self._playbin.set_property('audio-filter', level_filter)

        bus = self._playbin.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._on_bus_message)

        # Gapless: about-to-finish fires near end of track on streaming thread
        self._playbin.connect('about-to-finish', self._on_about_to_finish)

        self._playbin.set_state(Gst.State.PLAYING)
        self._state = PlayState.PLAYING
        self._fire_state()
        self._start_timer()

    def set_next_uri(self, file_path):
        """Pre-register the next file for gapless playback. Call after each track starts."""
        self._next_uri = Gst.filename_to_uri(file_path) if file_path else None

    def pause(self):
        if self._playbin and self._state == PlayState.PLAYING:
            self._playbin.set_state(Gst.State.PAUSED)
            self._state = PlayState.PAUSED
            self._fire_state()

    def resume(self):
        if self._playbin and self._state == PlayState.PAUSED:
            self._playbin.set_state(Gst.State.PLAYING)
            self._state = PlayState.PLAYING
            self._fire_state()
            self._start_timer()

    def toggle(self):
        if self._state == PlayState.PLAYING:
            self.pause()
        elif self._state == PlayState.PAUSED:
            self.resume()

    def stop(self):
        self._stop_pipeline()
        self._state = PlayState.STOPPED
        self._fire_state()

    def set_volume(self, v: float):
        self._volume = max(0.0, min(1.0, v))
        if self._playbin:
            self._playbin.set_property('volume', self._volume)

    @property
    def volume(self):
        return self._volume

    def seek(self, fraction):
        if self._playbin and self._duration_ns > 0:
            pos = int(max(0.0, min(1.0, fraction)) * self._duration_ns)
            self._playbin.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                pos,
            )

    @property
    def state(self):
        return self._state

    @property
    def current_file(self):
        return self._current

    # ------------------------------------------------------------------ #
    # GStreamer level filter

    def _make_level_filter(self):
        """Return a Gst.Bin that wraps audioconvert + level, or None."""
        try:
            convert = Gst.ElementFactory.make('audioconvert', 'ac')
            level   = Gst.ElementFactory.make('level',        'lv')
            if not convert or not level:
                return None

            level.set_property('message',  True)
            level.set_property('interval', self._LEVEL_INTERVAL_NS)

            bin_ = Gst.Bin.new('level-bin')
            bin_.add(convert)
            bin_.add(level)
            convert.link(level)

            bin_.add_pad(Gst.GhostPad.new('sink', convert.get_static_pad('sink')))
            bin_.add_pad(Gst.GhostPad.new('src',  level.get_static_pad('src')))
            return bin_
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # internals

    def _on_about_to_finish(self, playbin):
        # Runs on GStreamer streaming thread -- only touch the playbin URI, nothing else.
        # Setting uri here causes GStreamer to transition seamlessly without pipeline teardown.
        if self._next_uri:
            playbin.props.uri = self._next_uri
            self._gapless_pending = True

    def _start_timer(self):
        if self._pos_timer:
            GLib.source_remove(self._pos_timer)
        self._pos_timer = GLib.timeout_add(500, self._tick)

    def _tick(self):
        if self._state != PlayState.PLAYING or not self._playbin:
            self._pos_timer = None
            return GLib.SOURCE_REMOVE
        ok_d, dur = self._playbin.query_duration(Gst.Format.TIME)
        ok_p, pos = self._playbin.query_position(Gst.Format.TIME)
        if ok_d and dur > 0:
            self._duration_ns = dur
        if ok_p and self._duration_ns > 0 and self._on_position:
            self._on_position(
                pos / self._duration_ns,
                pos // Gst.SECOND,
                self._duration_ns // Gst.SECOND,
            )
        return GLib.SOURCE_CONTINUE

    def _on_bus_message(self, _bus, message):
        t = message.type
        if t == Gst.MessageType.STREAM_START:
            # Fires at the start of every stream, including gapless transitions.
            # Only act when we know a gapless jump was queued.
            if self._gapless_pending:
                self._gapless_pending = False
                self._duration_ns = 0   # reset so tick() re-queries for new track
                if self._on_track_started:
                    self._on_track_started()
        elif t == Gst.MessageType.EOS:
            # Only fires when there was no next URI set (last track or gapless disabled).
            self._state = PlayState.STOPPED
            self._fire_state()
            if self._on_track_ended:
                self._on_track_ended()
        elif t == Gst.MessageType.ERROR:
            err, _ = message.parse_error()
            self._state = PlayState.STOPPED
            self._fire_state()
            if self._on_error:
                self._on_error(str(err))
        elif t == Gst.MessageType.ELEMENT and self._on_level:
            struct = message.get_structure()
            if struct and struct.get_name() == 'level':
                rms = struct.get_value('rms')
                if rms:
                    left  = rms[0] if len(rms) > 0 else -60.0
                    right = rms[1] if len(rms) > 1 else left
                    self._on_level(left, right)

    def _stop_pipeline(self):
        if self._pos_timer:
            GLib.source_remove(self._pos_timer)
            self._pos_timer = None
        if self._playbin:
            self._playbin.set_state(Gst.State.NULL)
            self._playbin.get_bus().remove_signal_watch()
            self._playbin = None
        self._next_uri        = None
        self._gapless_pending = False

    def _fire_state(self):
        if self._on_state_changed:
            self._on_state_changed(self._state)

    def __del__(self):
        self._stop_pipeline()
