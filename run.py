#!/usr/bin/env python3
"""Development entry point. Run from this directory: python run.py"""
import sys
from musicplayer.main import MusicPlayerApp

app = MusicPlayerApp()
sys.exit(app.run(sys.argv))
