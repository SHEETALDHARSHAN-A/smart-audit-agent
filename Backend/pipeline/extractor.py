import re

class FieldExtractor:
    def __init__(self):
        self.date_pattern = re.compile(r"(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})")
        # Matches "Total" or "Grand Total" followed by optional space/colon/currency symbols and then a number
        self.total_pattern = re.compile(r"(?:Total|Grand Total|Amount)[:\s]*[₹$]?\s*([\d,]+\.?\d{0,2})", re.IGNORECASE)
        self.invoice_no_pattern = re.compile(r"(?:Invoice|Bill)\s*No\.?[:\s]*([A-Z0-9/-]+)", re.IGNORECASE)
        self.vendor_gstin_pattern = re.compile(r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}")

    def extract_fields(self, combined_text: str, text_blocks: list) -> dict:
        """
        Extracts fields using regex from the full text or individual blocks.
        """
        extracted = {}

        # 1. Date
        date_match = self.date_pattern.search(combined_text)
        extracted["date"] = date_match.group(1) if date_match else None

        # 2. Total
        total_match = self.total_pattern.search(combined_text)
        if total_match:
            try:
                # Remove commas and convert to float
                amount_str = total_match.group(1).replace(",", "")
                extracted["total"] = float(amount_str)
            except ValueError:
                extracted["total"] = None
        else:
            extracted["total"] = None

        # 3. Invoice Number
        inv_match = self.invoice_no_pattern.search(combined_text)
        extracted["invoice_no"] = inv_match.group(1) if inv_match else None

        # 4. GSTIN (Vendor ID)
        gstin_match = self.vendor_gstin_pattern.search(combined_text)
        extracted["gstin"] = gstin_match.group(0) if gstin_match else None

        # 5. Vendor Name (Heuristic: usually the first few lines, or largest text at top)
        # This is hard without NER, but we can try taking the first non-date/non-invoice line.
        # For now, we'll leave it as a placeholder or simple heuristic.
        extracted["vendor_name"] = self._heuristic_vendor_name(text_blocks)

        return extracted

    def _heuristic_vendor_name(self, text_blocks):
        # Sort blocks by vertical position (Y coordinate), then horizontal
        # Box format in PaddleOCR is usually [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
        # We want the top-most, left-most text that isn't a label.
        if not text_blocks:
            return None
        
        # Simple heuristic: First block that has high confidence and isn't a date/invoice label
        for block in text_blocks[:5]:
            text = block["text"]
            if len(text) > 3 and not self.date_pattern.search(text) and "invoice" not in text.lower():
                return text
        return "Unknown Vendor"
