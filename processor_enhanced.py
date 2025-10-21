import os
import csv
import re
import tempfile
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import shutil
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import Counter


class ExternalToolError(RuntimeError):
    pass


class QualityScore:
    """Confidence score for extraction quality"""
    def __init__(self):
        self.total_rows = 0
        self.rows_with_dates = 0
        self.rows_with_amounts = 0
        self.rows_with_both = 0
        self.duplicate_rows = 0
        self.header_rows_removed = 0
        
    def calculate_confidence(self) -> float:
        """Calculate confidence score (0-100)"""
        if self.total_rows == 0:
            return 0.0
        
        # Weight different factors
        date_score = (self.rows_with_dates / self.total_rows) * 40
        amount_score = (self.rows_with_amounts / self.total_rows) * 40
        complete_score = (self.rows_with_both / self.total_rows) * 20
        
        # Penalty for too many duplicates
        duplicate_penalty = min((self.duplicate_rows / max(self.total_rows, 1)) * 20, 20)
        
        confidence = date_score + amount_score + complete_score - duplicate_penalty
        return max(0.0, min(100.0, confidence))
    
    def get_quality_message(self, include_emoji: bool = True) -> str:
        """Get human-readable quality assessment
        
        Args:
            include_emoji: If True, includes emoji (for display). If False, plain text (for logging)
        """
        confidence = self.calculate_confidence()
        
        if confidence >= 80:
            emoji = "✅ " if include_emoji else ""
            return f"{emoji}Excellent quality ({confidence:.1f}%)"
        elif confidence >= 60:
            emoji = "⚠️ " if include_emoji else ""
            return f"{emoji}Good quality ({confidence:.1f}%) - Some data may need manual review"
        elif confidence >= 40:
            emoji = "⚠️ " if include_emoji else ""
            return f"{emoji}Fair quality ({confidence:.1f}%) - Manual review recommended"
        else:
            emoji = "❌ " if include_emoji else ""
            return f"{emoji}Low quality ({confidence:.1f}%) - Extraction may be unreliable"


