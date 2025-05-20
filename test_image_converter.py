import unittest
import os
import shutil
import subprocess
from PIL import Image # To create a dummy PNG

# Path to the script to be tested
SCRIPT_PATH = "image_converter.py"

class TestImageConverter(unittest.TestCase):

    def setUp(self):
        """Set up test environment: create temporary directories and files."""
        self.test_dir = "test_images_temp"
        self.empty_dir = "empty_test_dir_temp"
        self.png_filename = "dummy.png"
        self.webp_filename = "dummy.webp"
        self.txt_filename = "non_image.txt"
        self.subfolder_name = "subfolder"

        # Create main test directory
        os.makedirs(self.test_dir, exist_ok=True)
        # Create empty test directory
        os.makedirs(self.empty_dir, exist_ok=True)

        # Create a dummy PNG file using Pillow
        try:
            img = Image.new('RGB', (1, 1), color = 'red')
            img.save(os.path.join(self.test_dir, self.png_filename), "PNG")
        except Exception as e:
            self.fail(f"Setup failed: Could not create dummy PNG file: {e}")

        # Create a dummy text file
        with open(os.path.join(self.test_dir, self.txt_filename), 'w') as f:
            f.write("This is not an image.")

        # Create a subdirectory
        os.makedirs(os.path.join(self.test_dir, self.subfolder_name), exist_ok=True)
        
        # Create a folder with only a text file for the "no PNGs" test
        self.no_png_dir = "no_png_test_dir_temp"
        os.makedirs(self.no_png_dir, exist_ok=True)
        with open(os.path.join(self.no_png_dir, self.txt_filename), 'w') as f:
            f.write("Another text file.")


    def tearDown(self):
        """Clean up test environment: remove temporary directories and files."""
        for dir_path in [self.test_dir, self.empty_dir, self.no_png_dir]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)

    def _run_script(self, folder_path_arg):
        """Helper function to run the image_converter.py script."""
        process = subprocess.run(
            ["python", SCRIPT_PATH, folder_path_arg],
            capture_output=True,
            text=True
        )
        return process

    def test_successful_conversion(self):
        """Test conversion of a valid PNG to WebP."""
        process = self._run_script(self.test_dir)
        
        self.assertEqual(process.returncode, 0, f"Script exited with error: {process.stderr or process.stdout}")
        
        expected_webp_path = os.path.join(self.test_dir, self.webp_filename)
        self.assertTrue(os.path.exists(expected_webp_path), f"WebP file '{self.webp_filename}' was not created.")
        
        original_png_path = os.path.join(self.test_dir, self.png_filename)
        self.assertTrue(os.path.exists(original_png_path), "Original PNG file was deleted (it should not be).")
        self.assertIn(f"Success: Converted '{self.png_filename}' to '{self.webp_filename}'", process.stdout)

    def test_non_png_file_handling(self):
        """Test that non-PNG files are skipped and not converted."""
        process = self._run_script(self.test_dir)
        self.assertEqual(process.returncode, 0, f"Script exited with error: {process.stderr or process.stdout}")

        non_image_webp_path = os.path.join(self.test_dir, os.path.splitext(self.txt_filename)[0] + ".webp")
        self.assertFalse(os.path.exists(non_image_webp_path), f"WebP file was created for non-PNG file '{self.txt_filename}'.")
        
        original_txt_path = os.path.join(self.test_dir, self.txt_filename)
        self.assertTrue(os.path.exists(original_txt_path), f"Text file '{self.txt_filename}' was unexpectedly modified or deleted.")
        self.assertIn(f"Info: Skipping '{self.txt_filename}' (not a PNG image).", process.stdout)

    def test_subdirectory_handling(self):
        """Test that subdirectories are skipped."""
        process = self._run_script(self.test_dir)
        self.assertEqual(process.returncode, 0, f"Script exited with error: {process.stderr or process.stdout}")
        
        # Check stdout for skipping message
        self.assertIn(f"Info: Skipping '{self.subfolder_name}' (it is a directory or not a regular file).", process.stdout)
        
        # Ensure no .webp file was attempted for the subfolder name
        subfolder_webp_path = os.path.join(self.test_dir, self.subfolder_name + ".webp")
        self.assertFalse(os.path.exists(subfolder_webp_path), "Script attempted to convert a subfolder.")

    def test_invalid_folder_path(self):
        """Test script behavior with a non-existent folder path."""
        non_existent_folder = "this_folder_does_not_exist_12345"
        process = self._run_script(non_existent_folder)
        
        # Argparse typically exits with 2 for bad arguments, but the script's manual check exits with a print.
        # The script prints to stdout for this error.
        self.assertNotEqual(process.returncode, 0, "Script should exit with a non-zero code for invalid path.")
        self.assertIn(f"Error: The provided path '{non_existent_folder}' is not a valid directory or was not found.", process.stdout)

    def test_no_png_files_in_folder(self):
        """Test script with a folder containing no PNG files (e.g., only text files)."""
        process = self._run_script(self.no_png_dir)
        self.assertEqual(process.returncode, 0, f"Script exited with error: {process.stderr or process.stdout}")
        
        # Check that no WebP files were created
        found_webp_files = [f for f in os.listdir(self.no_png_dir) if f.lower().endswith(".webp")]
        self.assertEqual(len(found_webp_files), 0, f"WebP files were created in a folder with no PNGs: {found_webp_files}")
        self.assertIn(f"Info: Skipping '{self.txt_filename}' (not a PNG image).", process.stdout)

    def test_empty_folder(self):
        """Test script with an empty folder."""
        process = self._run_script(self.empty_dir)
        self.assertEqual(process.returncode, 0, f"Script exited with error: {process.stderr or process.stdout}")
        
        found_webp_files = [f for f in os.listdir(self.empty_dir) if f.lower().endswith(".webp")]
        self.assertEqual(len(found_webp_files), 0, "WebP files were created in an empty folder.")
        # Check that stdout contains the processing message but no conversion/skipping messages for files
        self.assertIn(f"Starting image processing in folder: '{self.empty_dir}'", process.stdout)
        self.assertNotIn("Success: Converted", process.stdout)
        self.assertNotIn("Info: Skipping", process.stdout) # No files to skip

if __name__ == "__main__":
    unittest.main()
