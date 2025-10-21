"""
Quick diagnostic script to test PDF conversion and identify issues
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processor import (
    is_pdf_text_based, 
    extract_text_pdf_enhanced,
    extract_text_ocr,
    parse_bank_statement_to_rows
)

def test_pdf_conversion(pdf_path):
    """Test PDF conversion step by step"""
    print("=" * 60)
    print("PDF CONVERSION DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Step 1: Check file exists
    print("\n1. Checking file...")
    if not os.path.exists(pdf_path):
        print(f"   ❌ ERROR: File not found: {pdf_path}")
        return
    print(f"   ✅ File exists: {pdf_path}")
    print(f"   📁 Size: {os.path.getsize(pdf_path):,} bytes")
    
    # Step 2: Check if text-based
    print("\n2. Detecting PDF type...")
    try:
        is_text = is_pdf_text_based(pdf_path)
        print(f"   {'✅ Text-based PDF' if is_text else '📸 Scanned PDF (OCR needed)'}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return
    
    # Step 3: Extract text
    print("\n3. Extracting text...")
    try:
        if is_text:
            text, tables = extract_text_pdf_enhanced(pdf_path)
            print(f"   ✅ Extracted {len(text)} characters")
            print(f"   📊 Found {len(tables) if tables else 0} tables")
        else:
            text = extract_text_ocr(pdf_path)
            tables = None
            print(f"   ✅ OCR extracted {len(text)} characters")
        
        # Show first 300 characters
        if text:
            print(f"\n   First 300 characters of extracted text:")
            print(f"   {'-' * 50}")
            print(f"   {text[:300]}")
            print(f"   {'-' * 50}")
        else:
            print("   ⚠️  WARNING: No text extracted!")
            
    except Exception as e:
        print(f"   ❌ ERROR during extraction: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Parse transactions
    print("\n4. Parsing transactions...")
    try:
        rows = parse_bank_statement_to_rows(text, tables)
        print(f"   ✅ Extracted {len(rows)} transactions")
        
        if rows:
            print(f"\n   Sample transactions:")
            for i, row in enumerate(rows[:5], 1):
                print(f"   {i}. Date: {row['date'][:20]:20s} | Amount: {str(row['amount'])[:15]:15s} | Desc: {row['description'][:30]}")
        else:
            print("   ⚠️  WARNING: No transactions found!")
            print("\n   Debugging info:")
            print(f"   - Text length: {len(text)}")
            print(f"   - Text has newlines: {chr(10) in text}")
            print(f"   - Sample lines:")
            for i, line in enumerate(text.split('\n')[:10], 1):
                print(f"     Line {i}: {repr(line[:60])}")
                
    except Exception as e:
        print(f"   ❌ ERROR during parsing: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
    
    return rows


if __name__ == "__main__":
    # Test with uploaded file or use a test file
    test_files = [
        "uploads/a0f969d96dfd4961a58641befd04c5e3_dummy_statement.pdf",
        "test.pdf",
        "sample.pdf"
    ]
    
    pdf_path = None
    for f in test_files:
        if os.path.exists(f):
            pdf_path = f
            break
    
    if pdf_path:
        test_pdf_conversion(pdf_path)
    else:
        print("No test PDF found. Please provide a PDF file.")
        print("Checked paths:")
        for f in test_files:
            print(f"  - {f}")
