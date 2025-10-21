# Tesseract OCR Installation Guide

## ❌ Issue: "Tesseract not found" Error

If you're seeing this error, it means **Tesseract OCR** is not installed on your system. This is required to process **scanned PDFs** (images of documents).

---

## 📥 Windows Installation (Step-by-Step)

### Option 1: Official Installer (Recommended)

1. **Download Tesseract:**
   - Visit: [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
   - Download the latest Windows installer:
     - `tesseract-ocr-w64-setup-5.3.x.exe` (64-bit)
     - OR `tesseract-ocr-w32-setup-5.3.x.exe` (32-bit)

2. **Run the Installer:**
   - Double-click the `.exe` file
   - Follow the installation wizard
   - **Important:** Note the installation path (default is `C:\Program Files\Tesseract-OCR`)

3. **Verify Installation:**
   ```powershell
   # Open PowerShell and run:
   tesseract --version
   ```
   
   If you see version info, installation was successful! ✅

4. **Restart Your Application:**
   - Stop the Flask server (Ctrl+C)
   - Restart: `python app.py`

---

### Option 2: Using Chocolatey (If you have it)

```powershell
choco install tesseract
```

---

### Option 3: Using Scoop (If you have it)

```powershell
scoop install tesseract
```

---

## 🔧 Manual Configuration (If Auto-Detection Fails)

If Tesseract is installed but still not found, manually set the path:

### Method 1: Environment Variable (Permanent)

1. **Find your Tesseract installation path:**
   - Common locations:
     - `C:\Program Files\Tesseract-OCR\tesseract.exe`
     - `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`
     - `C:\Tesseract-OCR\tesseract.exe`

2. **Set environment variable:**
   
   **Windows 10/11:**
   - Press `Win + X` → System
   - Click "Advanced system settings"
   - Click "Environment Variables"
   - Under "User variables" click "New"
   - Variable name: `TESSERACT_CMD`
   - Variable value: `C:\Program Files\Tesseract-OCR\tesseract.exe` (your actual path)
   - Click OK

3. **Restart your terminal and application**

### Method 2: PowerShell Session (Temporary)

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
python app.py
```

---

## 🐧 Linux Installation

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install tesseract-ocr

# Fedora/RHEL
sudo dnf install tesseract

# Arch Linux
sudo pacman -S tesseract
```

---

## 🍎 macOS Installation

```bash
# Using Homebrew
brew install tesseract
```

---

## ✅ Testing After Installation

Run this test script:

```powershell
python test_conversion.py
```

You should see:
```
✅ OCR extracted X characters
✅ Extracted Y transactions
```

---

## 🔍 Troubleshooting

### Issue: "tesseract: command not found"

**Solution 1:** Add Tesseract to PATH
1. Find installation directory (e.g., `C:\Program Files\Tesseract-OCR`)
2. Add to System PATH:
   - Win + X → System → Advanced → Environment Variables
   - Edit "Path" under System variables
   - Add: `C:\Program Files\Tesseract-OCR`
   - Click OK, restart terminal

**Solution 2:** Use full path in code
- Set `TESSERACT_CMD` environment variable (see above)

### Issue: "Error opening data file..."

Tesseract needs language data files. Reinstall using the official installer (includes language packs).

---

## 📚 Additional Resources

- **Official Documentation:** [https://tesseract-ocr.github.io/](https://tesseract-ocr.github.io/)
- **GitHub Releases:** [https://github.com/tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract)
- **Windows Builds:** [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

---

## 🚀 Quick Start (After Installation)

1. **Restart Flask app:**
   ```powershell
   python app.py
   ```

2. **Upload a PDF:**
   - Go to [http://localhost:5000](http://localhost:5000)
   - Upload a bank statement PDF
   - Conversion should now work! ✅

---

## 💡 Alternative: Use Text-Based PDFs

If you can't install Tesseract right now, the app can still process **text-based PDFs** (PDFs with selectable text):

- ✅ **Works without Tesseract:** PDFs created digitally (not scanned)
- ❌ **Needs Tesseract:** Scanned documents, photos of papers

To test, try uploading a PDF where you can select/copy the text.
