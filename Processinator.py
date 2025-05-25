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
# 4. Stretch
# 5. Saturation
# 6. Denoise
#
# bxt, nxt, denoise
# dbe, deconv, spcc
# builder: dbe, light denoise, spcc, cosmic clarity sharpen, stretch, saturation, final denoise
# wileecyte: dbe, deconv, color correction, denoise, separate stars
#
# Future work:
# - heuristics for type of object
# - heuristics for Bortle
# - heuristics for phase of moon
#
from threading import Thread
from time import sleep
import os

INSIDE_SIRIL = True
NAME = "Processinator"

if INSIDE_SIRIL:
    import sirilpy as s
    from sirilpy import tksiril

import sys
import tkinter as tk
from functools import partial
from tkinter import ttk, Frame

if INSIDE_SIRIL:
    s.ensure_installed("ttkthemes")
    s.ensure_installed("opencv-python")

from ttkthemes import ThemedTk
import cv2
import numpy as np

slog = partial(print, f'{NAME}:')

# Function to map each intensity level to output intensity level.
MAX_VALUE = 65535
def pixelVal(pix, r1, s1, r2, s2):
    if 0 <= pix and pix <= r1:
        return (s1 / r1)*pix
    elif r1 < pix and pix <= r2:
        return ((s2 - s1)/(r2 - r1)) * (pix - r1) + s1
    else:
        return ((MAX_VALUE - s2)/(MAX_VALUE - r2)) * (pix - r2) + s2

