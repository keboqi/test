# PNG to WebP Image Converter

This project provides a tool to convert PNG images to the WebP format. It offers both a command-line interface (CLI) for batch processing and a graphical user interface (GUI) for ease of use.

## Project Overview

The converter iterates through a specified folder, identifies PNG images (files ending with `.png` or `.PNG`), and converts them into WebP format, saving the new `.webp` files in the same folder.

The project consists of two main Python scripts:
-   `image_converter.py`: Contains the core conversion logic and provides the command-line interface.
-   `image_converter_ui.py`: Provides a Tkinter-based graphical user interface that uses the logic from `image_converter.py`.

## Prerequisites

To run this converter, you will need:

1.  **Python 3.x**: Ensure you have Python 3 installed. You can download it from [python.org](https://www.python.org/).
2.  **Pillow**: The Python Imaging Library (Pillow) is required for image processing.

## Installation

1.  **Download Scripts**: Place both `image_converter.py` and `image_converter_ui.py` in the same directory on your computer.
2.  **Install Pillow**: Open your terminal or command prompt and install Pillow using pip:
    ```bash
    python -m pip install Pillow
    ```
    If you are using a virtual environment, ensure it is activated before running this command.

## Usage

You can use either the command-line interface or the graphical user interface.

### 1. Command-Line Interface (CLI)

The CLI is suitable for batch processing or integrating into other scripts.

-   **How to run**:
    Open your terminal or command prompt, navigate to the directory where you saved the scripts, and run:
    ```bash
    python image_converter.py /path/to/your/image_folder
    ```
    Replace `/path/to/your/image_folder` with the actual path to the folder containing your PNG images.

-   **Example**:
    ```bash
    python image_converter.py ./MyPictures/SummerVacation
    ```
    On Unix-like systems (Linux, macOS), after making the script executable (`chmod +x image_converter.py`), you might also be able to run it directly if the shebang `#!/usr/bin/env python3` is present:
    ```bash
    ./image_converter.py ./MyPictures/SummerVacation
    ```

### 2. Graphical User Interface (GUI)

The GUI provides a user-friendly way to select a folder and convert images. It features a simple window with a "Browse..." button to select an input folder, an entry field to display the selected path, a "Convert to WebP" button, and a scrollable text area for status messages and conversion logs.

-   **How to run**:
    Open your terminal or command prompt, navigate to the directory where you saved the scripts, and run:
    ```bash
    python image_converter_ui.py
    ```
    On Unix-like systems (Linux, macOS), after making the script executable (`chmod +x image_converter_ui.py`), you might also be able to run it directly if the shebang `#!/usr/bin/env python3` is present:
    ```bash
    ./image_converter_ui.py
    ```
    This will open the application window.

-   **Using the GUI**:
    1.  Click the "Browse..." button to open a dialog and select the folder containing your PNG images.
    2.  The selected folder path will appear in the entry field.
    3.  Once a folder is selected, the "Convert to WebP" button will become active.
    4.  Click "Convert to WebP" to start the conversion process. The conversion runs in a separate thread to keep the UI responsive.
    5.  During the conversion, the "Browse..." and "Convert to WebP" buttons will be temporarily disabled.
    6.  Detailed feedback, including progress, any errors encountered during individual file conversions, and a final summary (counts of successful, failed, and skipped files), will be displayed in the scrollable status area.

## Important Note

-   For the GUI (`image_converter_ui.py`) to function correctly, the backend script (`image_converter.py`) **must be present in the same directory**. The UI script imports functionality directly from the backend script.
-   The script currently does not delete original PNG files. This feature might be added in the future.

---
If you encounter any issues, please ensure Python and Pillow are correctly installed and that the folder path provided is valid and accessible.
