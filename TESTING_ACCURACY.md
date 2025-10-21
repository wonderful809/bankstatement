# Testing Guide for Enhanced PDF to CSV Conversion

## Quick Test Checklist

### ✅ Test Scenarios

#### 1. **Text-Based PDF with Tables**
- Upload a standard bank statement PDF
- Expected: High accuracy (95-99%)
- Verify: Dates standardized, amounts cleaned, no headers in output

#### 2. **Scanned/Photographed PDF**
- Upload a scanned bank statement
- Expected: Good accuracy (80-95%)
- Verify: OCR successfully extracted text, transactions detected

#### 3. **Multi-line Descriptions**
- Upload statement with long transaction descriptions
- Expected: Descriptions merged correctly, not split into multiple rows
- Verify: Each transaction is one row in CSV

#### 4. **Various Date Formats**
- Test PDFs with different date formats:
  - `12/31/2023`
  - `2023-12-31`
  - `31 Dec 2023`
  - `Dec 31, 2023`
- Expected: All dates converted to `YYYY-MM-DD` format in CSV

#### 5. **Currency & Amount Variations**
- Test transactions with:
  - `$1,234.56` (formatted with currency)
  - `(123.45)` (negative in parentheses)
  - `-123.45` (negative with minus sign)
  - `1234.56` (plain number)
- Expected: All amounts cleaned (no $, commas preserved logic)

#### 6. **Headers and Footers**
- Upload statement with headers, page numbers, bank info
- Expected: Only transaction rows in CSV, no headers/footers

---

## Sample Test Data

### Create Test PDF Content

**Example 1: Standard Format**
```
Date          Description                    Amount
12/01/2023    Amazon Purchase               -$45.99
12/02/2023    Salary Deposit                $2,500.00
12/03/2023    Electric Bill                 ($125.50)
```

**Expected CSV Output:**
```csv
date,description,amount
2023-12-01,Amazon Purchase,-45.99
2023-12-02,Salary Deposit,2500.00
2023-12-03,Electric Bill,-125.50
```

**Example 2: Multi-line Description**
```
Date          Description                    Amount
12/05/2023    Transfer to John Smith        -$500.00
              Account ending in 1234
              Ref: INV-2023-001
12/06/2023    Gas Station                   -$55.00
```

**Expected CSV Output:**
```csv
date,description,amount
2023-12-05,Transfer to John Smith Account ending in 1234 Ref: INV-2023-001,-500.00
2023-12-06,Gas Station,-55.00
```

---

## Testing Steps

### 1. Start the Application
```powershell
python app.py
```

### 2. Access the Web Interface
Navigate to: `http://127.0.0.1:5000`

### 3. Upload Test PDF
- Click "Choose PDF File"
- Select your test bank statement PDF
- Click "Convert to CSV"

### 4. Download and Verify CSV
- Open the downloaded CSV file
- Check the following:
  - ✓ Dates are in `YYYY-MM-DD` format
  - ✓ Amounts are clean numbers (no `$` symbols)
  - ✓ Negative amounts are correctly identified
  - ✓ Descriptions are complete (multi-line merged)
  - ✓ No header rows in the data
  - ✓ No page numbers or footer text

### 5. Check Conversion Stats
- Verify the stats counter increases after each conversion
- Check conversion history shows your recent conversion

---

## Common Issues & Solutions

### Issue 1: "Tesseract not found"
**Solution**: Install Tesseract OCR or set environment variable:
```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### Issue 2: "Poppler not available"
**Solution**: Set Poppler path:
```powershell
$env:POPPLER_PATH = "C:\path\to\poppler\bin"
```

### Issue 3: Low accuracy on scanned PDFs
**Possible causes**:
- Poor image quality (use higher resolution scan)
- Handwritten text (OCR works best with printed text)
- Skewed/rotated pages

**Solutions**:
- Scan at minimum 300 DPI
- Ensure pages are straight
- Use clean, high-contrast scans

### Issue 4: Dates not recognized
**Check**:
- Is the date format extremely unusual?
- Add new pattern to `DATE_PATTERNS` in `processor.py`

### Issue 5: Amounts not parsed
**Check**:
- Are amounts in unusual format?
- Modify `AMOUNT_PATTERN` regex if needed

---

## Accuracy Metrics to Track

### For Each Test PDF:
1. **Total Transactions in PDF**: _______
2. **Transactions Extracted**: _______
3. **Accuracy Rate**: _______ %
4. **Dates Correctly Formatted**: _______
5. **Amounts Correctly Parsed**: _______
6. **Multi-line Descriptions Merged**: _______
7. **Headers/Footers Filtered**: Yes / No

### Target Benchmarks:
- Text-based PDFs: **95-99% accuracy**
- Scanned PDFs: **80-95% accuracy**
- Table-structured: **95-99% accuracy**

---

## Advanced Testing

### Stress Testing
1. Upload multi-page statements (10+ pages)
2. Upload statements with 100+ transactions
3. Upload mixed format statements

### Edge Cases
1. Statements with no transactions (opening balance only)
2. Statements with special characters in descriptions
3. Foreign currency statements
4. Statements with duplicate transactions

### Performance Testing
1. Measure conversion time for various PDF sizes
2. Test concurrent uploads (multiple users)
3. Monitor memory usage during large file processing

---

## Logging & Debugging

### Check Logs for Extraction Details
The processor now logs:
- Number of tables detected
- Rows extracted from tables
- Rows extracted from text parsing
- Final validated row count

### Example Log Output:
```
INFO: Extracted text-based PDF: 3 tables found
INFO: Extracted 45 rows from tables
INFO: Extracted 45 rows from text parsing
INFO: Final validated rows: 43
INFO: Conversion complete: 43 transactions extracted
```

---

## Regression Testing

Before deploying to production:

1. ✓ Test with previously converted PDFs
2. ✓ Compare new output vs. old output
3. ✓ Verify no breaking changes
4. ✓ Check that accuracy improved, not degraded
5. ✓ Test edge cases that previously failed

---

## Next Steps After Testing

### If Results are Good (95%+ accuracy):
✅ Deploy to production  
✅ Monitor real user conversions  
✅ Collect user feedback  

### If Results Need Improvement:
1. Identify specific failure patterns
2. Add targeted regex patterns
3. Implement bank-specific parsers
4. Consider ML-based approach

---

## Feedback Loop

After testing, document:
1. PDF types that work best
2. PDF types that need improvement
3. Specific bank formats tested
4. Edge cases discovered
5. User feedback on accuracy

This will guide future enhancements to reach even higher accuracy levels.
