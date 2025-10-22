"""
Multi-Format Bank Statement Processor
Supports: PDF, CSV, Excel (XLSX, XLS), OFX
"""

import os
import csv
import tempfile
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import chardet
from ofxparse import OfxParser

# Import PDF processor
from processor_enhanced import (
    convert_pdf_to_csv as pdf_processor,
    ExternalToolError
)

logger = logging.getLogger(__name__)


class ProcessorError(Exception):
    """Base exception for processor errors"""
    pass


class UnsupportedFormatError(ProcessorError):
    """Raised when file format is not supported"""
    pass


class DataQualityError(ProcessorError):
    """Raised when data quality is too low"""
    pass


def detect_encoding(file_path: str) -> str:
    """Detect file encoding for CSV files"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(100000)  # Read first 100KB
            result = chardet.detect(raw_data)
            return result['encoding'] or 'utf-8'
    except Exception:
        return 'utf-8'


def standardize_csv_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize CSV to our banking format:
    Date, Description, Debit, Credit, Balance, Category
    """
    # Common column name mappings
    column_mappings = {
        'date': ['date', 'transaction date', 'trans date', 'posting date', 'value date', 'dated'],
        'description': ['description', 'details', 'narration', 'particulars', 'transaction details', 'memo'],
        'debit': ['debit', 'withdrawal', 'withdrawals', 'debit amount', 'dr', 'paid out'],
        'credit': ['credit', 'deposit', 'deposits', 'credit amount', 'cr', 'paid in'],
        'amount': ['amount', 'transaction amount', 'value'],
        'balance': ['balance', 'running balance', 'closing balance', 'available balance']
    }
    
    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()
    
    # Find best matching columns
    found_columns = {}
    for target, variants in column_mappings.items():
        for col in df.columns:
            if col in variants:
                found_columns[target] = col
                break
    
    # Create standardized dataframe
    standard_df = pd.DataFrame()
    
    # Date column
    if 'date' in found_columns:
        standard_df['Date'] = pd.to_datetime(df[found_columns['date']], errors='coerce')
        standard_df['Date'] = standard_df['Date'].dt.strftime('%Y-%m-%d')
    else:
        standard_df['Date'] = ''
    
    # Description column
    if 'description' in found_columns:
        standard_df['Description'] = df[found_columns['description']].fillna('').astype(str)
    else:
        # Try to combine multiple text columns
        text_cols = [col for col in df.columns if df[col].dtype == 'object']
        if text_cols:
            standard_df['Description'] = df[text_cols].fillna('').astype(str).agg(' '.join, axis=1)
        else:
            standard_df['Description'] = ''
    
    # Amount columns - handle both split (Debit/Credit) and single amount
    if 'debit' in found_columns and 'credit' in found_columns:
        standard_df['Debit'] = pd.to_numeric(df[found_columns['debit']], errors='coerce').fillna(0)
        standard_df['Credit'] = pd.to_numeric(df[found_columns['credit']], errors='coerce').fillna(0)
    elif 'amount' in found_columns:
        # Single amount column - split into debit/credit based on sign
        amounts = pd.to_numeric(df[found_columns['amount']], errors='coerce').fillna(0)
        standard_df['Debit'] = amounts.apply(lambda x: abs(x) if x < 0 else 0)
        standard_df['Credit'] = amounts.apply(lambda x: x if x > 0 else 0)
    else:
        standard_df['Debit'] = 0
        standard_df['Credit'] = 0
    
    # Balance column
    if 'balance' in found_columns:
        standard_df['Balance'] = pd.to_numeric(df[found_columns['balance']], errors='coerce').fillna('')
    else:
        standard_df['Balance'] = ''
    
    # Auto-categorize
    standard_df['Category'] = standard_df['Description'].apply(auto_categorize)
    
    # Remove empty rows
    standard_df = standard_df[
        (standard_df['Date'] != '') | 
        (standard_df['Description'].str.strip() != '') |
        (standard_df['Debit'] != 0) |
        (standard_df['Credit'] != 0)
    ]
    
    return standard_df


