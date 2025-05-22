import unittest
import os
import shutil
import subprocess
from unittest.mock import patch, MagicMock

# Attempt to import Pillow for dummy image creation, but allow tests to run if it's not present
# (especially for testing MissingDependencyError)
try:
    from PIL import Image
    PIL_AVAILABLE_FOR_TEST_SETUP = True
except ImportError:
    PIL_AVAILABLE_FOR_TEST_SETUP = False

# Import the core function and custom exceptions from the refactored script
from image_converter import (
    convert_png_to_webp_in_folder,
    MissingDependencyError,
    InvalidFolderPathError,
    FolderPermissionError,
    # PIL_Image_Module # This is what we might mock
)

# Path to the script for CLI tests
SCRIPT_PATH = "image_converter.py"


class TestImageConverterCoreLogic(unittest.TestCase):

    def setUp(self):
        """Set up test environment: create temporary directories and files."""
        self.test_dir = "test_images_temp_core"
        self.empty_dir = "empty_test_dir_temp_core"
        self.png_filename = "dummy.png"
        self.webp_filename = "dummy.webp"
        self.txt_filename = "non_image.txt"
        self.subfolder_name = "subfolder_core"

        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(self.empty_dir, exist_ok=True)

        if PIL_AVAILABLE_FOR_TEST_SETUP:
            try:
                img = Image.new('RGB', (1, 1), color='red')
                img.save(os.path.join(self.test_dir, self.png_filename), "PNG")
            except Exception as e:
                # This might happen if Pillow is technically importable but broken
                self.fail(f"Setup failed: Could not create dummy PNG file even if PIL was imported: {e}")
        else:
            # Create a dummy empty file if PIL is not there, for tests that don't rely on actual conversion
            with open(os.path.join(self.test_dir, self.png_filename), 'w') as f:
                f.write("dummy png content")


        with open(os.path.join(self.test_dir, self.txt_filename), 'w') as f:
            f.write("This is not an image.")

        os.makedirs(os.path.join(self.test_dir, self.subfolder_name), exist_ok=True)
        
        self.no_png_dir = "no_png_test_dir_temp_core"
        os.makedirs(self.no_png_dir, exist_ok=True)
        with open(os.path.join(self.no_png_dir, self.txt_filename), 'w') as f:
            f.write("Another text file.")

    def tearDown(self):
        """Clean up test environment."""
        for dir_path in [self.test_dir, self.empty_dir, self.no_png_dir]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)

    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping actual conversion test.")
    def test_successful_conversion_core(self):
        """Test successful conversion using the core function."""
        results = convert_png_to_webp_in_folder(self.test_dir)
        
        self.assertIn((self.png_filename, self.webp_filename), results['successful'])
        self.assertEqual(len(results['failed']), 0)
        
        expected_webp_path = os.path.join(self.test_dir, self.webp_filename)
        self.assertTrue(os.path.exists(expected_webp_path), f"WebP file '{self.webp_filename}' was not created.")
        original_png_path = os.path.join(self.test_dir, self.png_filename)
        self.assertTrue(os.path.exists(original_png_path), "Original PNG file was deleted (it should not be).")

    def test_non_png_file_handling_core(self):
        """Test that non-PNG files are skipped by the core function."""
        results = convert_png_to_webp_in_folder(self.test_dir)
        
        found_txt_skipped = any(item[0] == self.txt_filename and "Not a PNG file" in item[1] for item in results['skipped'])
        self.assertTrue(found_txt_skipped, f"Text file '{self.txt_filename}' was not correctly skipped.")
        
        non_image_webp_path = os.path.join(self.test_dir, os.path.splitext(self.txt_filename)[0] + ".webp")
        self.assertFalse(os.path.exists(non_image_webp_path), "WebP file was created for non-PNG file.")

    def test_subdirectory_handling_core(self):
        """Test that subdirectories are skipped by the core function."""
        results = convert_png_to_webp_in_folder(self.test_dir)
        
        found_subdir_skipped = any(item[0] == self.subfolder_name and "Is a directory" in item[1] for item in results['skipped'])
        self.assertTrue(found_subdir_skipped, f"Subfolder '{self.subfolder_name}' was not correctly skipped.")

    def test_invalid_folder_path_exception_core(self):
        """Test core function raises InvalidFolderPathError for non-existent paths."""
        non_existent_folder = "this_folder_truly_does_not_exist_xyz"
        with self.assertRaisesRegex(InvalidFolderPathError, "not a valid directory or was not found"):
            convert_png_to_webp_in_folder(non_existent_folder)

    def test_no_png_files_in_folder_core(self):
        """Test core function with a folder containing no PNG files."""
        results = convert_png_to_webp_in_folder(self.no_png_dir)
        self.assertEqual(len(results['successful']), 0)
        self.assertEqual(len(results['failed']), 0)
        self.assertTrue(any(item[0] == self.txt_filename for item in results['skipped']))

    def test_empty_folder_core(self):
        """Test core function with an empty folder."""
        results = convert_png_to_webp_in_folder(self.empty_dir)
        self.assertEqual(len(results['successful']), 0)
        self.assertEqual(len(results['failed']), 0)
        self.assertEqual(len(results['skipped']), 0)

    @patch('image_converter.PIL_Image_Module', None)
    def test_missing_dependency_exception_core(self):
        """Test core function raises MissingDependencyError if Pillow is not available."""
        with self.assertRaisesRegex(MissingDependencyError, "Pillow library .* not found"):
            convert_png_to_webp_in_folder(self.test_dir)
            
    @patch('os.listdir')
    def test_folder_permission_error_core(self, mock_listdir):
        """Test core function raises FolderPermissionError if os.listdir fails."""
        mock_listdir.side_effect = PermissionError("Test permission denied")
        with self.assertRaisesRegex(FolderPermissionError, "Permission denied to read/list files"):
            convert_png_to_webp_in_folder(self.test_dir)