class Processinator:
    """Processinator."""

    def __init__(self, root: ThemedTk):
        """Initialize."""
        slog("Warming up the coils")
        self.root = root
        self.root.title(NAME)
        self.root.resizable(False, False)
        self.current_file = None
        self.steps = []
        self.width = None
        self.height = None

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

            tksiril.match_theme_to_siril(self.root, self.siril)

        self._create_ui()

    def _create_ui(self):
        """Create the UI."""
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        title = ttk.Label(main, text="Process ALL the images", style="Header.TLabel")
        title.pack(pady=(0, 20))

        # Buttons
        buttons = Frame(main)
        buttons.pack(pady=(0, 10))
        self.close_button = ttk.Button(buttons, text="Quit", command=self._dispose)
        self.close_button.pack(side=tk.LEFT)
        self.process_button = ttk.Button(buttons, text="Process", command=self.process)
        self.process_button.pack(side=tk.RIGHT)

        # Status at bottom of dialog
        self.status = ttk.Label(main, text="Ready", style="Status.TLabel")
        self.status.pack(pady=(0, 0))

        if INSIDE_SIRIL:
            tksiril.create_tooltip(self.close_button, "Quit the application")

    def _dispose(self):
        """Dispose of resources."""
        slog("Shutting down")
        if INSIDE_SIRIL:
            self.siril.disconnect()
        self.root.quit()
        self.root.destroy()

    def _update_status(self, text: str) -> None:
        """Update the status bar."""
        if self.root:
            self.status.config(text=text)
        slog(text)

        if not INSIDE_SIRIL:
            # for debugging only
            sleep(2)

    def process(self):
        """Process the current image."""
        slog(f"Starting to process.")

        if INSIDE_SIRIL:
            self.current_file = self.siril.get_image_filename()

            if self.current_file is None:
                self.siril.error_messagebox("No image selected")
                return

        thread = Thread(target=self.runner)
        thread.start()

    def runner(self):
        try:
            self.close_button["state"] = tk.DISABLED
            self.process_button["state"] = tk.DISABLED
            self.unclip()
            # self.background_extraction()
            # self.plate_solve()
            # self.crop()
            # self.color_calibration()
            # self.star_separation()
            # self.stretch()
            # self.star_recombination()
            # self.remove_green()
            # # self.denoise()
            self.curves()
            self.adjustments()
            # self.sharpen()
            self.save_result()
        finally:
            self.close_button["state"] = tk.NORMAL
            self.process_button["state"] = tk.NORMAL
            self._update_status("Done")

    def unclip(self):
        """Unclip stars."""
        self._update_status("Unclip")

        if INSIDE_SIRIL:
            self.siril.cmd("unclipstars")

        self.steps.append("UC")

    def background_extraction(self):
        """Background extraction."""
        self._update_status("Background extraction")

        if INSIDE_SIRIL:
            self.siril.cmd("subsky",
                           "-rbf",
                           "-dither",
                           "-samples=20",
                           "-tolerance=3.0", # Higher for higher gradient?
                           "-smooth=0.5")

        self.steps.append("BE")

    def plate_solve(self):
        """Plate solve."""
        self._update_status("Plate solve")

        if INSIDE_SIRIL:
            self.siril.cmd("platesolve")
            #  -blindpos, -blindres ?

        self.steps.append("PS")

    def color_calibration(self):
        """Color calibration."""
        self._update_status("Color calibration")

        if INSIDE_SIRIL:
            self.siril.cmd("spcc",
                           "-catalog=gaia",
                           "\"-whiteref=Average Spiral Galaxy\"",
                           "\"-oscsensor=ZWO Seestar S50\"",
                           "\"-oscfilter=UV/IR Block\"")

        self.steps.append("SPCC")

    def crop(self):
        """Crop image."""
        # todo : make this intelligent.  crop based on noise?
        self._update_status("Crop")

        if INSIDE_SIRIL:
            # Get the size of the image, and crop 5% from each side...
            _channels, self.height, self.width = self.siril.get_image_shape()

            pct = 0.07
            h_delta = pct * self.height
            w_delta = pct * self.width

            self.siril.cmd("crop",
                           w_delta,
                           h_delta,
                           self.width - 2 * w_delta,
                           self.height - 2 * h_delta)

        self.steps.append("CR")

    def star_separation(self):
        """Star separation."""
        self._update_status("Star separation")

        if INSIDE_SIRIL:
            self.siril.cmd("starnet", "-stretch")
            self.siril.cmd("save", "starless_result")
            self.siril.cmd("load", "starless_result")

        self.steps.append("StarSep")

    def star_recombination(self):
        """Star recombination."""
        self._update_status("Star recombination")

        if INSIDE_SIRIL:
            if "StarSep" in self.steps:
                # We really should do this a better way here!
                # todo : perhaps a context around processing steps?
                self.siril.cmd("save", "starless_result")

            directory, filename = os.path.split(self.current_file)
            new_filename = "starmask_" + filename
            starmask = os.path.join(directory, new_filename)
            slog(f"Original name '{self.current_file}' new name '{starmask}'")

            self.siril.cmd("load", f'"{starmask}"')
            self.siril.cmd("modasinh", "-human", "-D=7.5")
            self.siril.cmd("save", "starmask_result")
            # Use pixelmath to recombine.
            self.siril.cmd("pm",
                           "\"$starless_result$ + $starmask_result$\"")

        self.steps.append("StarComb")

    def remove_green(self):
        """Remove green."""
        self._update_status("Remove green")

        if INSIDE_SIRIL:
            self.siril.cmd("rmgreen")

        self.steps.append("DG")

    def stretch(self):
        """Stretch the image."""
        self._update_status("Stretch")

        if INSIDE_SIRIL:
            # last parameter is average brightness
            self.siril.cmd("autostretch", "-2.8", "0.20")

        self.steps.append("ST")

    def denoise(self):
        """Denoise."""
        self._update_status("Denoise")

        if INSIDE_SIRIL:
            self.siril.cmd("denoise", "-mod=0.5")

        self.steps.append("DN")

    def sharpen(self):
        """Sharpen."""
        self._update_status("Sharpen")

        if INSIDE_SIRIL:
            self.siril.cmd("pyscript",
                           "CosmicClarity_Sharpen.py")

        self.steps.append("SH")

    def curves(self):
        """Curves."""
        self._update_status("Curves")

        self._save_tiff(self._current_file_name())

        # Apply curve using OpenCV
        img = cv2.imread(f"{self._current_file_name()}.tif")
        slog(f"Image: {img} current file name: {self._current_file_name()}")
        if INSIDE_SIRIL and img is None:
            self.siril.error_messagebox("Failed to load image")
            return
        r1 = 70
        s1 = 0
        r2 = 140
        s2 = 255
        pixelVal_vec = np.vectorize(pixelVal)
        contrast_stretched = pixelVal_vec(img, r1, s1, r2, s2)

        self.steps.append("Curves")

        in_file = f"{self._current_file_name()}.png"
        cv2.imwrite(in_file, contrast_stretched)

        if INSIDE_SIRIL:
            self.siril.cmd("load", in_file)

    def adjustments(self):
        """Perform a variety of adjustments, including CLAHE."""
        self._update_status("Adjustments")

        if INSIDE_SIRIL:
            # Increase saturation a little, and apply CLAHE
            self.siril.cmd("satu", "0.15")
            #self.siril.cmd("clahe", "8", "2")

        self.steps.append("Adj")

    def save_result(self):
        """Save the result file, including step suffix."""
        self._save_state()

    def _current_file_name(self):
        """Return the current file name."""
        file_name = self.current_file.replace(".fit", "")
        file_name = f"{file_name}_{'_'.join(self.steps)}.fit"
        return file_name

    def _save_state(self):
        """Save the current state of the image."""
        if INSIDE_SIRIL:
            file_name = self._current_file_name()

            self._update_status(f"Saving result to {file_name}")
            self.siril.cmd("save", f'"{file_name}"')
        else:
            self._update_status("Saving result")

    def _save_tiff(self, file_name: str):
        """Save the current state of the image."""
        if INSIDE_SIRIL:
            self._update_status(f"Saving tif to {file_name}")
            self.siril.cmd("savetif", f'"{file_name}"', "-deflate")
        else:
            self._update_status("Saving result")

def main():
    try:
        root = ThemedTk()
        app = Processinator(root)
        root.mainloop()
        slog("We're done here")
    except Exception as e:
        slog(f'Error starting app: {e}')
        sys.exit(1)


if __name__ == "__main__":
    main()
