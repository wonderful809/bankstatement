# Bank Statement PDF → CSV Converter

Lightweight Flask app that converts bank statement PDFs to CSV. Handles both native (text-based) PDFs via pdfplumber and scanned (image) PDFs via pdf2image + pytesseract OCR. Prioritizes security: uploaded PDFs are processed in-memory or deleted immediately after conversion; no user data is stored.

## ⚡ Quick Start

**NEW USERS:** Follow the detailed [**SETUP_GUIDE.md**](./SETUP_GUIDE.md) for step-by-step instructions.

## ⚠️ Prerequisites (IMPORTANT!)

### Required Software:
- ✅ **Python 3.8+** 
- 🔴 **Tesseract OCR** - REQUIRED for scanned PDFs ([Installation Guide](./TESSERACT_INSTALLATION.md))
- 🟡 **Poppler** - Optional but recommended ([See Setup Guide](./SETUP_GUIDE.md))

**If you see "Tesseract not found" error:** → Read [TESSERACT_INSTALLATION.md](./TESSERACT_INSTALLATION.md)

## 📦 Installation

### 1. Clone and Setup

```powershell
cd "C:\Users\gadip\OneDrive\Documents\MERN\bankstatement converter"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file from the example:
```powershell
Copy-Item .env.example .env
```

Edit `.env` and set at minimum:
```bash
# Generate a strong secret key
FLASK_SECRET_KEY=your-secret-key-here

# Set paths to external tools (Windows example)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
POPPLER_PATH=C:\path\to\poppler\Library\bin
```

**💡 Tip**: Generate a secure secret key:
```python
python -c "import secrets; print(secrets.token_hex(32))"
```

See `ENV_CONFIG_GUIDE.md` for complete configuration reference.

### 3. Install External Tools (Required for OCR)

#### Tesseract OCR

Tesseract is required to process scanned (image-based) PDFs.

1. **Download:** https://github.com/UB-Mannheim/tesseract/wiki
2. **Install** the executable (recommended: use the installer and check "Add to PATH")
3. **Verify installation:**
   ```powershell
   tesseract --version
   ```
4. **Alternative:** If not on PATH, set environment variable:
   ```powershell
   $env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

#### Poppler

Poppler is required to convert PDF pages to images before OCR processing.

1. **Download:** https://github.com/oschwartz10612/poppler-windows/releases
2. **Extract** the ZIP file to a location (e.g., `C:\poppler`)
3. **Add the `bin` folder to your PATH:**
   - Add `C:\poppler\Library\bin` to your system PATH environment variable
   - Or temporarily in PowerShell:
     ```powershell
     $env:PATH += ";C:\poppler\Library\bin"
     ```
4. **Verify installation:**
   ```powershell
   pdftoppm -h
   ```
5. **Alternative:** Set environment variable:
   ```powershell
   $env:POPPLER_PATH = "C:\poppler\Library\bin"
   ```

**Note:** Without Tesseract and Poppler, the app can still process native (text-based) PDFs, but will fail on scanned PDFs with a clear error message.

## Running the App

### Basic App (Simple Interface)
```powershell
.\venv\Scripts\Activate.ps1
python app.py
```

### SaaS App (Full Features with Database)
```powershell
.\venv\Scripts\Activate.ps1
python app_saas.py
```

Then open: http://127.0.0.1:5000

**Note**: Configuration is automatically loaded from `.env` file. No need to set environment variables manually!

## Configuration

All configuration is managed through the `.env` file. Key settings:

| Setting | Description | Default |
|---------|-------------|---------|
| `FLASK_SECRET_KEY` | Secret key for sessions | (required) |
| `MAX_CONTENT_LENGTH` | Max upload size in bytes | 16777216 (16MB) |
| `TESSERACT_CMD` | Path to Tesseract executable | (auto-detect) |
| `POPPLER_PATH` | Path to Poppler bin directory | (auto-detect) |
| `FILE_CLEANUP_HOURS` | Hours before file deletion | 1 |
| `RATELIMIT_DEFAULT` | API rate limit | 10 per minute |

See `ENV_CONFIG_GUIDE.md` for complete configuration documentation.

## Security Notes

- This project intentionally does not persist uploaded PDFs. Files are removed after processing to meet strict privacy requirements.
- No customer data is stored on the server.
- For production, run behind a WSGI server (gunicorn) and enable HTTPS.

## Architecture

- **Backend:** Flask (Python)
- **PDF Processing:** pdfplumber (native text), pytesseract + pdf2image (OCR)
- **Frontend:** HTML/CSS/JavaScript
- **Security:** Stateless, immediate file deletion after processing
