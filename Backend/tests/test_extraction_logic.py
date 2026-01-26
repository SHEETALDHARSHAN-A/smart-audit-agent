"""
Comprehensive test suite for the upgraded FieldExtractor.
Tests all regex patterns with edge cases.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from pipeline.extractor import FieldExtractor


def run_tests():
    extractor = FieldExtractor()
    all_passed = True
    
    # ═══════════════════════════════════════════════════════════════════
    # TEST 1: Date Formats
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("TEST 1: Date Extraction")
    print("="*60)
    
    date_tests = [
        ("Invoice Date: 25/01/2024", "25/01/2024"),
        ("Date: 25-01-2024", "25/01/2024"),
        ("Dated: 2024-01-25", "25/01/2024"),
        ("Bill on 25 Jan 2024", "25/01/2024"),
        ("January 15, 2024", "15/01/2024"),
    ]
    
    for text, expected in date_tests:
        result = extractor._extract_date(text)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"  {status} Input: '{text}' | Got: '{result}' | Expected: '{expected}'")
    
    # ═══════════════════════════════════════════════════════════════════
    # TEST 2: Amount Parsing (Indian Format)
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("TEST 2: Amount Parsing")
    print("="*60)
    
    amount_tests = [
        ("1,00,000.50", 100000.50),
        ("₹50,000", 50000.0),
        ("Rs. 1234.56", 1234.56),
        ("1234", 1234.0),
    ]
    
    for text, expected in amount_tests:
        result = extractor._parse_amount(text.replace("₹", "").replace("Rs.", "").strip())
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"  {status} Input: '{text}' | Got: {result} | Expected: {expected}")
    
    # ═══════════════════════════════════════════════════════════════════
    # TEST 3: Total Extraction (Avoiding Subtotal)
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("TEST 3: Total vs Subtotal")
    print("="*60)
    
    total_text = """
    Subtotal: 500.00
    SGST: 45.00
    CGST: 45.00
    Grand Total: 590.00
    """
    result = extractor.extract_fields(total_text, [])
    print(f"  Subtotal: {result.get('subtotal')} (Expected: 500.0)")
    print(f"  Total: {result.get('total')} (Expected: 590.0)")
    if result.get('total') != 590.0:
        all_passed = False
        print("  ✗ Total extraction FAILED")
    else:
        print("  ✓ Total extraction PASSED")
    
    # ═══════════════════════════════════════════════════════════════════
    # TEST 4: GST Extraction
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("TEST 4: GST Components")
    print("="*60)
    
    gst_text = """
    Taxable Value: 1000.00
    SGST @ 9%: 90.00
    CGST @ 9%: 90.00
    Total: 1180.00
    """
    result = extractor.extract_fields(gst_text, [])
    print(f"  SGST: {result.get('sgst')} (Expected: 90.0)")
    print(f"  CGST: {result.get('cgst')} (Expected: 90.0)")
    print(f"  SGST Rate: {result.get('sgst_rate')} (Expected: 9.0)")
    print(f"  Total Tax: {result.get('total_tax')} (Expected: 180.0)")
    
    if result.get('sgst') == 90.0 and result.get('cgst') == 90.0:
        print("  ✓ GST extraction PASSED")
    else:
        print("  ✗ GST extraction FAILED")
        all_passed = False
    
    # ═══════════════════════════════════════════════════════════════════
    # TEST 5: GSTIN Validation
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("TEST 5: GSTIN Validation")
    print("="*60)
    
    gstin_tests = [
        ("GSTIN: 29ABCDE1234F1Z5", "29ABCDE1234F1Z5"),
        ("GST No: 07AABCU9603R1ZM", "07AABCU9603R1ZM"),
        ("Invalid: 99ABCDE1234F1Z5", None),  # 99 is not a valid state code
    ]
    
    for text, expected in gstin_tests:
        result = extractor._extract_gstin(text)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"  {status} Input: '{text}' | Got: '{result}' | Expected: '{expected}'")
    
    # ═══════════════════════════════════════════════════════════════════
    # TEST 6: Invoice Number
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("TEST 6: Invoice Number")
    print("="*60)
    
    inv_tests = [
        ("Invoice No: INV-2024-001", "INV-2024-001"),
        ("Bill No.: B/123/24", "B/123/24"),
        ("Receipt #REC12345", "REC12345"),
    ]
    
    for text, expected in inv_tests:
        result = extractor._extract_invoice_no(text)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"  {status} Input: '{text}' | Got: '{result}' | Expected: '{expected}'")
    
    # ═══════════════════════════════════════════════════════════════════
    # TEST 7: Contact Info
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("TEST 7: Contact Information")
    print("="*60)
    
    contact_text = "Call us: +91-9876543210, Email: support@shop.com"
    result = extractor.extract_fields(contact_text, [])
    print(f"  Phone: {result.get('phone')} (Expected: 9876543210)")
    print(f"  Email: {result.get('email')} (Expected: support@shop.com)")
    
    if result.get('phone') == '9876543210' and result.get('email') == 'support@shop.com':
        print("  ✓ Contact extraction PASSED")
    else:
        print("  ✗ Contact extraction FAILED")
        all_passed = False
    
    # ═══════════════════════════════════════════════════════════════════
    # FINAL RESULT
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED ✓")
    else:
        print("SOME TESTS FAILED ✗")
    print("="*60)


if __name__ == "__main__":
    run_tests()