def auto_categorize(description: str) -> str:
    """Auto-categorize transaction based on description"""
    desc_lower = str(description).lower()
    
    if any(word in desc_lower for word in ['grocery', 'supermarket', 'food', 'restaurant', 'cafe', 'dining']):
        return 'Food & Dining'
    elif any(word in desc_lower for word in ['gas', 'fuel', 'parking', 'uber', 'lyft', 'transit', 'metro']):
        return 'Transportation'
    elif any(word in desc_lower for word in ['netflix', 'spotify', 'subscription', 'membership', 'hulu', 'amazon prime']):
        return 'Entertainment'
    elif any(word in desc_lower for word in ['amazon', 'shop', 'store', 'retail', 'walmart', 'target']):
        return 'Shopping'
    elif any(word in desc_lower for word in ['rent', 'mortgage', 'utility', 'electric', 'water', 'internet', 'cable']):
        return 'Bills & Utilities'
    elif any(word in desc_lower for word in ['atm', 'withdrawal', 'cash']):
        return 'Cash & ATM'
    elif any(word in desc_lower for word in ['transfer', 'payment']):
        return 'Transfer'
    elif any(word in desc_lower for word in ['salary', 'payroll', 'income', 'deposit', 'direct dep']):
        return 'Income'
    elif any(word in desc_lower for word in ['interest', 'dividend']):
        return 'Interest & Dividends'
    elif any(word in desc_lower for word in ['fee', 'charge', 'penalty', 'overdraft']):
        return 'Fees & Charges'
    elif any(word in desc_lower for word in ['insurance', 'medical', 'health', 'doctor', 'pharmacy']):
        return 'Healthcare'
    elif any(word in desc_lower for word in ['school', 'education', 'tuition', 'course']):
        return 'Education'
    else:
        return 'Uncategorized'


def process_csv(file_path: str) -> Tuple[str, Dict]:
    """
    Process CSV file and convert to standardized format
    
    Returns:
        Tuple of (output_csv_path, metadata_dict)
    """
    try:
        # Detect encoding
        encoding = detect_encoding(file_path)
        logger.info(f"Detected encoding: {encoding}")
        
        # Read CSV with pandas
        try:
            df = pd.read_csv(file_path, encoding=encoding)
        except Exception:
            # Try with different encoding
            df = pd.read_csv(file_path, encoding='latin1')
        
        # Check if file has data
        if df.empty:
            raise DataQualityError("CSV file is empty")
        
        logger.info(f"Read CSV: {len(df)} rows, {len(df.columns)} columns")
        
        # Standardize format
        standard_df = standardize_csv_format(df)
        
        # Create output file
        fd, out_path = tempfile.mkstemp(prefix='csv_', suffix='.csv')
        os.close(fd)
        
        # Write standardized CSV
        standard_df.to_csv(out_path, index=False, encoding='utf-8')
        
        # Calculate quality metrics
        total_rows = len(standard_df)
        rows_with_dates = standard_df['Date'].ne('').sum()
        rows_with_amounts = ((standard_df['Debit'] != 0) | (standard_df['Credit'] != 0)).sum()
        
        confidence = (rows_with_dates / total_rows * 50 + rows_with_amounts / total_rows * 50) if total_rows > 0 else 0
        
        metadata = {
            'status': 'success',
            'csv_path': out_path,
            'row_count': total_rows,
            'conversion_type': 'parse',
            'file_format': 'csv',
            'quality': {
                'confidence': confidence,
                'message': f'Processed {total_rows} transactions',
                'rows_with_dates': rows_with_dates,
                'rows_with_amounts': rows_with_amounts
            }
        }
        
        return out_path, metadata
        
    except Exception as e:
        logger.exception(f"CSV processing failed: {str(e)}")
        raise ProcessorError(f"CSV processing failed: {str(e)}")


