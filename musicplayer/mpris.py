import os

try:
    import dbus
    import dbus.service
    import dbus.mainloop.glib
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    _DBUS_AVAILABLE = True
except ImportError:
    _DBUS_AVAILABLE = False

_MPRIS_IFACE  = 'org.mpris.MediaPlayer2'
_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
_PROPS_IFACE  = 'org.freedesktop.DBus.Properties'
_MPRIS_PATH   = '/org/mpris/MediaPlayer2'
_BUS_NAME     = 'org.mpris.MediaPlayer2.openreel'


def _noop(*_a, **_kw):
    pass


def _s(v):
    return dbus.String(v, variant_level=1)

def _b(v):
    return dbus.Boolean(v, variant_level=1)

def _d(v):
    return dbus.Double(v, variant_level=1)

def _i64(v):
    return dbus.Int64(v, variant_level=1)

def _arr(lst, sig='s'):
    return dbus.Array(lst, signature=sig, variant_level=1)

def _meta_dict(d):
    return dbus.Dictionary(d, signature='sv', variant_level=1)


def _no_track_metadata():
    return _meta_dict({
        'mpris:trackid': dbus.ObjectPath(
            '/org/mpris/MediaPlayer2/TrackList/NoTrack'),
    })


class _MPRISImpl(dbus.service.Object):

    def __init__(self, bus_name, on_play_pause, on_next, on_previous, on_stop):
        super().__init__(bus_name, _MPRIS_PATH)
        self._on_play_pause = on_play_pause
        self._on_next       = on_next
        self._on_previous   = on_previous
        self._on_stop       = on_stop

        self._playback_status = 'Stopped'
        self._can_go_next     = False
        self._can_go_previous = False
        self._metadata        = _no_track_metadata()
        self._shuffle         = False
        self._loop_status     = 'None'

    # ------ org.freedesktop.DBus.Properties ------

    @dbus.service.method(_PROPS_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        props = self._all_props(interface)
        if prop not in props:
            raise dbus.exceptions.DBusException(
                f'Property {prop} not found on {interface}',
                name='org.freedesktop.DBus.Error.InvalidArgs',
            )
        return props[prop]

    @dbus.service.method(_PROPS_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        return self._all_props(interface)

    @dbus.service.method(_PROPS_IFACE, in_signature='ssv')
    def Set(self, _interface, _prop, _value):
        pass

    @dbus.service.signal(_PROPS_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    def _all_props(self, interface):
        if interface == _MPRIS_IFACE:
            return {
                'CanQuit':             _b(False),
                'CanRaise':            _b(False),
                'HasTrackList':        _b(False),
                'Identity':            _s('Open Reel'),
                'SupportedUriSchemes': _arr([]),
                'SupportedMimeTypes':  _arr([]),
            }
        if interface == _PLAYER_IFACE:
            return {
                'PlaybackStatus': _s(self._playback_status),
                'Metadata':       self._metadata,
                'CanControl':     _b(True),
                'CanPlay':        _b(True),
                'CanPause':       _b(True),
                'CanSeek':        _b(False),
                'CanGoNext':      _b(self._can_go_next),
                'CanGoPrevious':  _b(self._can_go_previous),
                'Position':       _i64(0),
                'MinimumRate':    _d(1.0),
                'MaximumRate':    _d(1.0),
                'Rate':           _d(1.0),
                'Volume':         _d(1.0),
                'LoopStatus':     _s(self._loop_status),
                'Shuffle':        _b(self._shuffle),
            }
        return {}

    # ------ org.mpris.MediaPlayer2 ------

    @dbus.service.method(_MPRIS_IFACE)
    def Raise(self): pass

    @dbus.service.method(_MPRIS_IFACE)
    def Quit(self): pass

    # ------ org.mpris.MediaPlayer2.Player ------

    @dbus.service.method(_PLAYER_IFACE)
    def Play(self): self._on_play_pause()

    @dbus.service.method(_PLAYER_IFACE)
    def Pause(self): self._on_play_pause()

    @dbus.service.method(_PLAYER_IFACE)
    def PlayPause(self): self._on_play_pause()

    @dbus.service.method(_PLAYER_IFACE)
    def Stop(self): self._on_stop()

    @dbus.service.method(_PLAYER_IFACE)
    def Next(self): self._on_next()

    @dbus.service.method(_PLAYER_IFACE)
    def Previous(self): self._on_previous()

    @dbus.service.method(_PLAYER_IFACE, in_signature='x')
    def Seek(self, _offset): pass

    @dbus.service.method(_PLAYER_IFACE, in_signature='ox')
    def SetPosition(self, _track_id, _position): pass

    @dbus.service.method(_PLAYER_IFACE, in_signature='s')
    def OpenUri(self, _uri): pass

    # ------ update methods called from the window ------

    def set_playback_status(self, status: str):
        self._playback_status = status
        self.PropertiesChanged(
            _PLAYER_IFACE,
            {'PlaybackStatus': _s(status)},
            [],
        )

    def set_shuffle(self, active: bool):
        self._shuffle = active
        self.PropertiesChanged(_PLAYER_IFACE, {'Shuffle': _b(active)}, [])

    def set_loop_status(self, status: str):
        self._loop_status = status
        self.PropertiesChanged(_PLAYER_IFACE, {'LoopStatus': _s(status)}, [])

    def set_track(self, title, artist, album, art_path,
                  track_idx, track_count):
        meta = {
            'mpris:trackid': dbus.ObjectPath(
                f'/org/openreel/track/{track_idx}'),
            'xesam:title':  dbus.String(title  or ''),
            'xesam:artist': dbus.Array(
                [dbus.String(artist or '')], signature='s'),
            'xesam:album':  dbus.String(album  or ''),
        }
        if art_path and os.path.exists(art_path):
            meta['mpris:artUrl'] = dbus.String(f'file://{art_path}')
        self._metadata        = _meta_dict(meta)
        self._can_go_next     = track_idx < track_count - 1
        self._can_go_previous = track_idx > 0
        self.PropertiesChanged(
            _PLAYER_IFACE,
            {
                'Metadata':      self._metadata,
                'CanGoNext':     _b(self._can_go_next),
                'CanGoPrevious': _b(self._can_go_previous),
            },
            [],
        )


class MPRISService:
    """Public facade. All methods are no-ops when D-Bus is unavailable."""

    def __init__(self, on_play_pause=None, on_next=None,
                 on_previous=None, on_stop=None):
        self._impl = None
        if not _DBUS_AVAILABLE:
            return
        try:
            bus      = dbus.SessionBus()
            bus_name = dbus.service.BusName(
                _BUS_NAME, bus=bus, replace_existing=True)
            self._impl = _MPRISImpl(
                bus_name,
                on_play_pause = on_play_pause or _noop,
                on_next       = on_next       or _noop,
                on_previous   = on_previous   or _noop,
                on_stop       = on_stop       or _noop,
            )
        except Exception as e:
            print(f'[mpris] disabled: {e}')
            self._impl = None

    def set_playback_status(self, status: str):
        if self._impl:
            self._impl.set_playback_status(status)

    def set_track(self, title, artist, album, art_path=None,
                  track_idx=0, track_count=0):
        if self._impl:
            self._impl.set_track(
                title, artist, album, art_path, track_idx, track_count)

    def set_shuffle(self, active: bool):
        if self._impl:
            self._impl.set_shuffle(active)

    def set_loop_status(self, status: str):
        if self._impl:
            self._impl.set_loop_status(status)