class BankStatementParser:
    """Enhanced parser with regex patterns for common bank statement formats"""
    
    # Enhanced date patterns supporting multiple formats with more variations
    DATE_PATTERNS = [
        # MM/DD/YYYY or MM-DD-YYYY or MM.DD.YYYY (US format)
        (r'\b(0?[1-9]|1[0-2])[/\-\.](0?[1-9]|[12]\d|3[01])[/\-\.](\d{4})\b', 'US'),
        # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY (European format)
        (r'\b(0?[1-9]|[12]\d|3[01])[/\-\.](0?[1-9]|1[0-2])[/\-\.](\d{4})\b', 'EU'),
        # MM/DD/YY or MM-DD-YY (US short year)
        (r'\b(0?[1-9]|1[0-2])[/\-\.](0?[1-9]|[12]\d|3[01])[/\-\.](\d{2})\b', 'US_SHORT'),
        # DD/MM/YY or DD-MM-YY (European short year)
        (r'\b(0?[1-9]|[12]\d|3[01])[/\-\.](0?[1-9]|1[0-2])[/\-\.](\d{2})\b', 'EU_SHORT'),
        # YYYY-MM-DD or YYYY/MM/DD (ISO format)
        (r'\b(\d{4})[/\-\.]?(0?[1-9]|1[0-2])[/\-\.]?(0?[1-9]|[12]\d|3[01])\b', 'ISO'),
        # Month DD, YYYY (e.g., Jan 15, 2024 or January 15, 2024)
        (r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(0?[1-9]|[12]\d|3[01]),?\s+(\d{4})\b', 'LONG'),
        # DD Month YYYY (e.g., 15 Jan 2024 or 15 January 2024)
        (r'\b(0?[1-9]|[12]\d|3[01])\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})\b', 'LONG_EU'),
    ]
    
    # Enhanced currency patterns supporting multiple currencies and formats including negative amounts
    CURRENCY_PATTERNS = [
        # Negative amounts with currency symbols: -$1,234.56 or ($1,234.56)
        r'\(-?\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)',
        r'-\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
        # Positive amounts with currency symbols
        r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
        # Indian Rupee: ₹1,234.56 or ₹1234.56 with negatives
        r'\(-?₹\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)',
        r'-?₹\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
        # Euro: €1,234.56 with negatives
        r'\(-?€\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)',
        r'-?€\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
        # Pound: £1,234.56 with negatives
        r'\(-?£\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)',
        r'-?£\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
        # Plain numbers in parentheses (negative): (1,234.56)
        r'\(\d{1,3}(?:,\d{3})*(?:\.\d{2})?\)',
        # Plain number with commas and negative: -1,234.56
        r'-\d{1,3}(?:,\d{3})+(?:\.\d{2})?',
        # Plain number with commas: 1,234.56
        r'\d{1,3}(?:,\d{3})+(?:\.\d{2})?',
        # Plain number without commas but with decimals: -1234.56 or 1234.56
        r'-?\d+\.\d{2}',
        # With CR/DR suffix: 1,234.56 CR or 1,234.56 DR
        r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:CR|DR)\b',
        # International formats: 1.234,56 (European decimal separator)
        r'-?\d{1,3}(?:\.\d{3})+,\d{2}',
    ]
    
    # Common header/footer patterns to skip
    SKIP_PATTERNS = [
        r'page \d+ of \d+',
        r'continued on next page',
        r'^\s*date\s+description\s+amount\s*$',
        r'^\s*transaction\s+date\s+details\s*$',
        r'^\s*opening balance\s*$',
        r'^\s*closing balance\s*$',
        r'^\s*total\s*$',
        r'^\s*balance\s+brought\s+forward\s*$',
        r'statement period:',
        r'account number:',
        r'customer service:',
    ]
    
    def __init__(self):
        self.date_patterns = [(re.compile(pattern, re.IGNORECASE), format_type) 
                              for pattern, format_type in self.DATE_PATTERNS]
        self.currency_regex = re.compile('|'.join(self.CURRENCY_PATTERNS))
        self.skip_regex = re.compile('|'.join(self.SKIP_PATTERNS), re.IGNORECASE)
        self.quality_score = QualityScore()
        
    def should_skip_line(self, line: str) -> bool:
        """Check if line is a header/footer that should be skipped"""
        line_lower = line.strip().lower()
        
        # Skip empty lines
        if not line_lower:
            return True
        
        # Skip known header/footer patterns
        if self.skip_regex.search(line_lower):
            self.quality_score.header_rows_removed += 1
            return True
        
        # Skip lines that are too short (likely headers)
        if len(line_lower) < 10:
            return True
        
        # Skip lines with only numbers (likely page numbers)
        if line_lower.strip().isdigit():
            return True
            
        return False
    
    def extract_date(self, line: str) -> Optional[str]:
        """Extract and normalize date from line"""
        for pattern, format_type in self.date_patterns:
            match = pattern.search(line)
            if match:
                return match.group()
        return None
    
    def extract_amounts(self, line: str) -> List[str]:
        """Extract all currency amounts from line"""
        return [m.group().strip() for m in self.currency_regex.finditer(line)]
    
    def parse_line(self, line: str) -> Optional[Dict[str, str]]:
        """Parse a single line into date, description, amount with improved extraction"""
        line = line.strip()
        
        # Skip headers/footers
        if self.should_skip_line(line):
            return None
        
        # Extract components
        date_val = self.extract_date(line)
        amounts = self.extract_amounts(line)
        
        # Handle multiple amounts (debit/credit columns or running balance)
        debit_val = ''
        credit_val = ''
        balance_val = ''
        
        if len(amounts) == 3:
            # Format: date description debit credit balance
            debit_val = amounts[0] if amounts[0] else ''
            credit_val = amounts[1] if amounts[1] else ''
            balance_val = amounts[2] if amounts[2] else ''
        elif len(amounts) == 2:
            # Could be: debit/credit or amount/balance
            # Check which one is larger (balance usually larger)
            try:
                amt1 = float(amounts[0].replace(',', '').replace('$', '').replace('£', '').replace('€', '').strip().lstrip('-').strip('()'))
                amt2 = float(amounts[1].replace(',', '').replace('$', '').replace('£', '').replace('€', '').strip().lstrip('-').strip('()'))
                if amt2 > amt1 * 2:  # Second is likely balance
                    debit_val = amounts[0]
                    balance_val = amounts[1]
                else:  # Both are transaction amounts (debit/credit)
                    debit_val = amounts[0]
                    credit_val = amounts[1]
            except:
                debit_val = amounts[0]
                credit_val = amounts[1]
        elif len(amounts) == 1:
            # Single amount - store as primary amount
            debit_val = amounts[0]
        
        # Combine into single amount field (prefer debit, then credit)
        amount_val = debit_val or credit_val
        
        # Description is everything between date and amounts
        desc_val = line
        if date_val and amounts:
            # Remove date and all amounts from description
            desc_val = line
            desc_val = desc_val.replace(date_val, '', 1)
            for amt in amounts:
                desc_val = desc_val.replace(amt, '', 1)
            desc_val = desc_val.strip()
        elif date_val:
            desc_val = line.replace(date_val, '', 1).strip()
        elif amounts:
            for amt in amounts:
                desc_val = desc_val.replace(amt, '', 1)
            desc_val = desc_val.strip()
        
        # Clean up extra whitespace
        desc_val = ' '.join(desc_val.split())
        
        return {
            'date': date_val or '',
            'description': desc_val,
            'amount': amount_val,
            'debit': debit_val,
            'credit': credit_val,
            'balance': balance_val,
            'has_date': bool(date_val),
            'has_amount': bool(amount_val)
        }
    
    def parse_text(self, text: str) -> List[Dict[str, str]]:
        """Parse entire text into structured rows"""
        rows = []
        lines = text.splitlines()
        
        for line in lines:
            parsed = self.parse_line(line)
            if parsed:
                self.quality_score.total_rows += 1
                if parsed['has_date']:
                    self.quality_score.rows_with_dates += 1
                if parsed['has_amount']:
                    self.quality_score.rows_with_amounts += 1
                if parsed['has_date'] and parsed['has_amount']:
                    self.quality_score.rows_with_both += 1
                
                # Only keep rows with meaningful content
                if parsed['date'] or parsed['description'] or parsed['amount']:
                    rows.append(parsed)
        
        return rows
    
    def detect_duplicate_rows(self, rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Detect and remove duplicate header/footer rows that appear on each page"""
        if len(rows) < 10:
            return rows
        
        # Find lines that appear multiple times
        line_signatures = []
        for row in rows:
            # Create signature from description (ignoring dates/amounts which change)
            sig = row['description'].lower().strip()
            line_signatures.append(sig)
        
        # Count occurrences
        sig_counts = Counter(line_signatures)
        
        # Remove lines that appear too frequently (likely headers/footers)
        threshold = max(3, len(rows) // 20)  # Appears on >5% of pages
        filtered_rows = []
        
        for i, row in enumerate(rows):
            sig = line_signatures[i]
            if sig and sig_counts[sig] >= threshold and len(sig) < 50:
                # This is likely a repeating header/footer
                self.quality_score.header_rows_removed += 1
                self.quality_score.duplicate_rows += 1
                continue
            filtered_rows.append(row)
        
        return filtered_rows
    
    def merge_multiline_descriptions(self, rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Merge rows that are continuation of previous description"""
        if not rows:
            return rows
        
        merged = []
        current = None
        
        for row in rows:
            # If row has date or amount, it's likely a new transaction
            if row['date'] or row['amount']:
                if current:
                    merged.append(current)
                current = row.copy()
                # Remove temporary fields
                current.pop('has_date', None)
                current.pop('has_amount', None)
            else:
                # Continuation line - merge with current transaction
                if current and row['description']:
                    # Add to description with a space
                    current['description'] += ' ' + row['description']
                elif not current:
                    # First line without date/amount - keep it
                    current = row.copy()
                    current.pop('has_date', None)
                    current.pop('has_amount', None)
        
        if current:
            merged.append(current)
        
        return merged
    
    def get_quality_report(self) -> Dict[str, any]:
        """Get quality metrics and confidence score"""
        return {
            'confidence': self.quality_score.calculate_confidence(),
            'message': self.quality_score.get_quality_message(include_emoji=True),  # For display with emoji
            'message_plain': self.quality_score.get_quality_message(include_emoji=False),  # For logging
            'total_rows': self.quality_score.total_rows,
            'rows_with_dates': self.quality_score.rows_with_dates,
            'rows_with_amounts': self.quality_score.rows_with_amounts,
            'complete_rows': self.quality_score.rows_with_both,
            'headers_removed': self.quality_score.header_rows_removed,
            'duplicates_removed': self.quality_score.duplicate_rows
        }


def is_pdf_text_based(path: str) -> bool:
    """Check if PDF has extractable text"""
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:2]:
                text = page.extract_text() or ''
                if len(text.strip()) > 50:  # At least 50 characters
                    return True
    except Exception:
        return False
    return False


