#!/usr/bin/env python3
"""
image_converter_ui.py

Purpose:
  Provides a graphical user interface (GUI) for converting PNG images to
  WebP format using the backend logic from `image_converter.py`.

Description:
  This script launches a Tkinter-based GUI application. Users can:
  - Browse and select a folder containing PNG images.
  - Initiate the conversion process for all PNGs in that folder.
  - View real-time status messages, logs of converted/failed/skipped files,
    and a summary in a scrollable text area.
  The actual image conversion is performed by `image_converter.py`, which
  must be in the same directory. The UI runs the conversion in a separate
  thread to remain responsive.

Dependencies:
  - Python 3.x
  - Tkinter (usually included with Python)
  - Pillow (Python Imaging Library, required by `image_converter.py`)
  - `image_converter.py` (must be in the same directory or accessible via PYTHONPATH)

Usage:
  python image_converter_ui.py
  Or, if executable permissions are set on a Unix-like system:
  ./image_converter_ui.py
"""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import os # For os.path.isdir

# Attempt to import backend logic and exceptions
try:
    from image_converter import (
        convert_png_to_webp_in_folder,
        MissingDependencyError,
        InvalidFolderPathError,
        FolderPermissionError,
        ConversionPipelineError # Base for broader catches if needed
    )
    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False
    # Define dummy exceptions if backend is not available, so UI can still run (partially)
    class ConversionPipelineError(Exception): pass
    class MissingDependencyError(ConversionPipelineError): pass
    class InvalidFolderPathError(ConversionPipelineError): pass
    class FolderPermissionError(ConversionPipelineError): pass


