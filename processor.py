import os
import csv
import tempfile
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import shutil
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExternalToolError(RuntimeError):
    pass


def is_pdf_text_based(path):
    """Check if PDF contains extractable text"""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:2]:
                text = page.extract_text() or ''
                if text.strip():
                    return True
    except Exception:
        return False
    return False


def extract_text_pdf_enhanced(path):
    """Enhanced text extraction with table detection"""
    texts = []
    tables_data = []
    
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            # Extract regular text
            text = page.extract_text() or ''
            texts.append(text)
            
            # Try to extract tables (better for structured data)
            try:
                tables = page.extract_tables()
                if tables:
                    tables_data.extend(tables)
            except Exception as e:
                logger.warning(f"Table extraction failed: {e}")
    
    return '\n'.join(texts), tables_data


def extract_text_ocr(path):
    """OCR extraction with preprocessing for better accuracy"""
    # Check for Tesseract in common Windows installation paths
    tesseract_cmd = os.environ.get('TESSERACT_CMD')
    
    if not tesseract_cmd:
        # Try common Windows installation paths
        common_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe',
        ]
        for path_check in common_paths:
            if os.path.exists(path_check):
                tesseract_cmd = path_check
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                logger.info(f"Found Tesseract at: {tesseract_cmd}")
                break
    else:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    # Verify Tesseract is available
    if not shutil.which(pytesseract.pytesseract.tesseract_cmd or 'tesseract'):
        error_msg = (
            "❌ Tesseract OCR not found!\n\n"
            "To process scanned PDFs, install Tesseract:\n"
            "1. Download from: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "2. Run the installer (tesseract-ocr-w64-setup-5.x.x.exe)\n"
            "3. Restart your application\n\n"
            "OR set TESSERACT_CMD environment variable to the tesseract.exe path\n"
            "Example: set TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
        )
        raise ExternalToolError(error_msg)

    poppler_path = os.environ.get('POPPLER_PATH')
    poppler_bin = poppler_path if poppler_path else None

    try:
        # Convert PDF to images with higher DPI for better accuracy
        images = convert_from_path(path, dpi=300, poppler_path=poppler_bin)
    except Exception as e:
        raise ExternalToolError('Poppler not available or failed to render PDF: ' + str(e))
    
    texts = []
    for img in images:
        # Enhance image for better OCR
        img = img.convert('L')  # Convert to grayscale
        
        # Use better OCR configuration
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, config=custom_config)
        texts.append(text)
    
    return '\n'.join(texts)



# Advanced regex patterns for data extraction
DATE_PATTERNS = [
    r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b',  # MM/DD/YYYY or DD-MM-YYYY
    r'\b(\d{1,2}[-/]\d{1,2})\b',           # MM/DD or DD/MM (without year - common in statements)
    r'\b(\d{4}[-/]\d{2}[-/]\d{2})\b',      # YYYY-MM-DD
    r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',  # DD Mon YYYY
    r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b'  # Mon DD, YYYY
]

AMOUNT_PATTERN = r'[\$£€]?\s*[\-\(]?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*[\)]?'

# Common bank statement headers/footers to ignore
IGNORE_KEYWORDS = [
    'date', 'description', 'amount', 'balance', 'transaction', 
    'page', 'statement', 'account', 'period', 'opening', 'closing',
    'total', 'subtotal', 'continued', 'carry forward'
]


def clean_amount(amount_str):
    """Clean and standardize amount strings"""
    if not amount_str or not amount_str.strip():
        return ''
    
    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[\$£€\s]', '', amount_str)
    
    # Handle parentheses for negative amounts
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    
    # Remove commas (thousands separator)
    cleaned = cleaned.replace(',', '')
    
    # Validate it's a valid number
    try:
        float(cleaned)
        return cleaned
    except ValueError:
        return amount_str.strip()


def standardize_date(date_str):
    """Standardize date formats to YYYY-MM-DD"""
    if not date_str or not date_str.strip():
        return ''
    
    date_str = date_str.strip()
    
    # Handle MM/DD format (no year) - assume current year or statement year
    if re.match(r'^\d{1,2}[/-]\d{1,2}$', date_str):
        # Add current year or you could extract year from statement header
        current_year = datetime.now().year
        date_str = f"{date_str}/{current_year}"
    
    date_formats = [
        '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y',
        '%Y-%m-%d', '%Y/%m/%d',
        '%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y',
        '%b %d, %Y', '%B %d, %Y'
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str.strip(), fmt)
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return date_str


def is_likely_header_or_footer(line):
    """Detect if a line is likely a header or footer"""
    lower_line = line.lower()
    
    # Check for common keywords
    if any(keyword in lower_line for keyword in IGNORE_KEYWORDS):
        # But make sure it's not a transaction description containing these words
        # Headers usually have multiple keywords or are very short
        words = lower_line.split()
        keyword_count = sum(1 for word in words if any(kw in word for kw in IGNORE_KEYWORDS))
        if keyword_count >= 2 or len(words) <= 3:
            return True
    
    # Check for page numbers
    if re.search(r'\bpage\s+\d+\b', lower_line):
        return True
    
    return False


