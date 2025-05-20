"""
image_converter.py

Purpose:
  Converts PNG images to WebP format within a specified folder.

Description:
  This script iterates through all files in a user-provided folder.
  For each PNG file (.png, .PNG), it attempts to convert it to the
  WebP format, saving the new .webp file in the same folder.
  The script handles common errors such as missing folders,
  permission issues, and problematic image files.

Dependencies:
  - Pillow: The Python Imaging Library (PIL) fork.
    Install using: pip install Pillow

Usage:
  python image_converter.py <path_to_folder_with_images>

Example:
  python image_converter.py ./my_pictures
"""
import argparse
import os

try:
    from PIL import Image
except ModuleNotFoundError:
    print(
        "Error: The Pillow library is not installed. This script requires Pillow for image conversion.\n"
        "Please install it by running: pip install Pillow\n"
        "If you are using a virtual environment, ensure it's activated before installing."
    )
    # Set PIL_Image to None so the script can inform the user and exit gracefully in main().
    PIL_Image = None
else:
    PIL_Image = Image


def main():
    parser = argparse.ArgumentParser(
        description="Converts PNG images in a specified folder to WebP format.",
        epilog="Example: python image_converter.py ./my_images"
    )
    parser.add_argument(
        "folder_path",
        help="Path to the folder containing PNG images to be converted."
    )
    # TODO: Add an option to delete original PNG files after conversion.
    # parser.add_argument(
    #     "--delete-original",
    #     action="store_true",
    #     help="Delete original PNG files after successful conversion."
    # )

    args = parser.parse_args()

    folder_path = args.folder_path
    # delete_original = args.delete_original # Placeholder for when the feature is implemented

    if not os.path.isdir(folder_path):
        print(f"Error: The provided path '{folder_path}' is not a valid directory or was not found.")
        sys.exit(1) # Exit with a non-zero code

    if PIL_Image is None:
        # The ModuleNotFoundError message for Pillow is printed at import time.
        # Adding a note here before exiting.
        print("Exiting script because the Pillow library is missing.")
        sys.exit(1) # Exit with a non-zero code

    print(f"Starting image processing in folder: '{folder_path}'")
    try:
        filenames = os.listdir(folder_path)
    except PermissionError:
        print(f"Error: Permission denied to read files from folder '{folder_path}'. Please check permissions.")
        sys.exit(1) # Exit with a non-zero code
    except Exception as e:
        print(f"Error: Could not list files in folder '{folder_path}': {e}")
        sys.exit(1) # Exit with a non-zero code

    for filename in filenames:
        file_path = os.path.join(folder_path, filename)
        
        # Skip if not a file (e.g., it's a subdirectory)
        if not os.path.isfile(file_path):
            print(f"Info: Skipping '{filename}' (it is a directory or not a regular file).")
            continue

        if filename.lower().endswith(".png"):
            name_without_ext, _ = os.path.splitext(filename)
            webp_filename = name_without_ext + ".webp"
            webp_filepath = os.path.join(folder_path, webp_filename)

            try:
                # Attempt to open the image
                img = PIL_Image.open(file_path)
                try:
                    # Attempt to save the image in WebP format
                    img.save(webp_filepath, "webp")
                    print(f"Success: Converted '{filename}' to '{webp_filename}'")
                except PermissionError:
                    print(f"Error: Permission denied to save '{webp_filename}' in '{folder_path}'. Check write permissions for the folder.")
                except Exception as e_save:
                    print(f"Error: Failed to save '{webp_filename}'. Reason: {e_save}")
            except PermissionError:
                print(f"Error: Permission denied to read '{filename}'. Check read permissions for this file.")
            except FileNotFoundError:
                # This case should ideally be rare given os.listdir and os.path.isfile,
                # but good for robustness (e.g. file deleted mid-operation).
                print(f"Error: File '{filename}' was not found during processing.")
            except Exception as e_open: # Catches PIL.UnidentifiedImageError and other PIL/general errors
                print(f"Error: Could not open or process '{filename}'. It may not be a valid PNG or is corrupted. Details: {e_open}")
        else:
            print(f"Info: Skipping '{filename}' (not a PNG image).")

if __name__ == "__main__":
    # This script converts PNG images in a specified folder to WebP format.
    #
    # How to run from the command line:
    #   python image_converter.py /path/to/your/images
    #
    # Example:
    #   python image_converter.py ./my_pictures
    #
    # Make sure you have Pillow installed:
    #   pip install Pillow
    main()
