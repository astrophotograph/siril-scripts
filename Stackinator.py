# Name:        stackinator
# Description: One stacking script to rule them all. (YMMV)
# Author:      Random Erewhon <erewhon@astrophotography.tv>
#              https://youtube.com/@erewhon42
#
# Version history:
#
# todo:
# -dark=filename, -flat=filename, -cc=dark
#
from threading import Thread
from time import sleep

INSIDE_SIRIL = True
NAME = "Stackinator"

if INSIDE_SIRIL:
    import sirilpy as s
    from sirilpy import tksiril

import sys
import tkinter as tk
from functools import partial
from tkinter import ttk, Frame

if INSIDE_SIRIL:
    s.ensure_installed("ttkthemes")

from ttkthemes import ThemedTk

slog = partial(print, f'{NAME}:')


# todo :
# siril.is_cli - check to run headless!

class Stackinator:
    """Stackinator."""

    def __init__(self, root: ThemedTk):
        """Initialize."""
        slog("Warming up the coils")
        self.root = root
        # self.root.title("Stackinator")
        self.root.title("Dude, what?")
        self.root.resizable(False, False)
        self.status = None

        # Default stacking parameters
        self.drizzle = tk.BooleanVar()
        self.scale = tk.StringVar(value="2.0")  # Changed to StringVar
        self.scales = ["1.0", "2.0", "3.0"]  # Available scale values
        self.pixfrac = "0.5"
        self.min_pairs = tk.StringVar(value="10")  # Changed to StringVar
        self.kernel = tk.StringVar()
        self.kernels = ["square", "point", "turbo", "gaussian", "laczos2", "lanczos3"]
        self.max_stack = tk.BooleanVar()

        self.style = tksiril.standard_style()

        self.siril = s.SirilInterface()
        try:
            self.siril.connect()
            slog("Connected to Siril successfully")
        except SirilConnectionError as e:
            print(f'Connection failed: {e}')
            self.error('Failed to connect to Siril')
            self._dispose()
            raise RuntimeError('Failed to connect to Siril')

        # todo : check for "process" directory and error if it exists!
        tksiril.match_theme_to_siril(self.root, self.siril)

        self._create_ui()

    def error(self, msg: str) -> None:
        """Display an error message."""
        if self.root:
            self.siril.error_messagebox(msg)
        else:
            slog(msg)

    def on_drizzle_change(self):
        """Handle drizzle checkbox change."""
        if self.drizzle.get():
            self.kernel_combo["state"] = tk.NORMAL
            self.scale_combo["state"] = tk.NORMAL
        else:
            self.kernel_combo["state"] = tk.DISABLED
            self.scale_combo["state"] = tk.DISABLED

    def _create_ui(self):
        """Create the UI."""
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        title = ttk.Label(main,
                          text=NAME,
                          # width=30,
                          justify=tk.CENTER,
                          font=("Arial", 24, "bold"))
        title.pack(pady=(0, 20))

        # Create Drizzle LabelFrame
        drizzle_frame = ttk.LabelFrame(main, text="Drizzle", padding=10)
        drizzle_frame.pack(fill=tk.X, padx=5, pady=5)

        # Drizzle checkbox inside the LabelFrame
        drizzle_cb = ttk.Checkbutton(drizzle_frame,
                                     text="Enable Drizzle",
                                     variable=self.drizzle,
                                     onvalue=True,
                                     offvalue=False,
                                     command=self.on_drizzle_change)
        drizzle_cb.grid(row=0, column=0, sticky=tk.W, pady=5)
        self.drizzle.set(True)

        # Scale dropdown inside the LabelFrame
        scale_label = ttk.Label(drizzle_frame, text="Scale:")
        scale_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        self.scale_combo = ttk.Combobox(drizzle_frame, values=self.scales, 
                                       textvariable=self.scale, width=5)
        self.scale_combo.grid(row=1, column=1, sticky=tk.W, pady=2)

        # Kernel dropdown inside the LabelFrame
        kernel_label = ttk.Label(drizzle_frame, text="Kernel:")
        kernel_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.kernel_combo = ttk.Combobox(drizzle_frame, values=self.kernels)
        self.kernel_combo.grid(row=2, column=1, sticky=tk.W, pady=2)
        self.kernel_combo.current(0)
        self.kernel_combo.bind("<<ComboboxSelected>>", lambda _: self.kernel.set(self.kernel_combo.get()))
        self.kernel.set(self.kernels[0])
        self.kernel.trace_add("write", lambda *_: self.kernel_combo.set(self.kernel.get()))
        self.kernel_combo.config(textvariable=self.kernel)
        self.kernel_combo.config(width=10)

        # Create Settings LabelFrame
        settings_frame = ttk.LabelFrame(main, text="Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)

        # Min pairs numeric entry inside the Settings LabelFrame
        min_pairs_label = ttk.Label(settings_frame, text="Min Pairs:")
        min_pairs_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        min_pairs_spinbox = ttk.Spinbox(settings_frame, from_=1, to=100, 
                                        textvariable=self.min_pairs, width=5)
        min_pairs_spinbox.grid(row=0, column=1, sticky=tk.W, pady=2)

        # Buttons
        buttons = ttk.Frame(main)
        buttons.pack(pady=(10, 10))
        self.stack_button = ttk.Button(buttons, text="Stack", command=self.process_sequence)
        self.stack_button.pack(side=tk.RIGHT)

        self.close_button = ttk.Button(buttons, text="Quit", command=self._dispose)
        self.close_button.pack(side=tk.LEFT)

        # Status at bottom of dialog
        self.status = ttk.Label(main, text="Ready", style="Status.TLabel")
        self.status.pack(pady=(0, 0))

        tksiril.create_tooltip(self.stack_button, "Start stacking")
        tksiril.create_tooltip(self.close_button, "Quit the application")
        tksiril.create_tooltip(min_pairs_spinbox, "Minimum number of star pairs to use for alignment")
        tksiril.create_tooltip(self.scale_combo, "Image scale factor for drizzle")
        tksiril.create_tooltip(self.kernel_combo, "Kernel type for drizzle")

    def _update_status(self, text: str) -> None:
        """Update the status bar."""
        if self.root:
            self.status.config(text=text)
        slog(text)

    def process_sequence(self):
        """Stack subframes."""
        slog(
            f"Starting to stack. drizzle={self.drizzle.get()} scale={self.scale.get()} pixfrac={self.pixfrac} min_pairs={self.min_pairs.get()} kernel={self.kernel.get()}")

        thread = Thread(target=self.runner)
        thread.start()

    def runner(self):
        try:
            self.close_button["state"] = tk.DISABLED
            self.stack_button["state"] = tk.DISABLED
            self.conversion()
            self.calibration()
            self.registration()
            self.stack()
            self.finalize_stack()
        finally:
            self.close_button["state"] = tk.NORMAL
            self.stack_button["state"] = tk.NORMAL
            self._update_status("Done")

    def _dispose(self):
        """Dispose of resources."""
        slog("Shutting down")
        self.siril.disconnect()
        self.root.quit()
        self.root.destroy()

    def conversion(self):
        """Convert subframes."""
        self._update_status("Convert subframes")

        self.siril.cmd("set32bits")
        # Convert light frames to .FIT files
        self.siril.cmd("cd", "lights")
        self.siril.cmd("link", "light", "-out=../process")
        self.siril.cmd("cd", "../process")

    def calibration(self):
        """Calibration subframes."""
        self._update_status("Calibrate subframes")

        # Calibrate light frames
        self.siril.cmd("setfindstar",
                       "-sigma=0.1",
                       "-roundness=0.42",  # Should make this a bit tighter!
                       "-convergence=3")
        calibrate_args = ["-debayer"]
        if self.drizzle.get():
            calibrate_args = [
                "-cfa",
                "-equalize_cfa"
            ]
        self.siril.cmd("calibrate", "light", *calibrate_args)

    def registration(self):
        """Registration of subframes."""
        #
        # Align lights with Drizzle 2x.
        #   scale is image scale factor.  default 1.0
        #   pixfrac sets pixel fraction.  default 1.0
        #   DRIZZLE kernel options: square, point, turbo, gaussian, laczos2, lanczos3
        #
        self._update_status("Register subframes")

        self.siril.cmd("register",
                       "pp_light",
                       "-2pass",
                       f"-minpairs={self.min_pairs.get()}")
        seq_args = []
        if self.drizzle.get():
            seq_args = [
                "-drizzle",
                f"-scale={self.scale.get()}",
                f"-pixfrac={self.pixfrac}",
                f"-kernel={self.kernel.get()}",
            ]
        self.siril.cmd("seqapplyreg",
                       "pp_light",
                       "-filter-round=2.5k",
                       *seq_args)

    def stack(self):
        """Stack subframes."""
        self._update_status("Stack subframes")

        self.siril.cmd("stack", "r_pp_light",
                       "rej", "3", "3",
                       "-norm=addscale",
                       "-output_norm",
                       "-rgb_equal",
                       "-out=result")

    def finalize_stack(self):
        """Finish stacking."""
        self._update_status("Finish stacking")

        # Flip if required
        self.siril.cmd("mirrorx_single", "result")

        # Save to a different name
        self.siril.cmd("load", "result")

        self.siril.cmd("cd", "..")


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