def extract_from_tables(tables_data):
    """Extract transactions from table structures"""
    rows = []
    
    for table in tables_data:
        # Skip empty tables
        if not table:
            continue
        
        # Try to identify header row
        header_idx = -1
        for i, row in enumerate(table[:3]):  # Check first 3 rows
            if row and any('date' in str(cell).lower() for cell in row if cell):
                header_idx = i
                break
        
        # Process data rows
        start_idx = header_idx + 1 if header_idx >= 0 else 0
        for row in table[start_idx:]:
            if not row or len(row) < 2:
                continue
            
            # Filter out None values
            row_data = [str(cell).strip() if cell else '' for cell in row]
            
            # Skip rows that are likely headers/footers
            row_text = ' '.join(row_data)
            if is_likely_header_or_footer(row_text):
                continue
            
            # Try to identify date, description, amount columns
            date_col = ''
            desc_col = ''
            amount_col = ''
            
            # Look for date in first few columns
            for cell in row_data[:3]:
                if any(re.search(pattern, cell, re.IGNORECASE) for pattern in DATE_PATTERNS):
                    date_col = cell
                    break
            
            # Look for amount in last few columns
            for cell in reversed(row_data[-3:]):
                if re.search(AMOUNT_PATTERN, cell):
                    amount_col = cell
                    break
            
            # Everything else is description (merge middle columns)
            date_idx = row_data.index(date_col) if date_col in row_data else -1
            amount_idx = row_data.index(amount_col) if amount_col in row_data else -1
            
            if date_idx >= 0 and amount_idx >= 0:
                desc_parts = []
                for i, cell in enumerate(row_data):
                    if i != date_idx and i != amount_idx and cell:
                        desc_parts.append(cell)
                desc_col = ' '.join(desc_parts)
            elif len(row_data) >= 3:
                date_col = row_data[0]
                desc_col = ' '.join(row_data[1:-1])
                amount_col = row_data[-1]
            else:
                continue
            
            rows.append({
                'date': standardize_date(date_col),
                'description': desc_col,
                'amount': clean_amount(amount_col)
            })
    
    return rows


def parse_text_transactions(text):
    """Parse transactions from plain text using advanced pattern matching"""
    rows = []
    lines = text.split('\n')
    
    current_transaction = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip headers/footers
        if is_likely_header_or_footer(line):
            continue
        
        # Check if line starts with a date (new transaction)
        date_match = None
        for pattern in DATE_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match and match.start() < 20:  # Date should be near the start
                date_match = match
                break
        
        if date_match:
            # Save previous transaction if exists
            if current_transaction:
                rows.append(current_transaction)
            
            # Start new transaction
            date_str = date_match.group(0)
            remaining_text = line[date_match.end():].strip()
            
            # Try to extract amount from the end
            amount_match = re.search(AMOUNT_PATTERN, remaining_text)
            amount_str = ''
            desc_str = remaining_text
            
            if amount_match:
                # Check if amount is at the end
                amount_pos = amount_match.start()
                after_amount = remaining_text[amount_match.end():].strip()
                
                # Amount should be near the end (allow for some trailing chars)
                if len(after_amount) < 10:
                    amount_str = amount_match.group(0)
                    desc_str = remaining_text[:amount_pos].strip()
            
            current_transaction = {
                'date': standardize_date(date_str),
                'description': desc_str,
                'amount': clean_amount(amount_str)
            }
        else:
            # Continuation of previous transaction (multi-line description)
            if current_transaction:
                current_transaction['description'] += ' ' + line
    
    # Add last transaction
    if current_transaction:
        rows.append(current_transaction)
    
    return rows


def parse_bank_statement_to_rows(text, tables_data=None):
    """
    Enhanced parser with multiple strategies:
    1. Try table extraction first (most accurate)
    2. Fall back to advanced text parsing
    3. Apply data validation and cleaning
    """
    rows = []
    
    # Strategy 1: Extract from tables (if available)
    if tables_data:
        rows = extract_from_tables(tables_data)
        logger.info(f"Extracted {len(rows)} rows from tables")
    
    # Strategy 2: Parse text if no tables or insufficient data
    if not rows or len(rows) < 3:
        text_rows = parse_text_transactions(text)
        if len(text_rows) > len(rows):
            rows = text_rows
        logger.info(f"Extracted {len(rows)} rows from text parsing")
    
    # Data validation: Remove rows with no date or amount
    validated_rows = []
    for row in rows:
        if row['date'] or row['amount']:  # At least date or amount should exist
            # Clean up description
            row['description'] = ' '.join(row['description'].split())
            validated_rows.append(row)
    
    logger.info(f"Final validated rows: {len(validated_rows)}")
    return validated_rows


