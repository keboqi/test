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
    convert_images_in_folder, # Updated function name
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
        self.base_test_dir = "test_images_temp_base" # Base for all test dirs
        self.test_dir = os.path.join(self.base_test_dir, "core_tests")
        self.empty_dir = os.path.join(self.base_test_dir, "empty_dir_core")
        self.no_source_files_dir = os.path.join(self.base_test_dir, "no_source_files_dir_core")

        # Clean up base directory if it exists from a previous failed run
        if os.path.exists(self.base_test_dir):
            shutil.rmtree(self.base_test_dir)
        
        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(self.empty_dir, exist_ok=True)
        os.makedirs(self.no_source_files_dir, exist_ok=True)

        self.filenames = {
            "png": "dummy.png",
            "jpg": "dummy.jpg",
            "gif": "dummy.gif",
            "bmp": "dummy.bmp",
            "webp": "dummy.webp", # For testing conversion to an existing file type
            "txt": "non_image.txt",
            "corrupted_png": "corrupted.png",
            "corrupted_jpg": "corrupted.jpg",
            "fake_png_is_jpg": "fake_png_is_jpg.png", # A JPG file with .png extension
            "subfolder": "subfolder_core"
        }

        if PIL_AVAILABLE_FOR_TEST_SETUP:
            try:
                # Create valid images
                Image.new('RGB', (1, 1), color='red').save(os.path.join(self.test_dir, self.filenames["png"]), "PNG")
                Image.new('RGB', (1, 1), color='blue').save(os.path.join(self.test_dir, self.filenames["jpg"]), "JPEG")
                # For GIF, need to use save_all for animated, or just save for static
                gif_img = Image.new('L', (1, 1), color=0) # L mode for simple GIF
                gif_img.save(os.path.join(self.test_dir, self.filenames["gif"]), "GIF")
                Image.new('RGB', (1, 1), color='green').save(os.path.join(self.test_dir, self.filenames["bmp"]), "BMP")

                # Create a JPG file but name it with .png extension
                Image.new('RGB', (1,1), color='yellow').save(os.path.join(self.test_dir, self.filenames["fake_png_is_jpg"]), "JPEG")

                # Create dummy corrupted files (just text content)
                with open(os.path.join(self.test_dir, self.filenames["corrupted_png"]), 'w') as f:
                    f.write("This is not a valid PNG.")
                with open(os.path.join(self.test_dir, self.filenames["corrupted_jpg"]), 'w') as f:
                    f.write("This is not a valid JPG.")
            except Exception as e:
                self.fail(f"Setup failed: Could not create dummy image files even if PIL was imported: {e}")
        else:
            # Create dummy empty files if PIL is not there for tests that don't rely on actual conversion
            for ext in ["png", "jpg", "gif", "bmp"]:
                with open(os.path.join(self.test_dir, self.filenames[ext]), 'w') as f:
                    f.write(f"dummy {ext} content")
            with open(os.path.join(self.test_dir, self.filenames["corrupted_png"]), 'w') as f:
                f.write("dummy corrupted png")
            with open(os.path.join(self.test_dir, self.filenames["corrupted_jpg"]), 'w') as f:
                f.write("dummy corrupted jpg")
            with open(os.path.join(self.test_dir, self.filenames["fake_png_is_jpg"]), 'w') as f:
                f.write("actually a jpg but named .png")


        with open(os.path.join(self.test_dir, self.filenames["txt"]), 'w') as f:
            f.write("This is not an image.")
        
        # For no_source_files_dir, put a file of a different type
        with open(os.path.join(self.no_source_files_dir, "other_type.jpeg"), 'w') as f:
            f.write("A JPEG file.")

        os.makedirs(os.path.join(self.test_dir, self.filenames["subfolder"]), exist_ok=True)


    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.base_test_dir):
            shutil.rmtree(self.base_test_dir)

    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping actual conversion test.")
    def test_png_to_webp_successful_conversion_core(self):
        """Test successful PNG to WEBP conversion using the core function."""
        source = "png"
        dest = "webp"
        source_filename = self.filenames[source]
        dest_filename = os.path.splitext(source_filename)[0] + "." + dest
        
        results = convert_images_in_folder(self.test_dir, source_format=source, dest_format=dest)
        
        self.assertIn((source_filename, dest_filename), results['successful'])
        self.assertEqual(len(results['failed']), 0)
        
        expected_dest_path = os.path.join(self.test_dir, dest_filename)
        self.assertTrue(os.path.exists(expected_dest_path), f"{dest.upper()} file '{dest_filename}' was not created.")
        original_source_path = os.path.join(self.test_dir, source_filename)
        self.assertTrue(os.path.exists(original_source_path), "Original source file was deleted (it should not be).")

    def test_non_source_format_file_handling_core(self):
        """Test that files not matching source_format (e.g. .txt, or .jpg when source is .png) are skipped."""
        source_format = "png"
        dest_format = "webp"
        
        # Test with a .txt file
        txt_file = self.filenames["txt"]
        results = convert_images_in_folder(self.test_dir, source_format=source_format, dest_format=dest_format)
        expected_reason_txt = f"File is not a {source_format.upper()} image"
        found_txt_skipped = any(item[0] == txt_file and expected_reason_txt in item[1] for item in results['skipped'])
        self.assertTrue(found_txt_skipped, f"Text file '{txt_file}' was not correctly skipped when converting {source_format}.")
        txt_output_path = os.path.join(self.test_dir, os.path.splitext(txt_file)[0] + "." + dest_format)
        self.assertFalse(os.path.exists(txt_output_path), f"Output file was created for text file '{txt_file}'.")

        # Test with a .jpg file when source is .png
        jpg_file = self.filenames["jpg"]
        results = convert_images_in_folder(self.test_dir, source_format=source_format, dest_format=dest_format)
        expected_reason_jpg = f"File is not a {source_format.upper()} image"
        found_jpg_skipped = any(item[0] == jpg_file and expected_reason_jpg in item[1] for item in results['skipped'])
        self.assertTrue(found_jpg_skipped, f"JPG file '{jpg_file}' was not correctly skipped when converting {source_format}.")
        jpg_output_path = os.path.join(self.test_dir, os.path.splitext(jpg_file)[0] + "." + dest_format)
        self.assertFalse(os.path.exists(jpg_output_path), f"Output file was created for JPG file '{jpg_file}' when source was {source_format}.")


    def test_subdirectory_handling_core(self):
        """Test that subdirectories are skipped by the core function."""
        results = convert_images_in_folder(self.test_dir, source_format="png", dest_format="webp")
        subfolder_name = self.filenames["subfolder"]
        found_subdir_skipped = any(item[0] == subfolder_name and "Item is a directory" in item[1] for item in results['skipped']) # Updated reason check
        self.assertTrue(found_subdir_skipped, f"Subfolder '{subfolder_name}' was not correctly skipped.")

    def test_invalid_folder_path_exception_core(self):
        """Test core function raises InvalidFolderPathError for non-existent paths."""
        non_existent_folder = "this_folder_truly_does_not_exist_xyz"
        with self.assertRaisesRegex(InvalidFolderPathError, "not a valid directory or was not found"):
            convert_images_in_folder(non_existent_folder, source_format="png", dest_format="webp")

    def test_no_source_files_in_folder_core(self):
        """Test core function with a folder containing no files of the source_format."""
        # self.no_source_files_dir contains only a .jpeg file when it was created.
        # We are testing conversion from PNG to WEBP.
        source_format = "png"
        dest_format = "webp"
        results = convert_images_in_folder(self.no_source_files_dir, source_format=source_format, dest_format=dest_format)
        self.assertEqual(len(results['successful']), 0)
        self.assertEqual(len(results['failed']), 0)
        # The jpeg file should be skipped because it's not a png
        expected_reason = f"File is not a {source_format.upper()} image"
        self.assertTrue(any(item[0] == "other_type.jpeg" and expected_reason in item[1] for item in results['skipped']))


    def test_empty_folder_core(self):
        """Test core function with an empty folder."""
        results = convert_images_in_folder(self.empty_dir, source_format="png", dest_format="webp")
        self.assertEqual(len(results['successful']), 0)
        self.assertEqual(len(results['failed']), 0)
        self.assertEqual(len(results['skipped']), 0)

    @patch('image_converter.PIL_Image_Module', None)
    def test_missing_dependency_exception_core(self):
        """Test core function raises MissingDependencyError if Pillow is not available."""
        with self.assertRaisesRegex(MissingDependencyError, "Pillow library .* not found"):
            convert_images_in_folder(self.test_dir, source_format="png", dest_format="webp")
            
    @patch('os.listdir')
    def test_folder_permission_error_core(self, mock_listdir):
        """Test core function raises FolderPermissionError if os.listdir fails."""
        mock_listdir.side_effect = PermissionError("Test permission denied")
        with self.assertRaisesRegex(FolderPermissionError, "Permission denied to read/list files"):
            convert_images_in_folder(self.test_dir, source_format="png", dest_format="webp")

    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping actual conversion test.")
    def test_jpeg_to_png_successful_conversion_core(self):
        source = "jpg"
        dest = "png"
        source_filename = self.filenames[source]
        dest_filename = os.path.splitext(source_filename)[0] + "." + dest
        results = convert_images_in_folder(self.test_dir, source_format=source, dest_format=dest)
        self.assertIn((source_filename, dest_filename), results['successful'])
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, dest_filename)))

    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping actual conversion test.")
    def test_gif_to_bmp_successful_conversion_core(self):
        source = "gif"
        dest = "bmp"
        source_filename = self.filenames[source]
        dest_filename = os.path.splitext(source_filename)[0] + "." + dest
        results = convert_images_in_folder(self.test_dir, source_format=source, dest_format=dest)
        self.assertIn((source_filename, dest_filename), results['successful'])
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, dest_filename)))

    def test_unsupported_source_format_pillow_value_error(self):
        """Test ValueError for unsupported source format by Pillow."""
        with self.assertRaisesRegex(ValueError, "Source format 'xyz' is not a supported read format by Pillow"):
            convert_images_in_folder(self.test_dir, source_format="xyz", dest_format="webp")

    def test_unsupported_dest_format_pillow_value_error(self):
        """Test ValueError for unsupported destination format by Pillow."""
        # Assuming "png" is a valid source format for this test.
        with self.assertRaisesRegex(ValueError, "Destination format 'xyz' is not a supported write format by Pillow"):
            convert_images_in_folder(self.test_dir, source_format="png", dest_format="xyz")
            
    def test_invalid_source_format_empty_value_error(self):
        """Test ValueError for empty source_format string."""
        with self.assertRaisesRegex(ValueError, "Source format must be a non-empty string."):
            convert_images_in_folder(self.test_dir, source_format="", dest_format="webp")

    def test_invalid_dest_format_none_value_error(self):
        """Test ValueError for None dest_format."""
        with self.assertRaisesRegex(ValueError, "Destination format must be a non-empty string."):
            convert_images_in_folder(self.test_dir, source_format="png", dest_format=None)

    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping this test.")
    def test_mismatched_extension_skipped_if_source_ext_differs_from_arg(self):
        """Test file with .png ext (but is JPG) is skipped if source_format='jpg'."""
        # File is self.filenames["fake_png_is_jpg"] ("fake_png_is_jpg.png"), which is a JPG.
        # If we try to convert JPGs, this .png file should be skipped.
        results = convert_images_in_folder(self.test_dir, source_format="jpg", dest_format="webp")
        skipped_filename = self.filenames["fake_png_is_jpg"]
        self.assertTrue(
            any(item[0] == skipped_filename and "File is not a JPG image" in item[1] for item in results['skipped']),
            f"File '{skipped_filename}' was not skipped or reason was incorrect."
        )

    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping this test.")
    def test_mismatched_extension_failed_if_source_ext_matches_arg_but_content_bad(self):
        """Test file with .png ext (but is JPG) fails if source_format='png'."""
        # File is self.filenames["fake_png_is_jpg"] ("fake_png_is_jpg.png"), which is a JPG.
        # If we try to convert PNGs, Pillow should fail to open this as a PNG.
        results = convert_images_in_folder(self.test_dir, source_format="png", dest_format="webp")
        failed_filename = self.filenames["fake_png_is_jpg"]
        
        # Check if the specific file is in the 'failed' list
        failure_entry = next((item for item in results['failed'] if item[0] == failed_filename), None)
        self.assertIsNotNone(failure_entry, f"File '{failed_filename}' was not in failed list.")
        # Check if the error message indicates an issue with opening or identifying the image
        # PIL raises UnidentifiedImageError for this usually.
        self.assertIn("Cannot identify image file", failure_entry[1], "Error message for mismatched content seems incorrect.")


    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping corrupted file test.")
    def test_corrupted_png_file_failed(self):
        """Test corrupted PNG file is handled and reported in 'failed'."""
        results = convert_images_in_folder(self.test_dir, source_format="png", dest_format="webp")
        corrupted_file = self.filenames["corrupted_png"]
        self.assertTrue(
            any(item[0] == corrupted_file and "Cannot identify image file" in item[1] for item in results['failed']), # Pillow's UnidentifiedImageError
            f"Corrupted PNG file '{corrupted_file}' not found in 'failed' results or error message mismatch."
        )

    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping corrupted file test.")
    def test_corrupted_jpg_file_failed(self):
        """Test corrupted JPG file is handled and reported in 'failed'."""
        results = convert_images_in_folder(self.test_dir, source_format="jpg", dest_format="png")
        corrupted_file = self.filenames["corrupted_jpg"]
        self.assertTrue(
            any(item[0] == corrupted_file and "Cannot identify image file" in item[1] for item in results['failed']),
            f"Corrupted JPG file '{corrupted_file}' not found in 'failed' results or error message mismatch."
        )


