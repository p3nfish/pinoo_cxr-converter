# Pinoo CXR Converter

This script is a GUI application for converting Corona Renderer `.cxr` files to other image formats (`.jpg`, `.png`, `.exr`).

## Features

*   **Folder Selection:**
    *   Dropdown menu with the last 5 used folders.
    *   Button to open a folder selection dialog.
    *   Button to clear the current folder and file list.
*   **Drag & Drop:**
    *   Drag and drop `.cxr` files directly into the application window.
    *   Files of other formats are automatically filtered out.
*   **File Selection:**
    *   Select multiple files using a selection box.
*   **Settings Persistence:**
    *   The application saves the following settings between launches:
        *   Last 5 used folders.
        *   Selected output format.
        *   "only BEAUTY" checkbox state.
        *   Path to the `.conf` file.
*   **UI/UX:**
    *   Modern, dark-themed interface with clean layouts and consistent styling.
    *   "Drag&drop .cxr files or choose folder in explorer" placeholder text when the file list is empty.
    *   Visual feedback when dragging files over the application window.

## How to Run

### Pre-built Executable

You can download the pre-built `.exe` file from the following link:

[Download pinoo_CXR-Converter_1.0-alpha.exe](https://github.com/p3nfish/pinoo_cxr-converter/blob/main/dist/pinoo_CXR-Converter_1.0-alpha.exe)

### From Python Source

To run the script from the source code, you need to have Python installed.

1.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the script:**

    ```bash
    python pinoo_script.py
    ```

To build the executable from the source, run the `build.bat` script. This will create a standalone `.exe` file in the `dist` folder.

## Configuration File

The application creates a `pinoo_script.cfg` file in the same directory as the script or executable. This file stores your settings, such as the last used folders and other preferences.

## Donate

If you find this script useful, you can buy me a coffee:

[Donate via Telegram](https://t.me/PinooScript)