def process_excel(file_path: str) -> Tuple[str, Dict]:
    """
    Process Excel file (XLSX, XLS) and convert to standardized CSV
    
    Returns:
        Tuple of (output_csv_path, metadata_dict)
    """
    try:
        # Read Excel file (pandas handles both XLSX and XLS)
        # Try to read the first sheet that looks like transactions
        excel_file = pd.ExcelFile(file_path)
        
        # Try each sheet to find transaction data
        df = None
        sheet_used = None
        
        for sheet_name in excel_file.sheet_names:
            try:
                temp_df = pd.read_excel(file_path, sheet_name=sheet_name)
                if not temp_df.empty and len(temp_df) > 1:
                    # Check if it has date-like columns
                    has_date_col = any('date' in str(col).lower() for col in temp_df.columns)
                    if has_date_col:
                        df = temp_df
                        sheet_used = sheet_name
                        break
            except Exception:
                continue
        
        # If no sheet with date column found, use first non-empty sheet
        if df is None:
            for sheet_name in excel_file.sheet_names:
                try:
                    temp_df = pd.read_excel(file_path, sheet_name=sheet_name)
                    if not temp_df.empty and len(temp_df) > 1:
                        df = temp_df
                        sheet_used = sheet_name
                        break
                except Exception:
                    continue
        
        if df is None or df.empty:
            raise DataQualityError("Excel file contains no usable data")
        
        logger.info(f"Read Excel sheet '{sheet_used}': {len(df)} rows, {len(df.columns)} columns")
        
        # Standardize format
        standard_df = standardize_csv_format(df)
        
        # Create output file
        fd, out_path = tempfile.mkstemp(prefix='excel_', suffix='.csv')
        os.close(fd)
        
        # Write standardized CSV
        standard_df.to_csv(out_path, index=False, encoding='utf-8')
        
        # Calculate quality metrics
        total_rows = len(standard_df)
        rows_with_dates = standard_df['Date'].ne('').sum()
        rows_with_amounts = ((standard_df['Debit'] != 0) | (standard_df['Credit'] != 0)).sum()
        
        confidence = (rows_with_dates / total_rows * 50 + rows_with_amounts / total_rows * 50) if total_rows > 0 else 0
        
        metadata = {
            'status': 'success',
            'csv_path': out_path,
            'row_count': total_rows,
            'conversion_type': 'parse',
            'file_format': 'excel',
            'sheet_name': sheet_used,
            'quality': {
                'confidence': confidence,
                'message': f'Processed {total_rows} transactions from Excel',
                'rows_with_dates': rows_with_dates,
                'rows_with_amounts': rows_with_amounts
            }
        }
        
        return out_path, metadata
        
    except Exception as e:
        logger.exception(f"Excel processing failed: {str(e)}")
        raise ProcessorError(f"Excel processing failed: {str(e)}")


def process_ofx(file_path: str) -> Tuple[str, Dict]:
    """
    Process OFX (Open Financial Exchange) file and convert to standardized CSV
    
    Returns:
        Tuple of (output_csv_path, metadata_dict)
    """
    try:
        # Parse OFX file
        with open(file_path, 'rb') as f:
            ofx = OfxParser.parse(f)
        
        # Extract transactions from all accounts
        transactions = []
        account_count = 0
        
        if hasattr(ofx, 'accounts') and ofx.accounts:
            for account in ofx.accounts:
                account_count += 1
                if hasattr(account, 'statement') and hasattr(account.statement, 'transactions'):
                    for trans in account.statement.transactions:
                        transactions.append({
                            'date': trans.date.strftime('%Y-%m-%d') if hasattr(trans, 'date') else '',
                            'description': trans.memo or trans.payee or '',
                            'amount': float(trans.amount) if hasattr(trans, 'amount') else 0,
                            'type': trans.type if hasattr(trans, 'type') else ''
                        })
        
        if not transactions:
            raise DataQualityError("OFX file contains no transactions")
        
        # Create DataFrame
        df = pd.DataFrame(transactions)
        
        # Split amount into debit/credit
        df['Debit'] = df['amount'].apply(lambda x: abs(x) if x < 0 else 0)
        df['Credit'] = df['amount'].apply(lambda x: x if x > 0 else 0)
        df['Balance'] = ''
        df['Category'] = df['description'].apply(auto_categorize)
        
        # Format final dataframe
        standard_df = df[['date', 'description']].copy()
        standard_df.columns = ['Date', 'Description']
        standard_df['Debit'] = df['Debit']
        standard_df['Credit'] = df['Credit']
        standard_df['Balance'] = df['Balance']
        standard_df['Category'] = df['Category']
        
        # Create output file
        fd, out_path = tempfile.mkstemp(prefix='ofx_', suffix='.csv')
        os.close(fd)
        
        # Write CSV
        standard_df.to_csv(out_path, index=False, encoding='utf-8')
        
        # Calculate quality metrics
        total_rows = len(standard_df)
        confidence = 95  # OFX is a structured format, so high confidence
        
        metadata = {
            'status': 'success',
            'csv_path': out_path,
            'row_count': total_rows,
            'conversion_type': 'parse',
            'file_format': 'ofx',
            'accounts_processed': account_count,
            'quality': {
                'confidence': confidence,
                'message': f'Processed {total_rows} transactions from {account_count} account(s)',
                'rows_with_dates': total_rows,
                'rows_with_amounts': total_rows
            }
        }
        
        return out_path, metadata
        
    except Exception as e:
        logger.exception(f"OFX processing failed: {str(e)}")
        raise ProcessorError(f"OFX processing failed: {str(e)}")


