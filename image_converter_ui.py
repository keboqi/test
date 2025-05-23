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
        convert_images_in_folder,
        MissingDependencyError,
        InvalidFolderPathError,
        FolderPermissionError,
        ConversionPipelineError,
        SUPPORTED_OPEN_FORMATS, # Import the new list
        SUPPORTED_SAVE_FORMATS  # Import the new list
    )
    BACKEND_AVAILABLE = True
    # Use actual supported formats if backend is available
    # Fallback to common formats if the imported lists are empty (e.g. Pillow is missing but backend script somehow imported)
    UI_SOURCE_FORMATS = SUPPORTED_OPEN_FORMATS if SUPPORTED_OPEN_FORMATS else ['WEBP', 'PNG', 'JPEG', 'BMP', 'GIF', 'TIFF'] 
    UI_DEST_FORMATS = SUPPORTED_SAVE_FORMATS if SUPPORTED_SAVE_FORMATS else ['WEBP', 'PNG', 'JPEG', 'BMP', 'GIF', 'TIFF']

except ImportError:
    BACKEND_AVAILABLE = False
    # Define dummy exceptions and format lists if backend is not available
    class ConversionPipelineError(Exception): pass
    class MissingDependencyError(ConversionPipelineError): pass
    class InvalidFolderPathError(ConversionPipelineError): pass
    class FolderPermissionError(ConversionPipelineError): pass
    # Fallback format lists for UI when backend is completely unavailable
    SUPPORTED_OPEN_FORMATS = ['WEBP', 'PNG', 'JPEG', 'BMP', 'GIF', 'TIFF'] 
    SUPPORTED_SAVE_FORMATS = ['WEBP', 'PNG', 'JPEG', 'BMP', 'GIF', 'TIFF']
    UI_SOURCE_FORMATS = SUPPORTED_OPEN_FORMATS
    UI_DEST_FORMATS = SUPPORTED_SAVE_FORMATS


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
        self.root.title("Image Format Converter") # Updated title
        self.root.geometry("600x550") # Increased height for format options

        self.folder_path = tk.StringVar()
        self.source_format_var = tk.StringVar()
        self.dest_format_var = tk.StringVar()
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

        # Format options frame
        format_frame = ttk.Labelframe(main_frame, text="Format Options", padding="10")
        format_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0,10))
        format_frame.columnconfigure(1, weight=1)
        format_frame.columnconfigure(3, weight=1)


        # Conversion controls frame (for convert button)
        controls_frame = ttk.Frame(main_frame, padding="5")
        controls_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0,10))
        controls_frame.columnconfigure(0, weight=1) # Center the button

        # Status area frame
        status_frame = ttk.Labelframe(main_frame, text="Status & Log", padding="10")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        main_frame.columnconfigure(0, weight=1) 
        main_frame.rowconfigure(3, weight=1) # Allow status frame to expand


        # --- Widgets ---
        # Folder selection
        ttk.Label(folder_frame, text="Selected Folder:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.folder_display_entry = ttk.Entry(folder_frame, textvariable=self.folder_path, state="readonly", width=50) # Adjusted width
        self.folder_display_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.browse_button = ttk.Button(folder_frame, text="Browse...", command=self._select_folder)
        self.browse_button.grid(row=0, column=2, sticky=tk.E)

        # Format Selection
        # Values are now set using UI_SOURCE_FORMATS and UI_DEST_FORMATS from the top
        
        ttk.Label(format_frame, text="Source Format:").grid(row=0, column=0, padx=(0,5), pady=5, sticky=tk.W)
        self.source_format_combo = ttk.Combobox(
            format_frame, textvariable=self.source_format_var, values=UI_SOURCE_FORMATS, state="readonly", width=10
        )
        self.source_format_combo.grid(row=0, column=1, padx=(0,10), pady=5, sticky=(tk.W, tk.E))
        # Default selection for source format
        if UI_SOURCE_FORMATS:
            default_source = "PNG" if "PNG" in UI_SOURCE_FORMATS else UI_SOURCE_FORMATS[0]
            self.source_format_var.set(default_source)
        self.source_format_combo.bind("<<ComboboxSelected>>", self._update_button_states_handler)


        ttk.Label(format_frame, text="Destination Format:").grid(row=0, column=2, padx=(5,5), pady=5, sticky=tk.W)
        self.dest_format_combo = ttk.Combobox(
            format_frame, textvariable=self.dest_format_var, values=UI_DEST_FORMATS, state="readonly", width=10
        )
        self.dest_format_combo.grid(row=0, column=3, pady=5, sticky=(tk.W, tk.E))
        # Default selection for destination format
        if UI_DEST_FORMATS:
            default_dest = "WEBP" if "WEBP" in UI_DEST_FORMATS else UI_DEST_FORMATS[0]
            self.dest_format_var.set(default_dest)
        self.dest_format_combo.bind("<<ComboboxSelected>>", self._update_button_states_handler)

        # Conversion button
        self.convert_button = ttk.Button(controls_frame, text="Convert Images", command=self._start_conversion, state="disabled") # Updated text
        self.convert_button.grid(row=0, column=0, pady=5)

        # TODO: Add a Checkbutton here for "Delete original files" in a future step.
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
            self._log_message("Welcome to the Image Format Converter!\n"
                              "Please select a folder and desired formats to begin.")
        self._update_button_states()


    def _update_button_states_handler(self, event=None):
        """Handles Combobox selection events to update button states."""
        self._update_button_states()

    def _update_button_states(self):
        """
        Enables or disables the convert button based on whether a folder and
        both source and destination formats are selected.
        """
        folder_selected = bool(self.folder_path.get() and os.path.isdir(self.folder_path.get()))
        source_format_selected = bool(self.source_format_var.get())
        dest_format_selected = bool(self.dest_format_var.get())

        if BACKEND_AVAILABLE and folder_selected and source_format_selected and dest_format_selected:
            self.convert_button.config(state="normal")
        else:
            self.convert_button.config(state="disabled")


    def _select_folder(self):
        """
        Opens a dialog for the user to select a folder.
        Updates the UI with the selected path and calls _update_button_states.
        """
        if self.is_converting:
            self._log_message("Info: Cannot change folder during an active conversion process.")
            return

        directory = filedialog.askdirectory(title="Select Folder Containing Images") # Updated title
        if directory:
            self.folder_path.set(directory)
            self._log_message(f"Selected folder: {directory}")
        else:
            self._log_message("Info: Folder selection cancelled or no folder chosen.")
        self._update_button_states()


    def _start_conversion(self):
        """
        Initiates the image conversion process.
        Validates selected path and formats, disables relevant UI elements,
        and starts the `_conversion_worker` in a new thread.
        """
        if not BACKEND_AVAILABLE:
            self._log_message("Error: Backend script 'image_converter.py' is not available. Cannot perform conversion.")
            return

        if self.is_converting:
            self._log_message("Info: Conversion already in progress. Please wait.")
            return
        
        selected_path = self.folder_path.get()
        source_format = self.source_format_var.get()
        dest_format = self.dest_format_var.get()

        if not selected_path or not os.path.isdir(selected_path):
            self._log_message("Error: Please select a valid folder first using the 'Browse...' button.")
            self._update_button_states() # Re-check to disable convert if path became invalid
            return
        
        if not source_format:
            self._log_message("Error: Please select a source image format.")
            return
        if not dest_format:
            self._log_message("Error: Please select a destination image format.")
            return
        
        if source_format.lower() == dest_format.lower():
            self._log_message(f"Info: Source and destination formats ('{source_format}') are the same. No conversion needed for these files.")
            # Optionally, could choose to proceed and let backend skip, or just stop here.
            # For now, let's allow it, backend will skip if files are already in dest format.

        self.is_converting = True
        self.convert_button.config(state="disabled")
        self.browse_button.config(state="disabled")
        self.source_format_combo.config(state="disabled")
        self.dest_format_combo.config(state="disabled")
        # self.delete_originals_checkbox.config(state="disabled") # TODO: When implemented

        self._log_message(f"\nStarting conversion in folder: {selected_path}") # Slightly rephrased
        self._log_message(f"Task: Convert from {source_format.upper()} to {dest_format.upper()}") # More explicit
        self._log_message("-------------------------------------------------")
        
        # Run conversion in a separate thread to keep UI responsive
        conversion_thread = threading.Thread(
            target=self._conversion_worker,
            args=(selected_path, source_format, dest_format, False) # False for delete_originals
        )
        conversion_thread.start()

    def _conversion_worker(self, folder_path_str, source_format_str, dest_format_str, delete_originals_flag):
        """
        Worker function that runs the image conversion in a separate thread.
        Calls the backend `convert_images_in_folder` function and
        schedules UI updates on the main thread via `self.root.after()`.

        Args:
            folder_path_str (str): The path to the folder to process.
            source_format_str (str): The source image format.
            dest_format_str (str): The destination image format.
            delete_originals_flag (bool): Flag indicating whether to delete originals.
        """
        try:
            # Call the updated backend function
            results = convert_images_in_folder(
                folder_path_str, 
                source_format_str, 
                dest_format_str, 
                delete_originals_flag
            )
            # Pass source and dest formats to _update_ui_with_results
            self.root.after(0, self._update_ui_with_results, results, source_format_str, dest_format_str)
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
        except ValueError as e: # Catch format validation errors from backend
            self.root.after(0, self._log_message, f"Configuration Error: {e}")
        except ConversionPipelineError as e: # Catch other backend errors
            self.root.after(0, self._log_message, f"Conversion Pipeline Error: {e}")
        except Exception as e: # Catch any other unexpected errors
            self.root.after(0, self._log_message, f"An unexpected error occurred: {e}\nType: {type(e).__name__}")
        finally:
            self.root.after(0, self._re_enable_ui_after_conversion)

    def _update_ui_with_results(self, results, source_format, dest_format):
        """
        Updates the ScrolledText widget with detailed results from the conversion.
        This method is scheduled to run on the main UI thread by `_conversion_worker`.

        Args:
            results (dict): The results dictionary returned by `convert_images_in_folder`.
            source_format (str): The source format used for this batch.
            dest_format (str): The destination format used for this batch.
        """
        self._log_message("-------------------------------------------------")
        self._log_message(f"Conversion task ({source_format.upper()} to {dest_format.upper()}) finished.") # Clarified

        if results['successful']:
            self._log_message(f"\nSuccessfully converted ({len(results['successful'])} files) to {dest_format.upper()}:") # Added dest format
            for orig, new in results['successful']:
                self._log_message(f"  - '{orig}' -> '{new}'") # Simpler, context is given above
        
        if results['failed']:
            self._log_message(f"\nFailed conversions ({len(results['failed'])} files):")
            for fname, err_msg in results['failed']:
                self._log_message(f"  - '{fname}': {err_msg}")

        if results['skipped']:
            self._log_message(f"\nSkipped items ({len(results['skipped'])}):")
            for fname, reason in results['skipped']:
                # Backend now provides generic skip messages based on source_format,
                # so UI doesn't need to re-format "File is not a PNG image" etc.
                self._log_message(f"  - '{fname}': {reason}")
        
        self._log_message(f"\n--- Summary for {source_format.upper()} to {dest_format.upper()} conversion ---")
        self._log_message(f"Successfully converted: {len(results['successful']):<5}")
        self._log_message(f"Failed:                 {len(results['failed']):<5}")
        self._log_message(f"Skipped:                {len(results['skipped']):<5}")
        self._log_message("-------------------------------------------------")

    def _re_enable_ui_after_conversion(self):
        """
        Re-enables UI elements (Browse, Convert buttons, Format selectors) after
        the conversion attempt is complete. Sets `is_converting` to False.
        This method is scheduled to run on the main UI thread.
        """
        self.is_converting = False
        self.browse_button.config(state="normal")
        self.source_format_combo.config(state="readonly") # Re-enable format selectors
        self.dest_format_combo.config(state="readonly")
        # self.delete_originals_checkbox.config(state="normal") # TODO: When implemented
        
        self._update_button_states() # Re-evaluates convert button based on current state

        # Add a log message if convert button is still disabled due to some specific reason
        if self.convert_button['state'] == tk.DISABLED:
            if not BACKEND_AVAILABLE:
                 self._log_message("Note: Convert button remains disabled as backend is not available.")
            elif not (self.folder_path.get() and os.path.isdir(self.folder_path.get())):
                 self._log_message("Note: Convert button remains disabled as current folder path is invalid or not selected.")
            elif not (self.source_format_var.get() and self.dest_format_var.get()):
                 self._log_message("Note: Convert button remains disabled as source or destination format is not selected.")


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