def detect_transaction_type(description):
    """
    Detect transaction type from description.
    """
    desc_upper = description.upper()
    
    if any(keyword in desc_upper for keyword in ['POS PURCHASE', 'POS DEBIT', 'PURCHASE']):
        return 'Purchase'
    elif any(keyword in desc_upper for keyword in ['ATM WITHDRAWAL', 'ATM WD', 'ATM']):
        return 'ATM Withdrawal'
    elif any(keyword in desc_upper for keyword in ['CHECK', 'CHK', 'CHEQUE']):
        return 'Check'
    elif any(keyword in desc_upper for keyword in ['DEPOSIT', 'DEP', 'CREDIT']):
        return 'Deposit'
    elif any(keyword in desc_upper for keyword in ['TRANSFER', 'XFER', 'TRF']):
        return 'Transfer'
    elif any(keyword in desc_upper for keyword in ['FEE', 'CHARGE', 'SERVICE CHARGE']):
        return 'Fee'
    elif any(keyword in desc_upper for keyword in ['INTEREST', 'INT EARNED']):
        return 'Interest'
    elif any(keyword in desc_upper for keyword in ['PAYMENT', 'PAY', 'BILL PAY']):
        return 'Payment'
    elif any(keyword in desc_upper for keyword in ['PREAUTHORIZED', 'DIRECT DEP', 'PAYROLL', 'SALARY']):
        return 'Direct Deposit'
    elif any(keyword in desc_upper for keyword in ['REFUND', 'REVERSAL']):
        return 'Refund'
    else:
        return 'Other'


def rows_to_csv(rows, out_path, metadata=None):
    """
    Write the extracted rows to a CSV file with enhanced formatting.
    Includes separate debit/credit columns and transaction types.
    """
    with open(out_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write metadata section if provided
        if metadata:
            writer.writerow(['Statement Information'])
            if 'account_number' in metadata:
                writer.writerow(['Account Number', metadata['account_number']])
            if 'statement_period' in metadata:
                writer.writerow(['Statement Period', metadata['statement_period']])
            if 'bank_name' in metadata:
                writer.writerow(['Bank Name', metadata['bank_name']])
            writer.writerow([])  # Blank line separator
        
        # Enhance rows with transaction types and debit/credit columns
        enhanced_rows = []
        for r in rows:
            amount = r.get('amount', '')
            
            # Determine if debit or credit
            try:
                amount_float = float(amount) if amount else 0.0
                is_debit = amount_float < 0
                abs_amount = abs(amount_float)
                
                # Format amount with 2 decimals
                formatted_amount = f"{abs_amount:.2f}"
                
                enhanced_row = {
                    'Transaction Date': r.get('date', ''),
                    'Description': r.get('description', ''),
                    'Transaction Type': detect_transaction_type(r.get('description', '')),
                    'Debit': formatted_amount if is_debit else '',
                    'Credit': formatted_amount if not is_debit and amount_float != 0 else '',
                    'Amount': amount  # Keep original for reference
                }
            except (ValueError, TypeError):
                # If amount parsing fails, use as-is
                enhanced_row = {
                    'Transaction Date': r.get('date', ''),
                    'Description': r.get('description', ''),
                    'Transaction Type': detect_transaction_type(r.get('description', '')),
                    'Debit': '',
                    'Credit': '',
                    'Amount': amount
                }
            
            enhanced_rows.append(enhanced_row)
        
        # Write transaction data with enhanced headers
        fieldnames = ['Transaction Date', 'Description', 'Transaction Type', 'Debit', 'Credit', 'Amount']
        dict_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        dict_writer.writeheader()
        dict_writer.writerows(enhanced_rows)
        
        # Write summary section
        writer.writerow([])  # Blank line
        writer.writerow(['Summary Statistics'])
        
        try:
            total_debits = sum(float(r['Debit']) for r in enhanced_rows if r['Debit'])
            total_credits = sum(float(r['Credit']) for r in enhanced_rows if r['Credit'])
            net_change = total_credits - total_debits
            
            writer.writerow(['Total Debits', f'${total_debits:,.2f}'])
            writer.writerow(['Total Credits', f'${total_credits:,.2f}'])
            writer.writerow(['Net Change', f'${net_change:,.2f}'])
            writer.writerow(['Total Transactions', len(enhanced_rows)])
        except (ValueError, TypeError):
            pass  # Skip summary if calculation fails


def convert_pdf_to_csv(pdf_path):
    """
    Main conversion function with enhanced accuracy:
    - Detects text-based vs scanned PDFs
    - Extracts tables and text
    - Uses advanced parsing with multiple strategies
    - Applies data validation and standardization
    """
    use_text = is_pdf_text_based(pdf_path)
    
    if use_text:
        # Enhanced text extraction with table detection
        text, tables_data = extract_text_pdf_enhanced(pdf_path)
        logger.info(f"Extracted text-based PDF: {len(tables_data)} tables found")
    else:
        # OCR with preprocessing
        text = extract_text_ocr(pdf_path)
        tables_data = None
        logger.info("Extracted scanned PDF using OCR")

    # Parse with advanced algorithms
    rows = parse_bank_statement_to_rows(text, tables_data)

    # Write to CSV
    fd, out_path = tempfile.mkstemp(prefix='bs_', suffix='.csv')
    os.close(fd)
    rows_to_csv(rows, out_path)
    
    logger.info(f"Conversion complete: {len(rows)} transactions extracted")
    return out_path
    rows_to_csv(rows, out_path)
    return out_path