class ImageConverterApp:
    """
    Main application class for the PNG to WebP Tkinter UI.

    Manages UI elements, user interactions, and communication with the
    backend image conversion logic.
    """
    def __init__(self, root_window):
        """
        Initializes the ImageConverterApp.

        Args:
            root_window (tk.Tk): The main Tkinter root window.
        """
        self.root = root_window
        self.root.title("PNG to WebP Converter")
        self.root.geometry("600x450") # Increased height slightly for more log space

        self.folder_path = tk.StringVar()
        self.is_converting = False # To prevent multiple conversions at once

        # --- UI Frames ---
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Folder selection frame
        folder_frame = ttk.Labelframe(main_frame, text="Input Folder", padding="10")
        folder_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)

        # Conversion controls frame (for convert button)
        controls_frame = ttk.Frame(main_frame, padding="5")
        controls_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0,10))
        # Center the button in this frame
        controls_frame.columnconfigure(0, weight=1)


        # Status area frame
        status_frame = ttk.Labelframe(main_frame, text="Status & Log", padding="10")
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        main_frame.columnconfigure(0, weight=1) # Allow status frame to expand
        main_frame.rowconfigure(2, weight=1)    # Allow status frame to expand


        # --- Widgets ---
        # Folder selection
        ttk.Label(folder_frame, text="Selected Folder:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.folder_display_entry = ttk.Entry(folder_frame, textvariable=self.folder_path, state="readonly", width=60)
        self.folder_display_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.browse_button = ttk.Button(folder_frame, text="Browse...", command=self._select_folder)
        self.browse_button.grid(row=0, column=2, sticky=tk.E)

        # Conversion button
        self.convert_button = ttk.Button(controls_frame, text="Convert to WebP", command=self._start_conversion, state="disabled")
        self.convert_button.grid(row=0, column=0, pady=5) # Centered due to controls_frame config

        # TODO: Add a Checkbutton here for "Delete original PNG files" in a future step.
        # self.delete_originals_var = tk.BooleanVar()
        # self.delete_originals_checkbox = ttk.Checkbutton(
        #     controls_frame,
        #     text="Delete original PNG files after conversion",
        #     variable=self.delete_originals_var
        # )
        # self.delete_originals_checkbox.grid(row=1, column=0, pady=5, sticky=tk.W)


        # Status/Log area
        self.status_text_area = scrolledtext.ScrolledText(status_frame, wrap=tk.WORD, state="disabled", height=12) # Increased height
        self.status_text_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        if not BACKEND_AVAILABLE:
            self._log_message("CRITICAL ERROR: Backend 'image_converter.py' not found.\n"
                              "UI is running in a non-functional mode.\n"
                              "Please ensure 'image_converter.py' is in the same directory.")
        else:
            self._log_message("Welcome to the PNG to WebP Converter!\nPlease select a folder to begin.")


    def _select_folder(self):
        """
        Opens a dialog for the user to select a folder.
        Updates the UI with the selected path and enables the convert button.
        """
        if self.is_converting:
            self._log_message("Info: Cannot change folder during an active conversion process.")
            return

        directory = filedialog.askdirectory(title="Select Folder Containing PNG Images")
        if directory:
            self.folder_path.set(directory)
            if BACKEND_AVAILABLE: # Only enable if backend can actually do something
                self.convert_button.config(state="normal")
            self._log_message(f"Selected folder: {directory}")
        else:
            if not self.folder_path.get(): # Disable convert button if path is now empty
                 self.convert_button.config(state="disabled")
            self._log_message("Info: Folder selection cancelled or no folder chosen.")

    def _start_conversion(self):
        """
        Initiates the image conversion process.
        It validates the selected path, disables relevant UI elements,
        and starts the `_conversion_worker` in a new thread.
        """
        if not BACKEND_AVAILABLE:
            self._log_message("Error: Backend script 'image_converter.py' is not available. Cannot perform conversion.")
            return

        if self.is_converting:
            self._log_message("Info: Conversion already in progress. Please wait.")
            return
        
        selected_path = self.folder_path.get()
        if not selected_path or not os.path.isdir(selected_path):
            self._log_message("Error: Please select a valid folder first using the 'Browse...' button.")
            self.convert_button.config(state="disabled")
            return

        self.is_converting = True
        self.convert_button.config(state="disabled")
        self.browse_button.config(state="disabled")
        # self.delete_originals_checkbox.config(state="disabled") # TODO: When implemented

        self._log_message(f"\nStarting conversion for folder: {selected_path}")
        self._log_message("-------------------------------------------------")
        
        # Run conversion in a separate thread to keep UI responsive
        conversion_thread = threading.Thread(
            target=self._conversion_worker,
            args=(selected_path, False) # False for delete_originals
        )
        conversion_thread.start()

    def _conversion_worker(self, folder_path_str, delete_originals_flag):
        """
        Worker function that runs the image conversion in a separate thread.
        Calls the backend `convert_png_to_webp_in_folder` function and
        schedules UI updates on the main thread via `self.root.after()`.

        Args:
            folder_path_str (str): The path to the folder to process.
            delete_originals_flag (bool): Flag indicating whether to delete originals
                                          (passed to backend, currently a placeholder).
        """
        try:
            results = convert_png_to_webp_in_folder(folder_path_str, delete_originals_flag)
            self.root.after(0, self._update_ui_with_results, results)
        except MissingDependencyError as e:
            error_msg = (
                f"Critical Error: Missing Pillow library.\nDetails: {e}\n"
                "Please install it by running: python -m pip install Pillow"
            )
            self.root.after(0, self._log_message, error_msg)
        except InvalidFolderPathError as e:
            self.root.after(0, self._log_message, f"Configuration Error: {e}")
        except FolderPermissionError as e:
            self.root.after(0, self._log_message, f"Folder Permission Error: {e}")
        except ConversionPipelineError as e: # Catch other backend errors
            self.root.after(0, self._log_message, f"Conversion Pipeline Error: {e}")
        except Exception as e: # Catch any other unexpected errors
            self.root.after(0, self._log_message, f"An unexpected error occurred: {e}\nType: {type(e).__name__}")
        finally:
            self.root.after(0, self._re_enable_buttons_after_conversion)

    def _update_ui_with_results(self, results):
        """
        Updates the ScrolledText widget with detailed results from the conversion.
        This method is scheduled to run on the main UI thread by `_conversion_worker`.

        Args:
            results (dict): The results dictionary returned by
                            `convert_png_to_webp_in_folder`.
        """
        self._log_message("-------------------------------------------------")
        self._log_message("Conversion process finished.")

        if results['successful']:
            self._log_message(f"\nSuccessfully converted ({len(results['successful'])} files):")
            for orig, new in results['successful']:
                self._log_message(f"  - '{orig}' -> '{new}'")
        
        if results['failed']:
            self._log_message(f"\nFailed conversions ({len(results['failed'])} files):")
            for fname, err_msg in results['failed']:
                self._log_message(f"  - '{fname}': {err_msg}")

        if results['skipped']:
            self._log_message(f"\nSkipped items ({len(results['skipped'])}):")
            for fname, reason in results['skipped']:
                self._log_message(f"  - '{fname}': {reason}")
        
        self._log_message(f"\n--- Summary ---")
        self._log_message(f"Successful: {len(results['successful'])}")
        self._log_message(f"Failed:     {len(results['failed'])}")
        self._log_message(f"Skipped:    {len(results['skipped'])}")
        self._log_message("-------------------------------------------------")

    def _re_enable_buttons_after_conversion(self):
        """
        Re-enables UI elements (Browse and Convert buttons) after the
        conversion attempt is complete. Sets `is_converting` to False.
        This method is scheduled to run on the main UI thread.
        """
        self.is_converting = False
        self.browse_button.config(state="normal")
        # self.delete_originals_checkbox.config(state="normal") # TODO: When implemented
        
        # Only re-enable convert button if the path is still valid
        current_path = self.folder_path.get()
        if current_path and os.path.isdir(current_path) and BACKEND_AVAILABLE:
            self.convert_button.config(state="normal")
        else:
            self.convert_button.config(state="disabled")
            if not BACKEND_AVAILABLE:
                 self._log_message("Note: Convert button remains disabled as backend is not available.")
            elif not (current_path and os.path.isdir(current_path)):
                 self._log_message("Note: Convert button remains disabled as current path is no longer valid.")


    def _log_message(self, message):
        """Appends a message to the ScrolledText widget."""
        if not hasattr(self, 'status_text_area'): # UI not fully initialized
            print(f"DEBUG (pre-UI log): {message}")
            return
            
        self.status_text_area.config(state="normal")
        self.status_text_area.insert(tk.END, message + "\n")
        self.status_text_area.see(tk.END) # Scroll to the end
        self.status_text_area.config(state="disabled") # Disable again


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageConverterApp(root)
    root.mainloop()
