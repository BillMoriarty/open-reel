"""CSS template. Call get_css(theme_dict) to get the full stylesheet
with all colours substituted in from the chosen theme."""

from musicplayer.themes import THEMES, DEFAULT_THEME


def get_css(t: dict | None = None) -> str:
    if t is None:
        t = THEMES[DEFAULT_THEME]
    return f"""
@define-color window_bg_color        {t['window_bg']};
@define-color window_fg_color        {t['fg']};
@define-color accent_color           {t['accent']};
@define-color card_bg_color          {t['card_bg']};
@define-color card_fg_color          {t['fg']};
@define-color view_bg_color          {t['window_bg']};
@define-color view_fg_color          {t['fg']};
@define-color dialog_bg_color        {t['card_bg']};
@define-color popover_bg_color       {t['card_bg']};

/* ---- global font ---- */
* {{
    font-family: monospace, monospace;
}}

/* ---- window background ---- */
window, .background {{
    background-color: {t['window_bg']};
    color: {t['fg']};
}}

/* ---- our header bar only (scoped to avoid leaking into system dialogs) ---- */
.main-header {{
    background-color: {t['header_bg']};
    color: {t['fg']};
    border-bottom: 1px solid {t['border']};
    box-shadow: none;
}}

.main-header .title {{
    color: {t['fg']};
    font-weight: bold;
    letter-spacing: 2px;
}}

/* ---- search entry inside our header ---- */
.main-header searchentry,
.main-header entry {{
    background-color: {t['input_bg']};
    color: {t['fg']};
    border: 1px solid {t['border']};
    border-radius: 4px;
    caret-color: {t['accent']};
}}

.main-header searchentry:focus,
.main-header entry:focus {{
    border-color: {t['accent']};
    box-shadow: 0 0 0 2px alpha({t['accent']}, 0.25);
}}

searchentry text {{
    color: {t['fg']};
}}

/* ---- buttons (scoped to our main window to avoid polluting system dialogs) ---- */
.music-player-main button {{
    background-color: {t['input_bg']};
    color: {t['fg']};
    border: 1px solid {t['border']};
    border-radius: 5px;
}}

.music-player-main button:hover {{
    background-color: {t['hover_bg']};
    border-color: {t['accent']};
}}

.music-player-main button.suggested-action {{
    background-color: {t['accent_dark']};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1px;
}}

.music-player-main button.suggested-action:hover {{
    background-color: {t['accent']};
}}

/* ---- scrolled window / viewport ---- */
scrolledwindow, viewport, .scrollable {{
    background-color: {t['window_bg']};
}}

scrollbar {{
    background-color: {t['header_bg']};
}}

scrollbar slider {{
    background-color: {t['border']};
    border-radius: 4px;
    min-width: 6px;
    min-height: 6px;
}}

scrollbar slider:hover {{
    background-color: {t['accent']};
}}

/* ---- grid view ---- */
gridview {{
    background-color: {t['window_bg']};
    padding: 12px;
}}

gridview > child {{
    background-color: transparent;
    padding: 0;
    margin: 0;
    border-radius: 8px;
}}

gridview > child:selected {{
    background-color: transparent;
}}

/* ---- album card ---- */
.album-card {{
    background-color: {t['card_bg']};
    border-radius: 8px;
    padding: 10px;
    margin: 6px;
    border: 1px solid {t['card_border']};
    transition: background-color 120ms ease;
}}

.album-card:hover {{
    background-color: {t['hover_bg']};
    border-color: {t['accent']};
}}

.album-card-playing {{
    border-color: {t['accent']};
    border-width: 2px;
    background-color: {t['hover_bg']};
    box-shadow: 0 0 0 1px alpha({t['accent']}, 0.4), 0 0 14px alpha({t['accent']}, 0.18);
}}

.album-title {{
    color: {t['fg']};
    font-size: 12px;
    font-weight: bold;
}}

.album-artist {{
    color: {t['fg_dim']};
    font-size: 11px;
}}

.album-subtitle {{
    color: {t['accent']};
    font-size: 10px;
}}

/* ---- album card play button (hover overlay) ---- */
button.album-play-btn {{
    background-color: alpha({t['accent']}, 0.82);
    color: {t['fg']};
    border: none;
    border-radius: 50%;
    padding: 6px;
    min-width: 34px;
    min-height: 34px;
}}

button.album-play-btn:hover {{
    background-color: {t['accent']};
}}

/* ---- art placeholder ---- */
.art-placeholder {{
    background-color: {t['art_bg']};
    border-radius: 4px;
}}

/* ---- onboarding ---- */
.onboarding-box {{
    background-color: {t['window_bg']};
}}

.onboarding-title {{
    color: {t['fg']};
    font-size: 26px;
    font-weight: bold;
    letter-spacing: 3px;
}}

.onboarding-subtitle {{
    color: {t['fg_dim']};
    font-size: 14px;
}}

.onboarding-note {{
    color: {t['fg_muted']};
    font-size: 12px;
}}

/* ---- progress / scanning ---- */
.scanning-box {{
    background-color: {t['window_bg']};
}}

.scanning-title {{
    color: {t['fg']};
    font-size: 18px;
    font-weight: bold;
    letter-spacing: 2px;
}}

progressbar {{
    padding: 0;
}}

progressbar trough {{
    background-color: {t['input_bg']};
    border: 1px solid {t['border']};
    border-radius: 4px;
    min-height: 10px;
}}

progressbar progress {{
    background-color: {t['accent']};
    border-radius: 4px;
    min-height: 10px;
}}

.progress-label {{
    color: {t['fg_muted']};
    font-size: 11px;
}}

/* ---- track list ---- */
.track-listbox {{
    background-color: {t['window_bg']};
}}

.track-listbox row {{
    background-color: {t['window_bg']};
    color: {t['fg']};
    border-bottom: 1px solid {t['card_border']};
}}

.track-listbox row:hover {{
    background-color: {t['hover_bg']};
}}

.track-listbox row:selected {{
    background-color: {t['playing_bg']};
}}

.track-number {{
    color: {t['fg_muted']};
    font-size: 12px;
}}

.track-title {{
    color: {t['fg']};
    font-size: 13px;
}}

.track-duration {{
    color: {t['fg_muted']};
    font-size: 12px;
}}

.track-playing .track-title {{
    color: {t['fg']};
    font-weight: bold;
}}

.track-playing .track-number {{
    color: {t['fg']};
}}

/* ---- labels ---- */
label {{
    color: {t['fg']};
}}

/* ---- paned split -- hide drag handle, show as a plain border line ---- */
paned.main-split > separator {{
    min-width: 1px;
    background-color: {t['border']};
    border: none;
    padding: 0;
}}

/* ---- left panel (mascot home) ---- */
.left-panel {{
    background-color: {t['header_bg']};
}}

.left-album-info {{
    background-color: {t['header_bg']};
    border-top: 1px solid {t['border']};
    padding: 0;
}}

.left-art-wrap {{
    border-radius: 6px;
}}

.left-now-playing-badge {{
    color: {t['accent']};
    font-size: 9px;
    font-weight: bold;
    letter-spacing: 1.5px;
    margin-bottom: 2px;
}}

.left-album-title {{
    color: {t['fg']};
    font-size: 13px;
    font-weight: bold;
}}

.left-album-artist {{
    color: {t['fg_dim']};
    font-size: 11px;
}}

.left-album-genre {{
    color: {t['accent']};
    font-size: 9px;
    letter-spacing: 1px;
    margin-top: 2px;
}}

.header-album-title {{
    color: {t['fg']};
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 1px;
}}

/* ---- now-playing bar ---- */
.now-playing-bar {{
    background-color: {t['header_bg']};
    border-top: 1px solid {t['border']};
    padding: 8px 12px;
}}

.now-playing-title {{
    color: {t['fg']};
    font-size: 13px;
    font-weight: bold;
}}

.now-playing-artist {{
    color: {t['fg_dim']};
    font-size: 11px;
}}

.now-playing-time {{
    color: {t['fg_muted']};
    font-size: 11px;
}}

.now-playing-scrubber {{
    min-height: 12px;
}}

.now-playing-scrubber trough {{
    background-color: {t['border']};
    border-radius: 3px;
    min-height: 4px;
}}

.now-playing-scrubber highlight {{
    background-color: {t['accent']};
    border-radius: 3px;
}}

.now-playing-scrubber slider {{
    background-color: {t['fg']};
    border-radius: 50%;
    min-width: 14px;
    min-height: 14px;
    margin: 0;
}}

/* ---- now-playing jump button ---- */
.now-playing-jump-btn {{
    padding: 2px 6px;
    border-radius: 6px;
}}

.now-playing-jump-btn:hover {{
    background-color: {t['hover_bg']};
}}

/* ---- notes pane ---- */
.notes-section-title {{
    color: {t['fg']};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

.notes-art-thumb {{
    border-radius: 4px;
}}

.notes-context {{
    color: {t['fg_muted']};
    font-size: 11px;
}}

.note-has-content {{
    color: {t['note_dot']};
    font-size: 10px;
}}

.notes-text {{
    background-color: {t['note_bg']};
    color: {t['fg']};
    font-size: 13px;
}}

.notes-text text {{
    background-color: {t['note_bg']};
    color: {t['fg']};
}}

.notes-placeholder {{
    color: {t['note_placeholder']};
    font-size: 12px;
    font-style: italic;
}}

.notes-context {{
    color: {t['fg_muted']};
    font-size: 11px;
}}

.notes-context-sub {{
    color: {t['fg']};
    font-size: 12px;
    font-weight: bold;
}}

/* ---- view-mode tab bar ---- */
.album-grid-outer {{
    background-color: {t['window_bg']};
}}

.view-tab-group {{
    background-color: {t['window_bg']};
}}

.view-tab-btn {{
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 0;
    border: 1px solid {t['border']};
    background-color: {t['input_bg']};
    color: {t['fg_dim']};
    letter-spacing: 0.5px;
}}

.view-tab-btn:hover {{
    background-color: {t['hover_bg']};
    color: {t['fg']};
}}

.view-tab-btn:checked {{
    background-color: {t['playing_bg']};
    color: {t['fg']};
    border-color: {t['accent']};
}}

/* ---- shuffle / repeat active state ---- */
button.mode-btn:checked,
button.mode-btn.active-mode {{
    color: {t['accent']};
    background-color: alpha({t['accent']}, 0.15);
    border-color: alpha({t['accent']}, 0.4);
}}

/* ---- repeat-one badge ---- */
.repeat-one-badge {{
    font-size: 9px;
    font-weight: bold;
    color: inherit;
    margin-bottom: 4px;
}}

/* ---- volume scale in now-playing bar ---- */
.volume-scale {{
    min-height: 12px;
}}

.volume-scale trough {{
    background-color: {t['border']};
    border-radius: 3px;
    min-height: 3px;
}}

.volume-scale highlight {{
    background-color: {t['fg_dim']};
    border-radius: 3px;
}}

.volume-scale slider {{
    background-color: {t['fg']};
    border-radius: 50%;
    min-width: 10px;
    min-height: 10px;
    margin: 0;
}}

/* ---- prefs / theme chips ---- */
.theme-chip {{
    border-radius: 8px;
    padding: 10px 14px;
    border: 1px solid {t['border']};
    background-color: {t['card_bg']};
}}

.theme-chip:hover {{
    border-color: {t['accent']};
    background-color: {t['hover_bg']};
}}

.theme-chip-selected {{
    border-color: {t['accent']};
    border-width: 2px;
    background-color: {t['hover_bg']};
}}

.theme-chip-name {{
    color: {t['fg']};
    font-size: 12px;
    font-weight: bold;
}}
"""


# Legacy constant kept so any import of styles.CSS still works during transition.
# Remove once all callers use get_css().
CSS = get_css()
