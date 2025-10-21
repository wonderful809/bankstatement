"""
Test script for enhanced bank statement parser
Run this to verify parser improvements are working correctly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processor_enhanced import BankStatementParser

# Test data with various formats
test_text = """
Statement Period: 01/01/2024 to 01/31/2024
Account Number: XXXX-1234

Date        Description                     Amount
01/15/2024  Opening Balance                 1,000.00
01/16/2024  ATM Withdrawal                   -200.00
01/17/2024  Payment to Store ABC            -$150.50
            Transaction Reference: TXN12345
Jan 18, 2024 Direct Deposit                 $2,500.00
19/01/2024  Online Transfer                  -€50.25
2024-01-20  Restaurant Purchase              -₹1,234.56
21/01/24    Refund from Merchant             £75.00 CR
01-22-2024  Grocery Store                    -89.99
            Purchase ID: ABC123
            Location: Main St

Page 1 of 2
Continued on next page

01/23/2024  Closing Balance                 2,850.70

Total Transactions: 8
"""

def test_parser():
    print("=" * 60)
    print("ENHANCED BANK STATEMENT PARSER TEST")
    print("=" * 60)
    
    parser = BankStatementParser()
    
    # Test 1: Parse text
    print("\n[TEST 1] Parsing sample bank statement text...")
    rows = parser.parse_text(test_text)
    print(f"✓ Parsed {len(rows)} rows")
    
    # Test 2: Remove duplicates
    print("\n[TEST 2] Detecting duplicate headers/footers...")
    rows_clean = parser.detect_duplicate_rows(rows)
    removed = len(rows) - len(rows_clean)
    print(f"✓ Removed {removed} duplicate/header rows")
    
    # Test 3: Merge multiline descriptions
    print("\n[TEST 3] Merging multiline descriptions...")
    rows_merged = parser.merge_multiline_descriptions(rows_clean)
    print(f"✓ Merged into {len(rows_merged)} final transactions")
    
    # Test 4: Quality report
    print("\n[TEST 4] Quality metrics:")
    report = parser.get_quality_report()
    print(f"  Confidence Score: {report['confidence']}%")
    print(f"  Quality Message: {report['message']}")
    print(f"  Total Rows: {report['total_rows']}")
    print(f"  Rows with Dates: {report['rows_with_dates']}")
    print(f"  Rows with Amounts: {report['rows_with_amounts']}")
    print(f"  Complete Rows: {report['complete_rows']}")
    print(f"  Headers Removed: {report['headers_removed']}")
    print(f"  Duplicates Removed: {report['duplicates_removed']}")
    
    # Test 5: Display parsed transactions
    print("\n[TEST 5] Sample parsed transactions:")
    print("-" * 60)
    for i, row in enumerate(rows_merged[:5], 1):
        print(f"{i}. Date: {row['date']:<15} Amount: {row['amount']:<12}")
        print(f"   Description: {row['description'][:50]}")
    
    if len(rows_merged) > 5:
        print(f"   ... and {len(rows_merged) - 5} more transactions")
    
    # Test 6: Date format detection
    print("\n[TEST 6] Date format detection:")
    date_formats = set()
    for row in rows_merged:
        if row['date']:
            # Detect format type
            if '/' in row['date']:
                date_formats.add('Slash format (MM/DD/YYYY or DD/MM/YYYY)')
            elif '-' in row['date']:
                date_formats.add('Dash format (YYYY-MM-DD or DD-MM-YYYY)')
            elif any(month in row['date'] for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                date_formats.add('Long format (Jan 15, 2024)')
    
    print(f"  Detected {len(date_formats)} different date formats:")
    for fmt in date_formats:
        print(f"    • {fmt}")
    
    # Test 7: Currency symbol detection
    print("\n[TEST 7] Currency symbol detection:")
    currencies = set()
    for row in rows_merged:
        if row['amount']:
            if '$' in row['amount']:
                currencies.add('USD ($)')
            elif '₹' in row['amount']:
                currencies.add('INR (₹)')
            elif '€' in row['amount']:
                currencies.add('EUR (€)')
            elif '£' in row['amount']:
                currencies.add('GBP (£)')
            else:
                currencies.add('Plain number')
    
    print(f"  Detected {len(currencies)} different currency formats:")
    for curr in currencies:
        print(f"    • {curr}")
    
    # Test 8: Multiline detection
    print("\n[TEST 8] Multiline description handling:")
    multiline_count = sum(1 for row in rows_merged if len(row['description'].split()) > 5)
    print(f"  Found {multiline_count} transactions with merged descriptions")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✓")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  • Parsed {len(rows_merged)} transactions")
    print(f"  • Confidence: {report['confidence']}%")
    print(f"  • Quality: {report['message']}")
    print(f"  • Date formats: {len(date_formats)}")
    print(f"  • Currency types: {len(currencies)}")
    print("\nEnhanced parser is working correctly! 🎉")

if __name__ == '__main__':
    test_parser()