def extract_text_pdf(path: str) -> str:
    """Extract text from PDF using pdfplumber with enhanced table detection"""
    texts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            # Extract regular text
            page_text = page.extract_text() or ''
            
            # Try to extract tables for better structured data
            try:
                tables = page.extract_tables()
                if tables and len(tables) > 0:
                    # If we have table data, convert it to text with better formatting
                    for table in tables:
                        for row in table:
                            if row:
                                # Join cells with proper spacing to help regex matching
                                row_text = '  '.join(str(cell).strip() if cell else '' for cell in row)
                                texts.append(row_text)
                else:
                    # No tables, use regular text
                    texts.append(page_text)
            except Exception:
                # Fallback to regular text extraction
                texts.append(page_text)
    
    return '\n'.join(texts)


def extract_text_ocr(path: str, tesseract_cmd: Optional[str] = None, poppler_path: Optional[str] = None) -> str:
    """Extract text from PDF using OCR with enhanced preprocessing"""
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    else:
        # Try to find Tesseract in common locations
        common_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe',
        ]
        for test_path in common_paths:
            if os.path.exists(test_path):
                pytesseract.pytesseract.tesseract_cmd = test_path
                break
    
    if not shutil.which(pytesseract.pytesseract.tesseract_cmd or 'tesseract'):
        raise ExternalToolError('Tesseract not found. Install Tesseract or set TESSERACT_CMD env var.')
    
    try:
        # Convert with higher DPI for better OCR accuracy
        images = convert_from_path(path, dpi=300, poppler_path=poppler_path)
    except Exception as e:
        raise ExternalToolError(f'Poppler not available or failed to render PDF: {str(e)}')
    
    texts = []
    for img in images:
        # Enhanced image preprocessing for better OCR
        # Convert to grayscale
        img = img.convert('L')
        
        # Optional: Enhance contrast (can improve OCR on low-quality scans)
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # Use optimized Tesseract config for tables/documents
        # PSM 6 = Assume a single uniform block of text
        # PSM 4 = Assume a single column of text of variable sizes
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, config=custom_config)
        texts.append(text)
    
    return '\n'.join(texts)


