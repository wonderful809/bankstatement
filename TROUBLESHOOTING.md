# 🔧 Troubleshooting Guide

Common issues and solutions for the Bank Statement PDF to CSV Converter.

---

## 🚨 "Tesseract not found" Error

**Symptom:**
```
❌ Tesseract OCR not found!
To process scanned PDFs, install Tesseract...
```

**Cause:** Tesseract OCR is not installed on your system.

**Solution:**
1. Install Tesseract OCR - See [TESSERACT_INSTALLATION.md](./TESSERACT_INSTALLATION.md)
2. After installation, restart your Flask app
3. Test with: `tesseract --version`

**Quick Fix (Temporary):**
- Set environment variable:
  ```powershell
  $env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
  ```

---

## 📄 "0 transactions extracted" Issue

**Symptom:** CSV file is created but has only headers, no data rows.

**Possible Causes:**

### Cause 1: Tesseract Not Installed (Most Common)
**Solution:** Install Tesseract - See above

### Cause 2: PDF is Blank or Corrupted
**Solution:** 
- Open PDF manually and verify it contains data
- Try a different PDF file

### Cause 3: Bank Statement Format Not Recognized
**Solution:**
- Run diagnostic: `python test_conversion.py`
- Check the extracted text format
- Adjust regex patterns in `processor.py` if needed

### Cause 4: Date/Amount Patterns Don't Match
**Solution:**
- Look at `processor.py` lines 85-110 (DATE_PATTERNS and AMOUNT_PATTERN)
- Add your bank's specific format
- Example:
  ```python
  DATE_PATTERNS = [
      r'\b\d{2}/\d{2}/\d{4}\b',  # MM/DD/YYYY
      r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
      # Add your custom pattern here
  ]
  ```

---

## 🔒 "Unable to get page count" Error

**Symptom:** Error when trying to upload PDF.

**Cause:** PDF file is encrypted, password-protected, or corrupted.

**Solution:**
1. Remove password protection from PDF
2. Try re-downloading or re-exporting the PDF
3. Use a PDF repair tool if corrupted

---

## 🚫 "Page limit exceeded" Message

**Symptom:**
```
⚠️ You have used all 5 free pages this month!
Please upgrade to a paid plan to continue converting.
```

**This is expected behavior!** The free plan has a 5 pages/month limit.

**Solutions:**

### Option 1: Wait for Monthly Reset
- Usage resets automatically on the 1st of each month
- Check your usage: Look at homepage banner

### Option 2: Upgrade Plan (Simulation)
```powershell
# POST to upgrade endpoint
curl -X POST http://localhost:5000/upgrade-plan -d "plan=premium"
```

### Option 3: Reset for Testing
```powershell
# Reset usage (development only)
curl -X POST http://localhost:5000/reset-usage
```

---

## 🐌 "Conversion is very slow"

**Symptom:** PDF takes 30+ seconds to convert.

**Cause:** Scanned PDFs require OCR, which is CPU-intensive.

**Normal Processing Times:**
- Text-based PDF: 0.5-2 seconds ⚡
- Scanned PDF (1 page): 3-10 seconds 🐌
- Scanned PDF (10 pages): 30-60 seconds 🐢

**Solutions:**

### Optimize Tesseract
- Make sure you're using latest Tesseract version
- Use faster OCR mode (trade accuracy for speed)

### Optimize PDF
- Reduce image DPI before scanning (300 DPI is good balance)
- Use text-based PDFs when possible

### Hardware
- OCR is CPU-bound, faster processor = faster conversion
- Consider cloud deployment with better CPU

---

## 💥 Flask App Won't Start

**Symptom:**
```
Address already in use
Port 5000 is already allocated
```

**Cause:** Another process is using port 5000.

**Solutions:**

### Option 1: Kill Existing Process
```powershell
# Find process using port 5000
netstat -ano | findstr :5000

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Option 2: Use Different Port
```powershell
# Edit app.py, change last line:
app.run(debug=True, port=5001)  # Use port 5001 instead
```

---

## 📦 "Module not found" Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'pdfplumber'
```

**Cause:** Python packages not installed.

