***

# PDF Blur Tool

> A desktop PDF redaction tool built with Python and PyQt6. Visually select and blur sensitive content on any page via a drag-and-drop interface, then export the sanitized document instantly.

## 🚀 Features

*   **Drag & Drop Support:** simply drop a PDF file into the window to start.
*   **Visual Redaction:** Click and drag to draw a box around text or images.
*   **Instant Feedback:** The selected area is blurred immediately upon release.
*   **Page Navigation:** Seamlessly move between pages to redact the whole document.
*   **Export:** Save the modified pages as a new, high-quality PDF.

---

## 🛠️ Prerequisites

This application requires **Python 3.6+** and a system utility called **Poppler** (used to read/convert PDFs).

### 1. Install System Dependency: Poppler
The application **will not work** without Poppler installed on your OS.

#### 🪟 Windows
1.  Download the latest binary from [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/) (Look for `Release-xx.xx.xx-0.zip`).
2.  Extract the ZIP file.
3.  Move the folder to a stable location (e.g., `C:\Program Files\poppler`).
4.  **Important:** Add the `bin` folder to your System PATH:
    *   Search "Edit environment variables for your account" in Windows Start.
    *   Edit the `Path` variable.
    *   Click "New" and add the path to the bin folder (e.g., `C:\Program Files\poppler\Library\bin`).

#### 🍎 macOS
If you have Homebrew installed:
```bash
brew install poppler
```

#### 🐧 Linux (Debian/Ubuntu)
```bash
sudo apt-get install poppler-utils
```

---

## 📦 Installation

1.  **Clone the repository** (or download the files):
    ```bash
    git clone https://github.com/spylovec2/pdf-blur-tool.git
    cd pdf_blur_tool
    ```

2.  **Create a Virtual Environment** (Optional but recommended):
    ```bash
    # Windows
    python -m venv venv
    venv\Scripts\activate

    # Mac/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python Libraries**:
    ```bash
    pip install -r requirements.txt
    ```

---

## 🖥️ Usage

1.  **Start the application**:
    ```bash
    python pdf_blur_tool.py
    ```

2.  **Load a PDF**:
    *   Drag a PDF file directly onto the window.
    *   Or click the **Open PDF** button in the toolbar.

3.  **Redact Information**:
    *   Hold **Left Click** and drag over the sensitive area.
    *   Release the mouse to apply the blur.

4.  **Save**:
    *   Click **Save PDF** to export your blurred document.

---

## ❓ Troubleshooting

**"Unable to get page count" / "Poppler not found"**
> This indicates that Poppler is not installed or the `bin` folder is not in your System PATH. Please double-check the [Prerequisites](#1-install-system-dependency-poppler) section. On Windows, try restarting your terminal or computer after adding the PATH.

**The PDF is pixelated**
> The tool converts PDF pages to images to allow for pixel-perfect blurring. The default quality is set for standard documents. You can increase the resolution in the source code by adding `dpi=200` or `dpi=300` to the `convert_from_path` function.

---

## 📚 Tech Stack

*   **[PyQt6](https://pypi.org/project/PyQt6/)**: For the GUI and Graphics Scene.
*   **[pdf2image](https://pypi.org/project/pdf2image/)**: To render PDF pages as editable images.
*   **[Pillow (PIL)](https://python-pillow.org/)**: For image processing and Gaussian Blur filters.