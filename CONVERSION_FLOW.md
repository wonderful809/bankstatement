# 🎯 Enhanced PDF to CSV Conversion Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Uploads PDF File                       │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              PDF Type Detection (is_pdf_text_based)              │
│  • Checks if text is directly extractable from PDF              │
│  • Tests first 2 pages for text content                         │
└─────────┬───────────────────────────────────────────┬───────────┘
          │                                           │
   TEXT-BASED PDF                              SCANNED/IMAGE PDF
          │                                           │
          ▼                                           ▼
┌─────────────────────────────┐       ┌──────────────────────────┐
│ extract_text_pdf_enhanced() │       │   extract_text_ocr()     │
│ • Extract raw text          │       │ • Convert PDF to images  │
│ • Extract table structures  │       │ • DPI: 300 (high quality)│
│ • Returns: text + tables    │       │ • Grayscale conversion   │
└─────────┬───────────────────┘       │ • OCR with Tesseract     │
          │                           │ • Config: --oem 3 --psm 6│
          │                           └────────┬─────────────────┘
          │                                    │
          └────────────┬───────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│         parse_bank_statement_to_rows(text, tables_data)         │
│                                                                  │
│  ┌───────────────────── STRATEGY 1 ─────────────────────────┐  │
│  │        extract_from_tables(tables_data)                   │  │
│  │  • Process pdfplumber table structures                    │  │
│  │  • Detect header rows (skip "Date", "Description", etc.)  │  │
│  │  • Identify date column (first 3 cols, regex match)       │  │
│  │  • Identify amount column (last 3 cols, $ patterns)       │  │
│  │  • Merge middle columns as description                    │  │
│  │  • Apply standardize_date() and clean_amount()            │  │
│  │  • Filter headers/footers                                 │  │
│  │  ✓ Highest accuracy method                                │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                          │                                       │
│              ┌───────────▼─────────────┐                        │
│              │ Tables Found & Valid?   │                        │
│              └───┬─────────────────┬───┘                        │
│                YES               NO                              │
│                  │                 │                             │
│         ┌────────▼────────┐        │                            │
│         │ Use Table Data  │        │                            │
│         └────────┬────────┘        │                            │
│                  │                 │                             │
│                  │    ┌────────────▼─────────────────────────┐  │
│                  │    │    STRATEGY 2 (Fallback)             │  │
│                  │    │  parse_text_transactions(text)       │  │
│                  │    │  • Line-by-line analysis             │  │
│                  │    │  • Regex pattern matching:           │  │
│                  │    │    - DATE_PATTERNS (8+ formats)      │  │
│                  │    │    - AMOUNT_PATTERN (currency/neg)   │  │
│                  │    │  • Detect transaction start (date)   │  │
│                  │    │  • Multi-line description merging    │  │
│                  │    │  • Extract amount from line end      │  │
│                  │    │  • Filter headers/footers            │  │
│                  │    │  • Apply cleaning functions          │  │
│                  │    └────────┬─────────────────────────────┘  │
│                  │             │                                │
│                  └─────────┬───┘                                │
│                            │                                    │
│                            ▼                                    │
│              ┌──────────────────────────┐                       │
│              │   Data Validation        │                       │
│              │ • Filter rows without    │                       │
│              │   date OR amount         │                       │
│              │ • Clean descriptions     │                       │
│              │ • Remove extra spaces    │                       │
│              └─────────┬────────────────┘                       │
│                        │                                        │
│                        ▼                                        │
│              ┌──────────────────────────┐                       │
│              │  Validated Transactions  │                       │
│              └──────────┬───────────────┘                       │
└─────────────────────────┼───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Format Standardization                        │
│  • Dates: All converted to YYYY-MM-DD (ISO format)              │
│  • Amounts: Currency symbols removed, negatives normalized       │
│  • Descriptions: Trimmed, spaces normalized                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              rows_to_csv(rows, output_path)                      │
│  • Write CSV with headers: date, description, amount            │
│  • UTF-8 encoding for special characters                        │
│  • Create temporary file with 'bs_' prefix                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              User Downloads Clean CSV File                       │
│  ✓ Standardized dates (YYYY-MM-DD)                              │
│  ✓ Clean amounts (no symbols, proper negatives)                 │
│  ✓ Complete descriptions (multi-line merged)                    │
│  ✓ No headers/footers                                           │
│  ✓ Validated data only                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Processing Pipeline

### Step 1: Date Standardization
```
Input Examples:
  12/31/2023      →  2023-12-31
  2023-12-31      →  2023-12-31  (already ISO)
  31 Dec 2023     →  2023-12-31
  Dec 31, 2023    →  2023-12-31
  15-12-2023      →  2023-12-15
  
Process:
  1. Try each date format pattern
  2. Parse with datetime.strptime()
  3. Convert to ISO format (YYYY-MM-DD)
  4. If no match, keep original
```

### Step 2: Amount Cleaning
```
Input Examples:
  $1,234.56       →  1234.56
  (125.50)        →  -125.50
  -$99.00         →  -99.00
  £500.00         →  500.00
  €1.234,56       →  1234.56
  
Process:
  1. Remove currency symbols ($ £ € ¥)
  2. Detect parentheses → negative
  3. Remove thousand separators (,)
  4. Validate numeric format
  5. Keep decimal point
```