**Solution:**
```powershell
# Make sure you're in the project directory
cd "C:\Users\gadip\OneDrive\Documents\MERN\bankstatement converter"

# Install all requirements
pip install -r requirements.txt

# Verify installation
pip list
```

---

## 🔄 "Import Error" After Code Changes

**Symptom:**
```
ImportError: cannot import name 'function_name'
```

**Cause:** Code changes broke imports or function was removed.

**Solution:**
1. Check function exists in the file you're importing from
2. Restart Flask app (Ctrl+C then `python app.py`)
3. Clear Python cache:
   ```powershell
   # Remove __pycache__ folders
   Get-ChildItem -Include __pycache__ -Recurse -Force | Remove-Item -Force -Recurse
   ```

---

## 🌐 "404 Not Found" on Routes

**Symptom:** Clicking links gives "404 Not Found" error.

**Cause:** Route not defined or Flask app not restarted.

**Solution:**
1. Check route exists in `app.py`
2. Restart Flask app
3. Clear browser cache (Ctrl+Shift+R)

---

## 📊 "Database" or "Session" Errors

**Symptom:**
```
KeyError: 'user_id'
RuntimeError: Working outside of request context
```

**Cause:** Session not configured properly.

**Solution:**
1. Make sure `FLASK_SECRET_KEY` is set in environment
2. Check `.env` file exists and is loaded
3. Generate new secret key:
   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

---

## 🎨 CSS/Styling Not Loading

**Symptom:** Website shows plain HTML, no styling.

**Cause:** Static files not being served correctly.

**Solution:**
1. Check file exists: `static/styles_enhanced.css`
2. Clear browser cache (Ctrl+Shift+R)
3. Check Flask is serving static files:
   ```python
   # In app.py, verify this line exists:
   app = Flask(__name__, static_folder='static', template_folder='templates')
   ```

---

## 🧪 Diagnostic Commands

### Check All Dependencies

```powershell
# Python version
python --version

# Tesseract version (should show version, not error)
tesseract --version

# Python packages
pip list | Select-String "pdfplumber|pytesseract|pdf2image|Flask|Pillow"

# Test conversion
python test_conversion.py
```

### Check Flask App

```powershell
# Start in debug mode
$env:FLASK_DEBUG = "1"
python app.py

# Check if server is running
curl http://localhost:5000

# Check specific route
curl http://localhost:5000/api/stats
```

### Check File Permissions

```powershell
# Check uploads directory exists and is writable
Test-Path "uploads" -PathType Container
New-Item -ItemType File -Path "uploads\test.txt" -Force
Remove-Item "uploads\test.txt"
```

---

## 🆘 Still Having Issues?

### Step 1: Run Full Diagnostics
```powershell
python test_conversion.py
```

### Step 2: Check Logs
- Look at Flask console output
- Check for error messages
- Note exact error text

### Step 3: Review Documentation
- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - Setup instructions
- [TESSERACT_INSTALLATION.md](./TESSERACT_INSTALLATION.md) - OCR setup
- [ISSUE_DIAGNOSIS.md](./ISSUE_DIAGNOSIS.md) - Common issues

### Step 4: Test with Simple Case
```powershell
# Test with a text-based PDF (no OCR needed)
# Should work even without Tesseract
```

---

## 📚 Related Documentation

- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - Complete setup instructions
- [TESSERACT_INSTALLATION.md](./TESSERACT_INSTALLATION.md) - OCR installation
- [ACCURACY_IMPROVEMENTS.md](./ACCURACY_IMPROVEMENTS.md) - Parsing details
- [PAGE_LIMIT_FEATURE.md](./PAGE_LIMIT_FEATURE.md) - Usage limits
- [README.md](./README.md) - Main documentation

---

## 💡 Pro Tips

1. **Always check logs first** - They usually tell you exactly what's wrong
2. **Use diagnostic script** - `python test_conversion.py` catches most issues
3. **Test incrementally** - Start with simple text-based PDFs, then try scanned
4. **Keep dependencies updated** - Run `pip install -U -r requirements.txt`
5. **Restart after changes** - Python imports are cached, restart Flask after code changes
