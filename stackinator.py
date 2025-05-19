# Name:        stackinator
# Description: One stacking script to rule them all. (YMMV)
# Author:      Random Erewhon <erewhon@astrophotography.tv>
#              https://youtube.com/@erewhon42
#
# Version history:
#
from threading import Thread

INSIDE_SIRIL = False
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
        self.scale = "2.0"
        self.pixfrac = "0.5"
        self.min_pairs = "10"
        self.kernel = tk.StringVar()
        self.kernels = ["square", "point", "turbo", "gaussian", "laczos2", "lanczos3"]
        self.max_stack = tk.BooleanVar()

        if INSIDE_SIRIL:
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

        self._create_ui()

        if INSIDE_SIRIL:
            tksiril.match_theme_to_siril(self.root, self.siril)

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
        else:
            self.kernel_combo["state"] = tk.DISABLED

    def _create_ui(self):
        """Create the UI."""
        main = Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        title = ttk.Label(main,
                          text=NAME,
                          # width=30,
                          justify=tk.CENTER,
                          font=("Arial", 24, "bold"))
        title.pack(pady=(0, 20))

        # Parameters
        drizzle = tk.Checkbutton(main,
                                 text="Drizzle",
                                 variable=self.drizzle,
                                 height=2,
                                 width=10,
                                 onvalue=True,
                                 offvalue=False,
                                 command=self.on_drizzle_change
                                 )
        drizzle.pack(pady=(0, 20))
        self.drizzle.set(True)

        kernel_box = Frame(main)
        kernel_label = ttk.Label(kernel_box, text="Kernel")
        kernel_label.pack(side=tk.LEFT)
        self.kernel_combo = ttk.Combobox(kernel_box, values=self.kernels)
        self.kernel_combo.pack(side=tk.RIGHT)
        self.kernel_combo.current(0)
        self.kernel_combo.bind("<<ComboboxSelected>>", lambda _: self.kernel.set(self.kernel_combo.get()))
        self.kernel.set(self.kernels[0])
        self.kernel.trace_add("write", lambda *_: self.kernel_combo.set(self.kernel.get()))
        self.kernel_combo.config(textvariable=self.kernel)
        # self.kernel_combo.config(state="readonly")
        self.kernel_combo.config(width=10)
        # self.kernel_combo.config(height=2)
        # self.kernel_combo.config(justify=tk.CENTER)
        # self.kernel_combo.config(font=("Arial", 12))
        # self.kernel_combo.config(exportselection=0)
        kernel_box.pack(pady=(0, 10))

        # Buttons
        buttons = Frame(main)
        buttons.pack(pady=(0, 10))
        self.stack_button = ttk.Button(buttons, text="Stack", command=self.process_sequence)
        self.stack_button.pack(side=tk.RIGHT)

        self.close_button = ttk.Button(buttons, text="Quit", command=self._dispose)
        self.close_button.pack(side=tk.LEFT)

        # Status at bottom of dialog
        self.status = ttk.Label(main, text="Ready", style="Status.TLabel")
        self.status.pack(pady=(0, 0))

        if INSIDE_SIRIL:
            tksiril.create_tooltip(self.stack_button, "Start stacking")
            tksiril.create_tooltip(self.close_button, "Quit the application")

    def _update_status(self, text: str) -> None:
        """Update the status bar."""
        if self.root and INSIDE_SIRIL:
            self.status.config(text=text)
        else:
            slog(text)

    def process_sequence(self):
        """Stack subframes."""
        slog(
            f"Starting to stack. drizzle={self.drizzle.get()} scale={self.scale} pixfrac={self.pixfrac} min_pairs={self.min_pairs} kernel={self.kernel.get()}")

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
        if INSIDE_SIRIL:
            self.siril.disconnect()
        self.root.quit()
        self.root.destroy()

    def conversion(self):
        """Convert subframes."""
        self._update_status("Convert subframes")

        if INSIDE_SIRIL:
            self.siril.cmd("set32bits")
            # Convert light frames to .FIT files
            self.siril.cmd("cd", "lights")
            self.siril.cmd("link", "light", "-out=../process")
            self.siril.cmd("cd", "../process")

    def calibration(self):
        """Calibration subframes."""
        self._update_status("Calibrate subframes")

        if INSIDE_SIRIL:
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

        if INSIDE_SIRIL:
            self.siril.cmd("register",
                           "pp_light",
                           "-2pass",
                           f"-minpairs={self.min_pairs}")
            seq_args = []
            if self.drizzle.get():
                seq_args = [
                    "-drizzle",
                    f"-scale={self.scale}",
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

        if INSIDE_SIRIL:
            self.siril.cmd("stack", "r_pp_light",
                           "rej", "3", "3",
                           "-norm=addscale",
                           "-output_norm",
                           "-rgb_equal",
                           "-out=result")

    def finalize_stack(self):
        """Finish stacking."""
        self._update_status("Finish stacking")

        if INSIDE_SIRIL:
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