class TestImageConverterCLI(unittest.TestCase):
    """Tests for the Command-Line Interface of image_converter.py"""

    def setUp(self):
        """Set up test environment for CLI tests."""
        self.test_dir = "test_images_temp_cli"
        self.png_filename = "cli_dummy.png"
        self.webp_filename = "cli_dummy.webp"
        os.makedirs(self.test_dir, exist_ok=True)

        if PIL_AVAILABLE_FOR_TEST_SETUP:
            try:
                img = Image.new('RGB', (1, 1), color='blue')
                img.save(os.path.join(self.test_dir, self.png_filename), "PNG")
            except Exception as e:
                self.fail(f"CLI Setup failed: Could not create dummy PNG: {e}")
        else:
            # Create a dummy empty file if PIL is not there for CLI tests that don't rely on actual conversion
             with open(os.path.join(self.test_dir, self.png_filename), 'w') as f:
                f.write("dummy cli png content")


    def tearDown(self):
        """Clean up test environment for CLI tests."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _run_script_cli(self, folder_path_arg):
        """Helper function to run the image_converter.py script for CLI tests."""
        process = subprocess.run(
            ["python", SCRIPT_PATH, folder_path_arg],
            capture_output=True,
            text=True,
            env=os.environ.copy() # Important for subprocess to find python and script
        )
        return process

    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping CLI success test.")
    def test_cli_successful_run(self):
        """Test successful execution of CLI and output."""
        process = self._run_script_cli(self.test_dir)
        self.assertEqual(process.returncode, 0, f"CLI script exited with error: {process.stderr or process.stdout}")
        self.assertIn(f"Successfully converted:\n  - '{self.png_filename}' -> '{self.webp_filename}'", process.stdout)
        expected_webp_path = os.path.join(self.test_dir, self.webp_filename)
        self.assertTrue(os.path.exists(expected_webp_path), "WebP file was not created by CLI.")

    def test_cli_invalid_folder_path(self):
        """Test CLI behavior with a non-existent folder path."""
        non_existent_folder = "this_folder_does_not_exist_for_cli"
        process = self._run_script_cli(non_existent_folder)
        self.assertNotEqual(process.returncode, 0, "CLI script should exit with non-zero code for invalid path.")
        self.assertIn(f"Configuration Error: The path '{non_existent_folder}' is not a valid directory or was not found.", process.stdout)
        # Note: The error message comes from the main_cli's exception handling of InvalidFolderPathError.
        # The actual exit code 1 is set by sys.exit(1) in main_cli.

    # Testing CLI for missing Pillow is complex as it requires manipulating the subprocess's environment
    # or Python path in a way that Pillow (specifically PIL.Image) cannot be imported by image_converter.py.
    # The MissingDependencyError test for the core logic and the startup check in main_cli give good confidence.
    # A true end-to-end test for this would be more involved (e.g., running in a venv without Pillow).

if __name__ == "__main__":
    unittest.main()
