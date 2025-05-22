#!/usr/bin/env python3
"""
image_converter.py

Purpose:
  Converts PNG images to WebP format within a specified folder.
  This script serves a dual role:
  1. As a command-line tool for direct PNG to WebP conversion.
  2. As a backend module providing core conversion logic to other scripts,
     such as `image_converter_ui.py`.

Description:
  When run as a script, it iterates through files in a user-provided folder.
  For each PNG file (.png, .PNG), it attempts to convert it to the
  WebP format, saving the new .webp file in the same folder.
  The core function `convert_png_to_webp_in_folder` handles common errors
  such as missing folders,
  permission issues, and problematic image files.

Dependencies:
  - Pillow: The Python Imaging Library (PIL) fork.
    Install using: pip install Pillow

CLI Usage:
  python image_converter.py <path_to_folder_with_images>

Example:
  python image_converter.py ./my_pictures

Importable Functions:
  convert_png_to_webp_in_folder(folder_path, delete_originals=False)
"""
import argparse
import os
import sys

# --- Custom Exceptions ---
class ConversionPipelineError(Exception):
    """Base exception for errors in the conversion pipeline."""
    pass

class MissingDependencyError(ConversionPipelineError):
    """Raised when a required dependency (e.g., Pillow) is not found."""
    pass

class InvalidFolderPathError(ConversionPipelineError):
    """Raised when the provided folder path is invalid or not found."""
    pass

class FolderPermissionError(ConversionPipelineError):
    """Raised when there's a permission issue accessing the folder or its contents."""
    pass

# Note: FilePermissionError and ConversionError were defined in thought process,
# but for this refactoring, specific error messages within the 'failed' list
# of the results dictionary will cover these details. FolderPermissionError
# is kept for os.listdir level issues.

# --- Pillow Import Handling ---
try:
    from PIL import Image
    PIL_Image_Module = Image # Store Image module in a clearly named variable
except ModuleNotFoundError:
    PIL_Image_Module = None # Will be checked by core function

# --- Core Logic Function ---
def convert_png_to_webp_in_folder(folder_path, delete_originals=False):
    """
    Converts PNG images in a specified folder to WebP format.

    Args:
        folder_path (str): The path to the folder containing images.
        delete_originals (bool, optional): If True, original PNG files will be
                                 deleted after successful conversion.
                                 Defaults to False. (This feature is planned
                                 but not yet implemented).

    Returns:
        dict: A dictionary with keys 'successful', 'failed', and 'skipped',
              each containing a list of tuples.
              - 'successful': `[(original_filename, webp_filename), ...]`
              - 'failed': `[(filename, error_message_string), ...]`
              - 'skipped': `[(filename, reason_string), ...]`
              Example:
              {
                  'successful': [('image1.png', 'image1.webp')],
                  'failed': [('image2.png', 'Error: Could not open image.')],
                  'skipped': [('notes.txt', 'File is not a PNG image'),
                              ('archive/', 'Item is a directory or not a regular file')]
              }

    Raises:
        MissingDependencyError: If the Pillow library (PIL.Image) is not found/imported.
        InvalidFolderPathError: If `folder_path` is not a valid directory or is inaccessible.
        FolderPermissionError: If `os.listdir(folder_path)` fails due to permission
                               issues or other OS errors preventing file listing.
    """
    if PIL_Image_Module is None:
        raise MissingDependencyError(
            "Pillow library (PIL.Image) not found. It is required for image conversion."
        )

    if not os.path.isdir(folder_path):
        raise InvalidFolderPathError(f"The path '{folder_path}' is not a valid directory or was not found.")

    results = {
        'successful': [],
        'failed': [],
        'skipped': []
    }

    try:
        filenames = os.listdir(folder_path)
    except PermissionError as e:
        raise FolderPermissionError(f"Permission denied to read/list files in folder '{folder_path}'. OS Error: {e}")
    except Exception as e: # Other os.listdir errors
        raise FolderPermissionError(f"Could not list files in folder '{folder_path}'. OS Error: {e}")

    for filename in filenames:
        file_path = os.path.join(folder_path, filename)

        if not os.path.isfile(file_path):
            results['skipped'].append((filename, "Item is a directory or not a regular file"))
            continue

        if not filename.lower().endswith(".png"):
            results['skipped'].append((filename, "File is not a PNG image"))
            continue

        name_without_ext, _ = os.path.splitext(filename)
        webp_filename = name_without_ext + ".webp"
        webp_filepath = os.path.join(folder_path, webp_filename)

        try:
            img = PIL_Image_Module.open(file_path)
            try:
                img.save(webp_filepath, "webp")
                results['successful'].append((filename, webp_filename))
                if delete_originals:
                    # TODO: Implement deletion of original file
                    # try:
                    #     os.remove(file_path)
                    #     results['deleted_originals'].append(filename) # Optional: track deletions
                    # except Exception as e_del:
                    #     results['failed'].append((filename, f"Successfully converted but failed to delete original. Error: {e_del}"))
                    pass # Placeholder for now
            except PermissionError as e_save:
                results['failed'].append((filename, f"Error: Permission denied to save '{webp_filename}'. Check write permissions for the folder. Details: {e_save}"))
            except Exception as e_save: # Other errors during save (e.g., disk full, Pillow internal)
                results['failed'].append((filename, f"Error: Failed to save '{webp_filename}'. Reason: {e_save}"))
        except PermissionError as e_open:
            results['failed'].append((filename, f"Error: Permission denied to read '{filename}'. Check read permissions. Details: {e_open}"))
        except FileNotFoundError: # Should be rare given os.path.isfile, but for robustness
            results['failed'].append((filename, f"Error: File '{filename}' was not found during processing (it may have been moved/deleted)."))
        except Exception as e_open: # Catches PIL.UnidentifiedImageError, other PIL/general errors
            results['failed'].append((filename, f"Error: Could not open or process '{filename}'. It may not be a valid PNG or is corrupted. Details: {e_open}"))
            
    return results