def detect_file_format(filename: str) -> str:
    """Detect file format from extension"""
    ext = os.path.splitext(filename)[1].lower()
    
    format_map = {
        '.pdf': 'pdf',
        '.csv': 'csv',
        '.xlsx': 'excel',
        '.xls': 'excel',
        '.ofx': 'ofx',
        '.qfx': 'ofx',  # Quicken uses .qfx which is same as OFX
    }
    
    return format_map.get(ext, 'unknown')


def convert_bank_statement(file_path: str, filename: str = None, 
                           tesseract_cmd: str = None, poppler_path: str = None) -> Dict:
    """
    Universal bank statement converter supporting multiple formats
    
    Args:
        file_path: Path to the file
        filename: Original filename (to detect format)
        tesseract_cmd: Path to Tesseract (for PDF OCR)
        poppler_path: Path to Poppler (for PDF OCR)
    
    Returns:
        Dictionary with conversion results and metadata
    """
    try:
        if filename is None:
            filename = os.path.basename(file_path)
        
        # Detect format
        file_format = detect_file_format(filename)
        
        if file_format == 'unknown':
            raise UnsupportedFormatError(f"Unsupported file format: {filename}")
        
        logger.info(f"Processing {file_format.upper()} file: {filename}")
        
        # Route to appropriate processor
        if file_format == 'pdf':
            # Use existing PDF processor
            result = pdf_processor(file_path, tesseract_cmd=tesseract_cmd, poppler_path=poppler_path)
            
            # Normalize result format
            if result.get('status') == 'success':
                return {
                    'success': True,
                    'csv_path': result['csv_path'],
                    'row_count': result.get('row_count', 0),
                    'conversion_type': result.get('metadata', {}).get('conversion_type', 'unknown'),
                    'file_format': 'pdf',
                    'page_count': result.get('metadata', {}).get('pages', 1),
                    'quality_score': result.get('quality', {}).get('confidence', 0),
                    'quality_message': result.get('quality', {}).get('message', ''),
                    'processing_time': result.get('metadata', {}).get('processing_time', 0)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'error_type': result.get('error_type', 'unknown')
                }
        
        elif file_format == 'csv':
            csv_path, metadata = process_csv(file_path)
            return {
                'success': True,
                'csv_path': csv_path,
                'row_count': metadata['row_count'],
                'conversion_type': metadata['conversion_type'],
                'file_format': 'csv',
                'page_count': 1,
                'quality_score': metadata['quality']['confidence'],
                'quality_message': metadata['quality']['message'],
                'processing_time': 0.5
            }
        
        elif file_format == 'excel':
            csv_path, metadata = process_excel(file_path)
            return {
                'success': True,
                'csv_path': csv_path,
                'row_count': metadata['row_count'],
                'conversion_type': metadata['conversion_type'],
                'file_format': 'excel',
                'page_count': 1,
                'quality_score': metadata['quality']['confidence'],
                'quality_message': metadata['quality']['message'],
                'processing_time': 0.8
            }
        
        elif file_format == 'ofx':
            csv_path, metadata = process_ofx(file_path)
            return {
                'success': True,
                'csv_path': csv_path,
                'row_count': metadata['row_count'],
                'conversion_type': metadata['conversion_type'],
                'file_format': 'ofx',
                'page_count': 1,
                'quality_score': metadata['quality']['confidence'],
                'quality_message': metadata['quality']['message'],
                'processing_time': 0.3
            }
        
        else:
            raise UnsupportedFormatError(f"Format not implemented: {file_format}")
            
    except (ProcessorError, UnsupportedFormatError, DataQualityError) as e:
        logger.error(f"Processing error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': 'processing'
        }
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'error_type': 'unknown'
        }
