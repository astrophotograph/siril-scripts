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
# - tunable values for different steps, where applicable
#
from pathlib import Path
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
    s.ensure_installed("scipy")

from ttkthemes import ThemedTk
import cv2
import numpy as np
from scipy.interpolate import CubicSpline

slog = partial(print, f'{NAME}:')

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
        self.active_checkbox = None
        
        # Settings variables
        self.save_each_step_var = tk.BooleanVar(value=True)
        
        # Define processing steps configuration
        self.step_configs = [
            {"name": "unclip", "display_name": "Unclip Stars", "default": True},
            {"name": "crop", "display_name": "Crop", "default": True},
            {"name": "background_extraction", "display_name": "Background Extraction", "default": True},
            {"name": "plate_solve", "display_name": "Plate Solve", "default": True},
            {"name": "color_calibration", "display_name": "Color Calibration", "default": True},
            {"name": "star_separation", "display_name": "Star Separation", "default": False},
            {"name": "stretch", "display_name": "Stretch", "default": True},
            {"name": "star_recombination", "display_name": "Star Recombination", "default": False},
            {"name": "remove_green", "display_name": "Remove Green", "default": True},
            {"name": "curves", "display_name": "Curves", "default": True},
            {"name": "adjustments", "display_name": "Adjustments", "default": True},
            {"name": "denoise", "display_name": "Denoise", "default": True},
            {"name": "sharpen", "display_name": "Sharpen", "default": True},
        ]
        
        # Create boolean variables for each step
        self.step_vars = {}
        self.step_checkbuttons = {}  # Dictionary to store checkbox widgets
        for step in self.step_configs:
            self.step_vars[step["name"]] = tk.BooleanVar(value=step["default"])

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

        # Define highlight color
        self.highlight_color = "#4CAF50"  # Green color
        self.normal_color = self.root.cget("background")  # Get the default background color

        title = ttk.Label(main, text="Process ALL the images", style="Header.TLabel")
        title.pack(pady=(0, 20))

        # Settings Frame
        settings_frame = ttk.LabelFrame(main, text="Settings")
        settings_frame.pack(fill=tk.X, expand=False, pady=(0, 10))
        
        # Save each step checkbox
        ttk.Checkbutton(
            settings_frame, 
            text="Save intermediate image after each step",
            variable=self.save_each_step_var
        ).pack(anchor=tk.W, padx=5, pady=5)

        # Processing Steps Frame
        self.steps_frame = ttk.LabelFrame(main, text="Processing Steps")
        self.steps_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Calculate columns based on the number of steps
        columns = 2  # Set number of columns
        
        # Create checkboxes for each step with automatic row/column calculation
        for i, step in enumerate(self.step_configs):
            row = i % (len(self.step_configs) // columns + (1 if len(self.step_configs) % columns > 0 else 0))
            col = i // (len(self.step_configs) // columns + (1 if len(self.step_configs) % columns > 0 else 0))
            
            # Create checkbox with frame for highlighting
            frame = ttk.Frame(self.steps_frame)
            frame.grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            
            # Create the checkbox inside the frame
            cb = ttk.Checkbutton(
                frame, 
                text=step["display_name"], 
                variable=self.step_vars[step["name"]]
            )
            cb.pack(anchor=tk.W)
            
            # Store reference to the checkbox and its frame
            self.step_checkbuttons[step["name"]] = {"checkbox": cb, "frame": frame}

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
            tksiril.create_tooltip(self.process_button, "Start processing the current image")

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

    def _highlight_step(self, step_name):
        """Highlight the checkbox for the current step."""
        if step_name in self.step_checkbuttons:
            # Reset previous highlight if any
            if self.active_checkbox:
                self.step_checkbuttons[self.active_checkbox]["frame"].configure(style="")
            
            # Apply highlight to the current step
            self.step_checkbuttons[step_name]["frame"].configure(style="Highlight.TFrame")
            self.active_checkbox = step_name
            
            # Force update UI
            self.root.update_idletasks()
    
    def _unhighlight_step(self, step_name):
        """Remove highlighting from the checkbox."""
        if step_name in self.step_checkbuttons:
            self.step_checkbuttons[step_name]["frame"].configure(style="")
            if self.active_checkbox == step_name:
                self.active_checkbox = None
            
            # Force update UI
            self.root.update_idletasks()

    def runner(self):
        try:
            self.close_button["state"] = tk.DISABLED
            self.process_button["state"] = tk.DISABLED
            
            # Reset steps list at the beginning of processing
            self.steps = []
            
            # Get the save_each_step value from the checkbox
            self.save_each_step = self.save_each_step_var.get()
            
            # Reset any active highlighting
            if self.active_checkbox:
                self._unhighlight_step(self.active_checkbox)
            
            if self.step_vars["unclip"].get():
                self._highlight_step("unclip")
                self.unclip()
                self._unhighlight_step("unclip")
                
            if self.step_vars["crop"].get():
                self._highlight_step("crop")
                self.crop(0.01)
                self._unhighlight_step("crop")
                
            if self.step_vars["background_extraction"].get():
                self._highlight_step("background_extraction")
                self.background_extraction(tolerance=2.0)
                self._unhighlight_step("background_extraction")
                
            if self.step_vars["plate_solve"].get():
                self._highlight_step("plate_solve")
                self.plate_solve()
                self._unhighlight_step("plate_solve")
                
            if self.step_vars["color_calibration"].get():
                self._highlight_step("color_calibration")
                self.color_calibration()
                self._unhighlight_step("color_calibration")
                
            if self.step_vars["star_separation"].get():
                self._highlight_step("star_separation")
                self.star_separation()
                self._unhighlight_step("star_separation")
                
            if self.step_vars["stretch"].get():
                self._highlight_step("stretch")
                self.stretch()
                self._unhighlight_step("stretch")
                
            if self.step_vars["star_recombination"].get():
                self._highlight_step("star_recombination")
                self.star_recombination(8.5)
                self._unhighlight_step("star_recombination")
                
            if self.step_vars["remove_green"].get():
                self._highlight_step("remove_green")
                self.remove_green()
                self._unhighlight_step("remove_green")
                
            if self.step_vars["curves"].get():
                self._highlight_step("curves")
                self.curves()
                self._unhighlight_step("curves")
                
            if self.step_vars["adjustments"].get():
                self._highlight_step("adjustments")
                self.adjustments()
                self._unhighlight_step("adjustments")
                
            if self.step_vars["denoise"].get():
                self._highlight_step("denoise")
                self.denoise()
                self._unhighlight_step("denoise")
                
            if self.step_vars["sharpen"].get():
                self._highlight_step("sharpen")
                self.sharpen()
                self._unhighlight_step("sharpen")
                
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
        if self.save_each_step:
            self._save_state()

    def background_extraction(self, samples:int = 20, tolerance:float = 3.0, smooth:float = 0.5):
        """Background extraction."""
        self._update_status("Background extraction")

        if INSIDE_SIRIL:
            self.siril.cmd("subsky",
                           "-rbf",
                           "-dither",
                           f"-samples={samples}",
                           f"-tolerance={tolerance}", # Higher for higher gradient?
                           f"-smooth={smooth}")

        self.steps.append("BE")
        if self.save_each_step:
            self._save_state()

    def plate_solve(self):
        """Plate solve."""
        self._update_status("Plate solve")

        if INSIDE_SIRIL:
            self.siril.cmd("platesolve")
            #  -blindpos, -blindres ?

        self.steps.append("PS")
        if self.save_each_step:
            self._save_state()

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
        if self.save_each_step:
            self._save_state()

    def crop(self, pct: float = 0.07):
        """Crop image."""
        # todo : make this intelligent.  crop based on noise?
        self._update_status("Crop")

        if INSIDE_SIRIL:
            # Get the size of the image, and crop 5% from each side...
            _channels, self.height, self.width = self.siril.get_image_shape()

            h_delta = pct * self.height
            w_delta = pct * self.width

            self.siril.cmd("crop",
                           w_delta,
                           h_delta,
                           self.width - 2 * w_delta,
                           self.height - 2 * h_delta)

        self.steps.append("CR")
        if self.save_each_step:
            self._save_state()

    def star_separation(self):
        """Star separation."""
        self._update_status("Star separation")

        if INSIDE_SIRIL:
            self.siril.cmd("starnet", "-stretch")
            self.siril.cmd("save", "starless_result")
            self.siril.cmd("load", "starless_result")

        self.steps.append("StarSep")
        if self.save_each_step:
            self._save_state()

    def star_recombination(self, strength:float = 7.5):
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
            self.siril.cmd("modasinh", "-human", f"-D={strength}")
            self.siril.cmd("save", "starmask_result")
            # Use pixelmath to recombine.
            self.siril.cmd("pm",
                           "\"$starless_result$ + $starmask_result$\"")

        self.steps.append("StarComb")
        if self.save_each_step:
            self._save_state()

    def remove_green(self):
        """Remove green."""
        self._update_status("Remove green")

        if INSIDE_SIRIL:
            self.siril.cmd("rmgreen")

        self.steps.append("DG")
        if self.save_each_step:
            self._save_state()

    def stretch(self, shadows_clip:float = -2.8, target_bg:float = 0.20):
        """Stretch the image."""
        self._update_status("Stretch")

        if INSIDE_SIRIL:
            # last parameter is average brightness
            self.siril.cmd("autostretch", str(shadows_clip), str(target_bg))

        self.steps.append("ST")
        if self.save_each_step:
            self._save_state()

    def denoise(self):
        """Denoise."""
        self._update_status("Denoise")

        if INSIDE_SIRIL:
            # self.siril.cmd("denoise", "-mod=0.5")
            self.steps.append("DN")
            self.siril.cmd("pyscript",
                           "CosmicClarity_Denoise.py")
            if self.save_each_step:
                self._save_state()


    def sharpen(self):
        """Sharpen."""
        self._update_status("Sharpen")

        if INSIDE_SIRIL:
            self.steps.append("SH")
            self.siril.cmd("pyscript",
                           "CosmicClarity_Sharpen.py")
            if self.save_each_step:
                self._save_state()


    def curves(self):
        """Curves."""
        self._update_status("Curves")

        self._save_tiff(self._current_file_name(''))

        # Apply the curve using OpenCV
        img = cv2.imread(self._current_file_name('.tif'), cv2.IMREAD_UNCHANGED)
        if INSIDE_SIRIL and img is None:
            self.siril.error_messagebox("Failed to load image")
            return

        # Get the image data type to preserve it
        original_dtype = img.dtype

        # Convert to float for processing
        img_float = img.astype(np.float32)


        # Normalize to 0-1 range
        min_val = np.min(img_float)
        max_val = np.max(img_float)

        if max_val > min_val:
            normalized = (img_float - min_val) / (max_val - min_val)
        else:
            normalized = img_float

        control_points = [
            (0.0, 0.0),
            (0.07, 0.015), # Pull down shadows
            (0.6, 0.75),   # Boost mid to light mid-tones
            (1.0, 1.0)
        ]
        # Extract x and y values from control points
        x_points = np.array([point[0] for point in control_points])
        y_points = np.array([point[1] for point in control_points])

        # Create cubic spline function
        cs = CubicSpline(x_points, y_points)

        # Apply the spline function to each pixel
        adjusted = cs(normalized)

        # Clip to [0, 1] range
        adjusted = np.clip(adjusted, 0, 1)

        # Scale back to original range
        adjusted = adjusted * (max_val - min_val) + min_val

        # Convert back to original data type
        if original_dtype == np.uint8:
            adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)
        elif original_dtype == np.uint16:
            adjusted = np.clip(adjusted, 0, 65535).astype(np.uint16)
        else:
            adjusted = adjusted.astype(original_dtype)

        self.steps.append("Curves")

        cv2.imwrite(self._current_file_name('.tif'), adjusted)

        if INSIDE_SIRIL:
            self.siril.cmd("load", f'"{self._current_file_name('.tif')}"')

    def adjustments(self):
        """Perform a variety of adjustments, including CLAHE."""
        self._update_status("Adjustments")

        if INSIDE_SIRIL:
            # Increase saturation a little, and apply CLAHE
            self.siril.cmd("satu", "0.15")
            #self.siril.cmd("clahe", "8", "2")

        self.steps.append("Adj")
        if self.save_each_step:
            self._save_state()

    def save_result(self):
        """Save the result file, including step suffix."""
        self._save_state()

    def _current_file_name(self, suffix: str | None = None) -> str:
        """Return the current file name."""
        steps = '_'.join(self.steps)
        input_path = Path(self.current_file)
        extension = suffix if suffix is not None else input_path.suffix
        output_path = input_path.parent / f"{input_path.stem}_{steps}{extension}"
        return str(output_path)

    def _save_state(self):
        """Save the current state of the image."""
        if INSIDE_SIRIL:
            file_name = self._current_file_name()
            base_name = os.path.basename(file_name)

            self._update_status(f"Saving result to {base_name}")
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