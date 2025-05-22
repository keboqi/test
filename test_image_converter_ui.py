import unittest
import tkinter as tk
from unittest.mock import patch, MagicMock
import sys

# We need to handle the case where the image_converter module or its dependencies
# might not be available, especially Pillow, which could prevent the UI from
# even being imported if not handled carefully by the UI script itself.
# The image_converter_ui.py script already has a BACKEND_AVAILABLE flag.

# To ensure this test script doesn't fail during discovery or import
# if 'image_converter' or 'PIL' is missing, we can try to import
# ImageConverterApp and catch ImportErrors related to the backend.
try:
    from image_converter_ui import ImageConverterApp
    UI_IMPORT_SUCCESSFUL = True
except ImportError as e:
    # This might happen if image_converter.py is missing, or if image_converter.py
    # itself has an unhandled import error for PIL at the module level (which it doesn't).
    # Our image_converter_ui.py is designed to handle missing backend, so this
    # outer try-except is more for robustness of the test script itself.
    UI_IMPORT_SUCCESSFUL = False
    print(f"Warning: Could not import ImageConverterApp for testing: {e}", file=sys.stderr)


@unittest.skipUnless(UI_IMPORT_SUCCESSFUL, "ImageConverterApp could not be imported. Skipping UI tests.")
class TestImageConverterUI(unittest.TestCase):
    
    def test_app_creation(self):
        """Test if the ImageConverterApp can be created without immediate errors."""
        root = None  # Ensure root is defined for finally block
        try:
            # In some CI environments, a display might not be available.
            # Tkinter requires a display to initialize.
            # We attempt to create the root window and the app.
            # If a TclError related to display occurs, we skip the test.
            root = tk.Tk()
            # Hide the window during test; not strictly necessary for this test,
            # but good practice for UI tests that might otherwise show windows.
            root.withdraw() 
            
            app = ImageConverterApp(root)
            self.assertIsNotNone(app.root, "App root window should be created.")
            self.assertEqual(app.root, root, "App root should be the provided root window.")
            
            # Check if the title is set (basic check that __init__ ran)
            self.assertEqual(app.root.title(), "PNG to WebP Converter")

        except tk.TclError as e:
            # Common TclError messages when no display is available:
            # - "no display name and no $DISPLAY environment variable"
            # - "couldn't connect to display"
            # - "Application initialization failed: couldn't connect to display" (on some systems)
            no_display_errors = [
                "no display name", 
                "couldn't connect to display",
                "application initialization failed" # Catch broader init errors on CI
            ]
            if any(err_msg in str(e).lower() for err_msg in no_display_errors):
                self.skipTest(f"Skipping UI test: Display not available or Tcl/Tk initialization failed. Error: {e}")
            else:
                # If it's a TclError but not related to display, re-raise it.
                raise
        finally:
            # Ensure the root window is destroyed if it was created.
            if root:
                # Using root.destroy() directly can sometimes hang or error if mainloop hasn't run.
                # A safer way in tests is to schedule its destruction.
                root.after(0, root.destroy) 
                # Or, if withdraw() was used and no mainloop, just destroy.
                # root.destroy() # Simpler if no mainloop interaction.

if __name__ == "__main__":
    unittest.main()