class TestImageConverterCLI(unittest.TestCase):
    """Tests for the Command-Line Interface of image_converter.py"""

    def setUp(self):
        """Set up test environment for CLI tests."""
        self.base_test_dir_cli = "test_images_temp_base_cli" # Base for all CLI test dirs
        self.test_dir = os.path.join(self.base_test_dir_cli, "cli_tests")
        
        if os.path.exists(self.base_test_dir_cli):
            shutil.rmtree(self.base_test_dir_cli)
        os.makedirs(self.test_dir, exist_ok=True)

        self.png_filename = "cli_dummy.png"
        self.jpg_filename = "cli_dummy.jpg" # For new CLI test

        if PIL_AVAILABLE_FOR_TEST_SETUP:
            try:
                Image.new('RGB', (1, 1), color='blue').save(os.path.join(self.test_dir, self.png_filename), "PNG")
                Image.new('RGB', (1, 1), color='green').save(os.path.join(self.test_dir, self.jpg_filename), "JPEG")
            except Exception as e:
                self.fail(f"CLI Setup failed: Could not create dummy images: {e}")
        else:
            with open(os.path.join(self.test_dir, self.png_filename), 'w') as f:
                f.write("dummy cli png content")
            with open(os.path.join(self.test_dir, self.jpg_filename), 'w') as f:
                f.write("dummy cli jpg content")


    def tearDown(self):
        """Clean up test environment for CLI tests."""
        if os.path.exists(self.base_test_dir_cli):
            shutil.rmtree(self.base_test_dir_cli)

    def _run_script_cli(self, folder_path_arg, source_format_arg=None, dest_format_arg=None):
        """Helper function to run the image_converter.py script for CLI tests."""
        cmd = ["python", SCRIPT_PATH, folder_path_arg]
        if source_format_arg:
            cmd.append(source_format_arg)
        if dest_format_arg:
            cmd.append(dest_format_arg)
            
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=os.environ.copy() 
        )
        return process

    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping CLI success test.")
    def test_cli_png_to_webp_successful_run(self):
        """Test successful execution of CLI for PNG to WEBP and output."""
        source_format = "png"
        dest_format = "webp"
        webp_filename = os.path.splitext(self.png_filename)[0] + "." + dest_format
        
        process = self._run_script_cli(self.test_dir, source_format, dest_format)
        
        self.assertEqual(process.returncode, 0, f"CLI script exited with error: {process.stderr or process.stdout}")
        # Example: Successfully converted: \n  - 'cli_dummy.png' -> 'cli_dummy.webp'
        # Need to be careful with exact stdout format.
        success_msg_part1 = "Successfully converted:"
        success_msg_part2 = f"  - '{self.png_filename}' -> '{webp_filename}'" # Check specific conversion
        
        self.assertIn(success_msg_part1, process.stdout)
        self.assertIn(success_msg_part2, process.stdout)
        
        expected_webp_path = os.path.join(self.test_dir, webp_filename)
        self.assertTrue(os.path.exists(expected_webp_path), f"{dest_format.upper()} file was not created by CLI.")

    def test_cli_invalid_folder_path(self):
        """Test CLI behavior with a non-existent folder path."""
        non_existent_folder = "this_folder_does_not_exist_for_cli"
        process = self._run_script_cli(non_existent_folder, "png", "webp") # Must provide formats now
        self.assertNotEqual(process.returncode, 0, "CLI script should exit with non-zero code for invalid path.")
        self.assertIn(f"Configuration Error: The path '{non_existent_folder}' is not a valid directory or was not found.", process.stdout)

    @unittest.skipUnless(PIL_AVAILABLE_FOR_TEST_SETUP, "Pillow not installed, skipping CLI success test.")
    def test_cli_jpeg_to_png_successful_run(self):
        """Test successful execution of CLI for JPEG to PNG."""
        source_format = "jpg"
        dest_format = "png"
        dest_filename = os.path.splitext(self.jpg_filename)[0] + "." + dest_format
        
        process = self._run_script_cli(self.test_dir, source_format, dest_format)
        
        self.assertEqual(process.returncode, 0, f"CLI script exited with error: {process.stderr or process.stdout}")
        self.assertIn(f"  - '{self.jpg_filename}' -> '{dest_filename}'", process.stdout)
        expected_dest_path = os.path.join(self.test_dir, dest_filename)
        self.assertTrue(os.path.exists(expected_dest_path), f"{dest_format.upper()} file was not created by CLI.")

    def test_cli_missing_format_args(self):
        """Test CLI exits with error if source/dest format args are missing."""
        # Missing both
        process_missing_both = self._run_script_cli(self.test_dir)
        self.assertNotEqual(process_missing_both.returncode, 0)
        # The exact error message depends on argparse configuration.
        # It's typically "the following arguments are required: source_format, dest_format"
        self.assertIn("the following arguments are required: source_format, dest_format", process_missing_both.stderr.lower())

        # Missing one (dest_format)
        process_missing_dest = self._run_script_cli(self.test_dir, "png")
        self.assertNotEqual(process_missing_dest.returncode, 0)
        self.assertIn("the following arguments are required: dest_format", process_missing_dest.stderr.lower())

    def test_cli_unsupported_format_arg(self):
        """Test CLI exits with error for unsupported format arguments."""
        # This tests if the ValueError from core logic is caught by main_cli and prints error.
        source_format = "xyz" # Unsupported
        dest_format = "webp"
        process = self._run_script_cli(self.test_dir, source_format, dest_format)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(f"Configuration Error: Source format '{source_format}' is not a supported read format by Pillow.", process.stdout)
        
    # Note: Testing CLI for missing Pillow (MissingDependencyError) is complex as it requires
    # manipulating the subprocess's environment. The core logic test for this and the
    # initial check in main_cli itself are considered sufficient.

if __name__ == "__main__":
    unittest.main()
