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
    # Expose Pillow's supported formats using the correct API
    SUPPORTED_OPEN_FORMATS = ['WEBP', 'PNG', 'JPEG', 'BMP', 'GIF', 'TIFF']  # Common formats
    SUPPORTED_SAVE_FORMATS = ['WEBP', 'PNG', 'JPEG', 'BMP', 'GIF', 'TIFF']  # Common formats
except ModuleNotFoundError:
    PIL_Image_Module = None # Will be checked by core function
    SUPPORTED_OPEN_FORMATS = []
    SUPPORTED_SAVE_FORMATS = []

# --- Core Logic Function ---
def convert_images_in_folder(folder_path, source_format, dest_format, delete_originals=False):
    """
    Converts images in a specified folder from a source format to a destination format.

    Args:
        folder_path (str): The path to the folder containing images.
        source_format (str): The source image format (e.g., "png", "jpeg").
        dest_format (str): The destination image format (e.g., "webp", "gif").
        delete_originals (bool, optional): If True, original files will be
                                 deleted after successful conversion.
                                 Defaults to False. (This feature is planned
                                 but not yet implemented).

    Returns:
        dict: A dictionary with keys 'successful', 'failed', and 'skipped',
              each containing a list of tuples.
              - 'successful': `[(original_filename, new_filename), ...]`
              - 'failed': `[(filename, error_message_string), ...]`
              - 'skipped': `[(filename, reason_string), ...]`
              Example:
              {
                  'successful': [('image1.jpg', 'image1.png')],
                  'failed': [('image2.bmp', 'Error: Could not open image.')],
                  'skipped': [('notes.txt', 'File is not a JPG image'), # Assuming source_format='jpg'
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

    # Format validation (basic)
    if not source_format or not isinstance(source_format, str):
        raise ValueError("Source format must be a non-empty string.")
    if not dest_format or not isinstance(dest_format, str):
        raise ValueError("Destination format must be a non-empty string.")

    # Normalize formats to lowercase for consistent processing
    source_format_lower = source_format.lower()
    dest_format_lower = dest_format.lower()
    
    # Convert provided formats to uppercase for comparison
    source_format_upper = source_format.upper()
    dest_format_upper = dest_format.upper()

    # Instead of checking against SUPPORTED_OPEN_FORMATS, we'll try to open a file
    # and let Pillow handle the format support check
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

        # Use source_format_lower for filename matching
        if not filename.lower().endswith(f".{source_format_lower}"): 
            results['skipped'].append((filename, f"File is not a {source_format.upper()} image"))
            continue

        name_without_ext, _ = os.path.splitext(filename)
        new_filename = name_without_ext + f".{dest_format_lower}" 
        new_filepath = os.path.join(folder_path, new_filename)

        try:
            # Try to open the image - Pillow will handle format support check
            img = PIL_Image_Module.open(file_path)
            try:
                # Try to save in the new format - Pillow will handle format support check
                img.save(new_filepath, dest_format.upper())
                results['successful'].append((filename, new_filename))
                if delete_originals:
                    # TODO: Implement deletion of original file
                    pass # Placeholder for now
            except PermissionError as e_save:
                results['failed'].append((filename, f"Error: Permission denied to save '{new_filename}'. Check write permissions for the folder. Details: {e_save}"))
            except ValueError as e_save:
                results['failed'].append((filename, f"Error: Failed to save '{new_filename}'. Pillow error: {e_save}"))
            except Exception as e_save:
                results['failed'].append((filename, f"Error: Failed to save '{new_filename}'. Reason: {e_save}"))
        except PermissionError as e_open:
            results['failed'].append((filename, f"Error: Permission denied to read '{filename}'. Check read permissions. Details: {e_open}"))
        except FileNotFoundError:
            results['failed'].append((filename, f"Error: File '{filename}' was not found during processing (it may have been moved/deleted)."))
        except PIL_Image_Module.UnidentifiedImageError:
            results['failed'].append((filename, f"Error: Cannot identify image file '{filename}'. It may not be a valid {source_format.upper()} or is corrupted."))
        except Exception as e_open:
            results['failed'].append((filename, f"Error: Could not open or process '{filename}'. Details: {e_open}"))
            
    return results

# --- Command-Line Interface (CLI) Handling ---
def main_cli():
    """
    Command-line interface entry point.
    Parses arguments, calls `convert_images_in_folder`, and prints a report.
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
        description="Converts images in a specified folder from a source format to a destination format.",
        epilog=f"Example: python {os.path.basename(__file__)} ./my_pictures png webp"
    )
    parser.add_argument(
        "folder_path",
        help="Path to the folder containing images to be converted."
    )
    parser.add_argument(
        "source_format",
        help="Source image format (e.g., png, jpg, tiff)."
    )
    parser.add_argument(
        "dest_format",
        help="Destination image format (e.g., webp, gif, bmp)."
    )
    # TODO: Fully implement --delete-original flag
    # parser.add_argument(
    #     "--delete-original",
    #     action="store_true",
    #     help="Delete original files after successful conversion. (NOT YET IMPLEMENTED)"
    # )

    args = parser.parse_args()
    folder_path = args.folder_path
    source_format = args.source_format
    dest_format = args.dest_format
    # delete_originals_flag = args.delete_original # When implemented

    try:
        print(f"Starting image processing in folder: '{folder_path}'...")
        print(f"Converting from {source_format.upper()} to {dest_format.upper()}...")
        # results = convert_images_in_folder(folder_path, source_format, dest_format, delete_originals_flag) # When implemented
        results = convert_images_in_folder(folder_path, source_format, dest_format) # delete_originals default to False

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
    except ValueError as e: # Catch argument validation errors from core function
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except Exception as e: # Catch-all for other unexpected errors from the core function
        print(f"An unexpected critical error occurred during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # This script converts images in a specified folder from a source format
    # to a destination format.
    #
    # How to run from the command line:
    #   python image_converter.py /path/to/your/images <source_format> <dest_format>
    #
    # Example:
    #   python image_converter.py ./my_pictures png webp
    #   python image_converter.py ./my_drawings jpg png
    #
    # Make sure you have Pillow installed (if not, the script will prompt):
    #   pip install Pillow
    main_cli()
