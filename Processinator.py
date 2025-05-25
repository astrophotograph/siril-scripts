#
# Name:        processinator
# Description: Process ALL the things.  Auto and manual flavors.
# Author:      Random Erewhon <erewhon@astrophotography.tv>
#              https://youtube.com/@erewhon42
#
# Version history:
#
# Steps:
# 1. Stack (optionally from stackinator)
# 2. Background Extraction
# 3. Color calibration
# 4. Star Separation (Optional)
#
# bxt, nxt, denoise
# dbe, deconv, spcc
# builder: dbe, light denoise, spcc, cosmic clarity sharpen, stretch, saturation, final denoise
# wileecyte: dbe, deconv, color correction, denoise, separate stars
#
INSIDE_SIRIL = False
NAME = "Processinator"

if INSIDE_SIRIL:
    import sirilpy as s
    from sirilpy import tksiril

import sys
import tkinter as tk
from tkinter import ttk, Frame
from functools import partial

if INSIDE_SIRIL:
    s.ensure_installed("ttkthemes")

from ttkthemes import ThemedTk

slog = partial(print, f'{NAME}:')

class Stackinator:
    """Stackinator."""

    def __init__(self, root: ThemedTk):
        """Initialize."""
        slog("Warming up the coils")
        self.root = root
        # self.root.title("Stackinator")
        self.root.title("Dude, what?")
        self.root.resizable(False, False)

        if INSIDE_SIRIL:
            self.style = tksiril.standard_style()

            self.siril = s.SirilInterface()
            try:
                self.siril.connect()
                slog("Connected to Siril successfully")
            except SirilConnectionError as e:
                print(f'Connection failed: {e}')
                self.siril.error_messagebox('Failed to connect to Siril')
                self.close_dialog()
                raise RuntimeError('Failed to connect to Siril')

        self._create_ui()

        if INSIDE_SIRIL:
            tksiril.match_theme_to_siril(self.root, self.siril)

    def _create_ui(self):
        """Create the UI."""
        main = Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        title = ttk.Label(main, text=NAME, style="Header.TLabel")
        title.pack(pady=(0, 20))

        close = ttk.Button(main, text="Quit", command=self._dispose)
        close.pack(side=tk.LEFT)
        if INSIDE_SIRIL:
            tksiril.create_tooltip(close, "Quit the application")

    def _dispose(self):
        """Dispose of resources."""
        slog("Shutting down")
        if INSIDE_SIRIL:
            self.siril.disconnect()
        self.root.quit()
        self.root.destroy()

    def background_extraction(self):
        """Background extraction."""
        slog("Background extraction")

    def color_calibration(self):
        """Color calibration."""
        slog("Color calibration")

    def star_separation(self):
        """Star separation."""
        slog("Star separation")

    def stack(self):
        """Stack."""

    def star_recombination(self):
        """Star recombination."""

    def remove_green(self):
        """Remove green."""

    def denoise(self):
        """Denoise."""

    def sharpen(self):
        """Sharpen."""


def main():
    try:
        root = ThemedTk()
        app = Stackinator(root)
        root.mainloop()
        slog("We're done here")
    except Exception as e:
        slog(f'Error starting app: {e}')
        sys.exit(1)


if __name__ == "__main__":
    main()