def rows_to_csv(rows: List[Dict[str, str]], out_path: str):
    """Write rows to CSV file with professional banking format"""
    with open(out_path, 'w', newline='', encoding='utf-8') as csvfile:
        # Professional banking CSV format
        fieldnames = ['Date', 'Description', 'Debit', 'Credit', 'Balance', 'Category']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        for r in rows:
            # Get values from parsed row
            date_val = r.get('date', '').strip()
            desc_val = r.get('description', '').strip()
            debit_raw = r.get('debit', '').strip()
            credit_raw = r.get('credit', '').strip()
            balance_raw = r.get('balance', '').strip()
            
            # Clean up amounts (remove currency symbols)
            def clean_amount(amt_str):
                if not amt_str:
                    return ''
                # Remove currency symbols and clean
                cleaned = amt_str.replace('$', '').replace('£', '').replace('€', '').replace('₹', '')
                cleaned = cleaned.replace(',', '').strip()
                # Handle negative amounts in parentheses
                if cleaned.startswith('(') and cleaned.endswith(')'):
                    cleaned = '-' + cleaned.strip('()')
                return cleaned.strip()
            
            debit_val = clean_amount(debit_raw)
            credit_val = clean_amount(credit_raw)
            balance_val = clean_amount(balance_raw)
            
            # If we have a single amount but no debit/credit split, categorize it
            if not debit_val and not credit_val and r.get('amount'):
                amount_str = clean_amount(r.get('amount', ''))
                
                # Classify as debit or credit based on description keywords
                desc_lower = desc_val.lower()
                debit_keywords = ['withdrawal', 'payment', 'purchase', 'atm', 'fee', 'charge', 'debit', 
                                 'transfer out', 'check', 'cheque', 'bill', 'subscription']
                credit_keywords = ['deposit', 'credit', 'refund', 'interest', 'transfer in', 
                                  'salary', 'payment received', 'income', 'reimbursement']
                
                is_negative = amount_str.startswith('-')
                if is_negative:
                    debit_val = amount_str.lstrip('-')
                elif any(keyword in desc_lower for keyword in debit_keywords):
                    debit_val = amount_str
                elif any(keyword in desc_lower for keyword in credit_keywords):
                    credit_val = amount_str
                else:
                    # Default: positive amounts are debits (expenses)
                    debit_val = amount_str
            
            # Auto-categorize transactions
            category = ''
            desc_lower = desc_val.lower()
            
            if any(word in desc_lower for word in ['grocery', 'supermarket', 'food', 'restaurant', 'cafe']):
                category = 'Food & Dining'
            elif any(word in desc_lower for word in ['gas', 'fuel', 'parking', 'uber', 'lyft', 'transit']):
                category = 'Transportation'
            elif any(word in desc_lower for word in ['netflix', 'spotify', 'subscription', 'membership']):
                category = 'Entertainment'
            elif any(word in desc_lower for word in ['amazon', 'shop', 'store', 'retail']):
                category = 'Shopping'
            elif any(word in desc_lower for word in ['rent', 'mortgage', 'utility', 'electric', 'water', 'internet']):
                category = 'Bills & Utilities'
            elif any(word in desc_lower for word in ['atm', 'withdrawal', 'cash']):
                category = 'Cash & ATM'
            elif any(word in desc_lower for word in ['transfer', 'payment']):
                category = 'Transfer'
            elif any(word in desc_lower for word in ['salary', 'payroll', 'income', 'deposit']):
                category = 'Income'
            elif any(word in desc_lower for word in ['interest', 'dividend']):
                category = 'Interest & Dividends'
            elif any(word in desc_lower for word in ['fee', 'charge', 'penalty']):
                category = 'Fees & Charges'
            else:
                category = 'Uncategorized'
            
            # Format row with proper column names
            formatted_row = {
                'Date': date_val,
                'Description': desc_val,
                'Debit': debit_val,
                'Credit': credit_val,
                'Balance': balance_val,
                'Category': category
            }
            
            writer.writerow(formatted_row)