### Step 3: Description Assembly
```
Line 1: 12/15/2023  Transfer to Account     -$500.00
Line 2:             Account ending in 1234
Line 3:             Ref: INV-2023-001
Line 4: 12/16/2023  Gas Station              -$55.00

Process:
  1. Detect date at line start → new transaction
  2. No date → continuation of previous
  3. Merge continuation lines with space
  4. Trim extra whitespace
  5. Result: "Transfer to Account Account ending in 1234 Ref: INV-2023-001"
```

---

## Pattern Recognition Details

### Date Patterns (Regex)
```regex
1. \b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b
   Matches: 12/31/2023, 31-12-2023, 1/1/2023

2. \b(\d{4}[-/]\d{2}[-/]\d{2})\b
   Matches: 2023-12-31, 2023/12/31

3. \b(\d{1,2}\s+(?:Jan|Feb|...|Dec)[a-z]*\s+\d{4})\b
   Matches: 31 Dec 2023, 1 January 2023

4. \b((?:Jan|Feb|...|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b
   Matches: Dec 31, 2023, December 31 2023
```

### Amount Patterns (Regex)
```regex
[\$£€]?\s*[\-\(]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*[\)]?

Breakdown:
  [\$£€]?           Optional currency symbol
  \s*               Optional whitespace
  [\-\(]?           Optional negative sign or opening parenthesis
  \s*               Optional whitespace
  \d{1,3}           1-3 digits (hundreds place)
  (?:,\d{3})*       Optional thousands groups (,123)
  (?:\.\d{2})?      Optional decimal with 2 digits
  \s*               Optional whitespace
  [\)]?             Optional closing parenthesis

Matches:
  $1,234.56  →  Yes
  (125.50)   →  Yes
  -99.00     →  Yes
  £500       →  Yes
  1234.56    →  Yes
  ABC        →  No
```

### Header/Footer Detection
```
Keywords to Ignore:
  - date, description, amount, balance, transaction
  - page, statement, account, period
  - opening, closing, total, subtotal
  - continued, carry forward

Logic:
  1. Convert line to lowercase
  2. Count keyword matches
  3. If 2+ keywords OR line is very short → header/footer
  4. Check for page numbers pattern
  5. Skip if identified
```

---

## Quality Assurance

### Validation Rules
```python
For each extracted row:
  ✓ Must have date OR amount (at least one)
  ✓ Description should not be empty (fill with line if needed)
  ✓ Date should match known formats
  ✓ Amount should be numeric (after cleaning)
  ✓ No header keywords in date field
  ✓ Row should not be page number line
```

### Confidence Factors
```
High Confidence (95-99%):
  • Text-based PDF with clear tables
  • Well-defined columns
  • Standard date/amount formats
  • Clean headers/footers

Medium Confidence (80-95%):
  • Scanned PDF with good quality
  • Some format variations
  • Minor OCR corrections needed

Low Confidence (<80%):
  • Poor scan quality
  • Handwritten elements
  • Unusual formats
  • Heavy OCR corrections needed
```

---

## Logging Output

### Example Console Log
```
INFO: PDF type detection: text-based
INFO: Extracted text-based PDF: 3 tables found
INFO: Table 1: 15 rows
INFO: Table 2: 20 rows  
INFO: Table 3: 8 rows
INFO: Extracted 43 rows from tables
INFO: Fallback text parsing found: 42 rows
INFO: Using table extraction (more rows)
INFO: Validation: 43 rows → 41 rows (2 filtered)
INFO: Final validated rows: 41
INFO: Conversion complete: 41 transactions extracted
INFO: Output CSV: /tmp/bs_abc123.csv
```

---

## Performance Metrics

### Processing Time (Estimated)

```
Small PDF (1-5 pages, 10-50 transactions):
  Text-based:  0.5-2 seconds
  Scanned:     2-5 seconds

Medium PDF (5-15 pages, 50-200 transactions):
  Text-based:  2-5 seconds
  Scanned:     5-15 seconds

Large PDF (15+ pages, 200+ transactions):
  Text-based:  5-10 seconds
  Scanned:     15-30 seconds
```

### Memory Usage

```
Text-based:  ~50-100 MB per PDF
Scanned:     ~200-500 MB per PDF (due to images)
```

---

## Error Handling

### Graceful Degradation
```
Table Extraction Failed
  ↓
Try Text Parsing
  ↓
Try Line-by-Line
  ↓
Return Best Result (even if partial)
```

### Error Messages
```
ExternalToolError: Tesseract not found
  → Install Tesseract or set TESSERACT_CMD

ExternalToolError: Poppler not available
  → Install Poppler or set POPPLER_PATH

ValueError: Invalid date format
  → Date pattern not recognized (kept as-is)

ValueError: Invalid amount format
  → Amount pattern not recognized (kept as-is)
```

---

*This visual guide demonstrates the complete conversion flow from PDF upload to clean CSV output with all enhancement features.*