# --- Command-Line Interface (CLI) Handling ---
def main_cli():
    """
    Command-line interface entry point.
    Parses arguments, calls `convert_png_to_webp_in_folder`, and prints a report.
    Exits with appropriate status codes based on success or failure.
    """
    # Initial check for Pillow when running as CLI.
    # The core function also checks, but this provides a clearer message for direct CLI users.
    if PIL_Image_Module is None:
        print(
            "Critical Error: The Pillow library is not installed. This script requires Pillow for image conversion.\n"
            "Please install it by running: python -m pip install Pillow\n"
            "If you are using a virtual environment, ensure it's activated before installing."
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Converts PNG images in a specified folder to WebP format.",
        epilog=f"Example: python {os.path.basename(__file__)} ./my_pictures"
    )
    parser.add_argument(
        "folder_path",
        help="Path to the folder containing PNG images to be converted."
    )
    # TODO: Fully implement --delete-original flag
    # parser.add_argument(
    #     "--delete-original",
    #     action="store_true",
    #     help="Delete original PNG files after successful conversion. (NOT YET IMPLEMENTED)"
    # )

    args = parser.parse_args()
    folder_path = args.folder_path
    # delete_originals_flag = args.delete_original # When implemented

    try:
        print(f"Starting image processing in folder: '{folder_path}'...")
        # results = convert_png_to_webp_in_folder(folder_path, delete_originals_flag) # When implemented
        results = convert_png_to_webp_in_folder(folder_path) # delete_originals default to False

        print("\n--- Conversion Report ---")
        if results['successful']:
            print("\nSuccessfully converted:")
            for orig, new in results['successful']:
                print(f"  - '{orig}' -> '{new}'")
        
        if results['failed']:
            print("\nFailed conversions:")
            for fname, err_msg in results['failed']:
                print(f"  - '{fname}': {err_msg}")

        if results['skipped']:
            print("\nSkipped files/items:")
            for fname, reason in results['skipped']:
                print(f"  - '{fname}': {reason}")
        
        total_processed = len(results['successful']) + len(results['failed']) + len(results['skipped'])
        print(f"\n--- Summary ---")
        print(f"Total items processed: {total_processed}")
        print(f"Successful conversions: {len(results['successful'])}")
        print(f"Failed conversions:     {len(results['failed'])}")
        print(f"Skipped items:          {len(results['skipped'])}")
        print("-------------------------")

    except MissingDependencyError as e: # Should be caught by the initial check in main_cli
        print(f"Critical Error: {e}")
        print("Please ensure Pillow is installed correctly.")
        sys.exit(1)
    except InvalidFolderPathError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except FolderPermissionError as e:
        print(f"Permission Error: {e}")
        sys.exit(1)
    except Exception as e: # Catch-all for other unexpected errors from the core function
        print(f"An unexpected critical error occurred during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # This script converts PNG images in a specified folder to WebP format.
    #
    # How to run from the command line:
    #   python image_converter.py /path/to/your/images
    #
    # Example:
    #   python image_converter.py ./my_pictures
    #
    # Make sure you have Pillow installed (if not, the script will prompt):
    #   pip install Pillow
    main_cli()