def convert_pdf_to_csv(pdf_path: str, bank_type: str = 'auto', tesseract_cmd: Optional[str] = None, poppler_path: Optional[str] = None) -> Dict:
    """
    Convert PDF to CSV with quality metrics and bank-specific optimizations
    
    Args:
        pdf_path: Path to PDF file
        bank_type: Bank type ('auto', 'chase', 'bofa', 'wells_fargo', etc.)
        tesseract_cmd: Optional path to tesseract executable
        poppler_path: Optional path to poppler binaries
    
    Returns: Dictionary with status, csv_path, metadata, and quality info
    """
    try:
        # Setup Tesseract/Poppler from environment if not provided
        if not tesseract_cmd:
            tesseract_cmd = os.environ.get('TESSERACT_CMD')
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        
        if not poppler_path:
            poppler_path = os.environ.get('POPPLER_PATH')
        
        # Decide whether to use text extraction or OCR
        use_text = is_pdf_text_based(pdf_path)
        
        # Extract text
        start_time = datetime.now()
        if use_text:
            text = extract_text_pdf(pdf_path)
            conversion_type = 'text'
        else:
            text = extract_text_ocr(pdf_path, tesseract_cmd, poppler_path)
            conversion_type = 'ocr'
        
        # Parse with enhanced parser (bank-specific optimization can be added)
        parser = BankStatementParser()
        rows = parser.parse_text(text)
        rows = parser.detect_duplicate_rows(rows)  # Remove duplicate headers/footers
        rows = parser.merge_multiline_descriptions(rows)
        
        # Get quality report
        quality_report = parser.get_quality_report()
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Estimate page count from PDF
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
        except:
            page_count = 1
        
        # Create CSV
        fd, out_path = tempfile.mkstemp(prefix='bs_', suffix='.csv')
        os.close(fd)
        rows_to_csv(rows, out_path)
        
        # Build result dictionary
        result = {
            'status': 'success',
            'csv_path': out_path,
            'filename': os.path.basename(out_path),
            'row_count': len(rows),
            'metadata': {
                'pages': page_count,
                'conversion_type': conversion_type,
                'bank_type': bank_type,
                'processing_time': round(processing_time, 2),
                'original_file': os.path.basename(pdf_path)
            },
            'quality': {
                'confidence': quality_report['confidence'],
                'message': quality_report['message'],
                'details': {
                    'total_rows': quality_report['total_rows'],
                    'rows_with_dates': quality_report['rows_with_dates'],
                    'rows_with_amounts': quality_report['rows_with_amounts'],
                    'complete_rows': quality_report['complete_rows'],
                    'headers_removed': quality_report['headers_removed'],
                    'duplicates_removed': quality_report['duplicates_removed']
                }
            }
        }
        
        return result
        
    except ExternalToolError as e:
        return {
            'status': 'error',
            'error': str(e),
            'error_type': 'external_tool'
        }
    except Exception as e:
        import traceback
        return {
            'status': 'error',
            'error': f'Conversion failed: {str(e)}',
            'error_type': 'processing',
            'traceback': traceback.format_exc()
        }
