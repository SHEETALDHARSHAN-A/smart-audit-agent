"""
Production-Quality Field Extractor for Indian Invoices/Bills
Robust regex patterns designed to handle:
- Multiple date formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, "25 Jan 2024", etc.)
- Indian currency formats (₹1,00,000.00 with lakh separators)
- All GST variants (SGST, CGST, IGST, UTGST, Cess)
- Various invoice number formats
- Phone numbers, emails, addresses
- Comprehensive key-value extraction
"""
import re
from typing import Dict, List, Optional, Any
import logging


class FieldExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regex patterns for performance"""
        
        # ═══════════════════════════════════════════════════════════════════
        # DATE PATTERNS - Handles 10+ formats
        # ═══════════════════════════════════════════════════════════════════
        self.date_patterns = [
            # Mon DD, YYYY (e.g., "Jan 25, 2024", "January 15, 2024") - Check FIRST
            re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})[,.]?\s+(\d{4})\b', re.IGNORECASE),
            # DD Mon YYYY or DD Month YYYY (e.g., "25 Jan 2024", "25 January 2024")
            re.compile(r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)[,.]?\s+(\d{4})\b', re.IGNORECASE),
            # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
            re.compile(r'\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b'),
            # YYYY-MM-DD (ISO format)
            re.compile(r'\b(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\b'),
        ]
        
        # ═══════════════════════════════════════════════════════════════════
        # AMOUNT/TOTAL PATTERNS - Indian currency with lakh separators
        # ═══════════════════════════════════════════════════════════════════
        # Matches: ₹1,00,000.00 or Rs. 1,00,000 or INR 50000 or just 1234.56
        self.amount_pattern = re.compile(
            r'(?:₹|Rs\.?|INR|Rupees?)?\s*'  # Optional currency prefix
            r'([\d,]+(?:\.\d{1,2})?)',       # Number with optional decimals
            re.IGNORECASE
        )
        
        # Total/Grand Total with variations
        self.total_patterns = [
            # "Grand Total: ₹1234" or "Total Amount: 1234.00"
            re.compile(r'\b(?:Grand\s*Total|Net\s*Total|Final\s*Total|Total\s*Amount|Amount\s*Payable|Net\s*Payable|You\s*Pay)[:\s]*(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE),
            # "Total: 1234" (but NOT Subtotal)
            re.compile(r'(?<![Sub])(?<![sub])\bTotal[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE),
            # "Amount: 1234" (standalone)
            re.compile(r'\bAmount[:\s]+(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE),
        ]
        
        # Subtotal pattern (separate to avoid confusion)
        self.subtotal_pattern = re.compile(
            r'\b(?:Sub[\s\-]?Total|Taxable\s*(?:Value|Amount)|Base\s*Amount)[:\s]*(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)',
            re.IGNORECASE
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # GST PATTERNS - All variants with rate and amount
        # ═══════════════════════════════════════════════════════════════════
        # Generic GST tax pattern: "SGST @ 9%: 45.00" or "CGST 9% - ₹45" or "IGST: 18%"
        def make_tax_pattern(tax_name: str) -> re.Pattern:
            return re.compile(
                rf'\b{tax_name}'                           # Tax name
                rf'[:\s@]*'                                # Optional separators
                rf'(?:(\d+(?:\.\d+)?)\s*%)?'               # Optional rate (group 1)
                rf'[:\s\-₹Rs.INR]*'                        # Separators before amount
                rf'([\d,]+(?:\.\d{{1,2}})?)?',             # Optional amount (group 2)
                re.IGNORECASE
            )
        
        self.tax_patterns = {
            'sgst': make_tax_pattern('SGST'),
            'cgst': make_tax_pattern('CGST'),
            'igst': make_tax_pattern('IGST'),
            'utgst': make_tax_pattern('UTGST'),
            'cess': make_tax_pattern('(?:GST\s*)?Cess'),
            'gst': re.compile(r'\bGST\b(?!\s*I[ND])[:\s@]*(?:(\d+(?:\.\d+)?)\s*%)?[:\s\-₹Rs.INR]*([\d,]+(?:\.\d{1,2}})?)?', re.IGNORECASE),  # Matches "GST" alone
            'vat': make_tax_pattern('VAT'),
            'service_tax': make_tax_pattern('Service\s*Tax'),
        }
        
        # Combined tax pattern for "Tax: 18%" or "Tax Amount: 500"
        self.generic_tax_pattern = re.compile(
            r'\b(?:Tax(?:\s*Amount)?|Taxes)[:\s]*(?:₹|Rs\.?)?[\s]*([\d,]+(?:\.\d{1,2})?)',
            re.IGNORECASE
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # GSTIN PATTERN - Indian GST Identification Number (strict validation)
        # ═══════════════════════════════════════════════════════════════════
        # Format: 2 digits (state) + 10 char PAN + 1 entity + Z + 1 checksum
        self.gstin_pattern = re.compile(
            r'\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1})\b'
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # INVOICE/BILL NUMBER PATTERNS
        # ═══════════════════════════════════════════════════════════════════
        self.invoice_patterns = [
            # "Invoice No: INV-2024-001" or "Bill No.: B/123/24"
            re.compile(r'\b(?:Invoice|Bill|Receipt|Order|Ref(?:erence)?|Transaction)\s*(?:No\.?|Number|#|Id)[:\s]*([A-Z0-9\-/]+)', re.IGNORECASE),
            # "#INV123" or "No. 12345"
            re.compile(r'(?:#|No\.?\s*)([A-Z]{2,5}[\-]?[0-9]{3,})', re.IGNORECASE),
        ]
        
        # ═══════════════════════════════════════════════════════════════════
        # CONTACT INFORMATION
        # ═══════════════════════════════════════════════════════════════════
        # Phone: Indian format (+91, 10 digits, with/without spaces/dashes)
        self.phone_pattern = re.compile(
            r'(?:\+91[\s\-]?)?(?:0)?([6-9]\d{9}|\d{2,5}[\s\-]?\d{6,8})'
        )
        
        # Email
        self.email_pattern = re.compile(
            r'\b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b'
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # DISCOUNT PATTERNS
        # ═══════════════════════════════════════════════════════════════════
        self.discount_patterns = [
            re.compile(r'\b(?:Discount|Off|Savings?)[:\s]*(?:₹|Rs\.?)?[\s]*([\d,]+(?:\.\d{1,2})?)', re.IGNORECASE),
            re.compile(r'\b(?:Discount)[:\s]*(\d+(?:\.\d+)?)\s*%', re.IGNORECASE),  # Percentage discount
        ]
        
        # ═══════════════════════════════════════════════════════════════════
        # GENERIC KEY-VALUE PATTERN (for capturing everything else)
        # ═══════════════════════════════════════════════════════════════════
        # Matches "Key: Value" or "Key - Value" on same line
        self.kv_pattern = re.compile(
            r'^[\s]*([A-Za-z][A-Za-z0-9\s]{1,30}?)[:\-]\s*(.{1,100})$',
            re.MULTILINE
        )

    def extract_fields(self, combined_text: str, text_blocks: list) -> Dict[str, Any]:
        """
        Main extraction method. Returns a comprehensive dictionary of all extracted fields.
        """
        if not combined_text:
            return {}
        
        extracted = {}
        
        # 1. Date (try multiple patterns, pick first match)
        extracted["date"] = self._extract_date(combined_text)
        
        # 2. Total Amount
        extracted["total"] = self._extract_total(combined_text)
        
        # 3. Subtotal
        extracted["subtotal"] = self._extract_subtotal(combined_text)
        
        # 4. Invoice/Bill Number
        extracted["invoice_no"] = self._extract_invoice_no(combined_text)
        
        # 5. GSTIN
        extracted["gstin"] = self._extract_gstin(combined_text)
        
        # 6. All Tax Components
        tax_details = self._extract_all_taxes(combined_text)
        extracted.update(tax_details)
        
        # 7. Discount
        extracted["discount"] = self._extract_discount(combined_text)
        
        # 8. Contact Info
        extracted["phone"] = self._extract_phone(combined_text)
        extracted["email"] = self._extract_email(combined_text)
        
        # 9. Vendor Name (heuristic from text blocks)
        extracted["vendor_name"] = self._heuristic_vendor_name(text_blocks, combined_text)
        
        # 10. Generic Key-Value pairs (catch-all)
        extracted["all_details"] = self._extract_all_key_values(combined_text)
        
        # 11. Calculate total tax if not found
        if not extracted.get("total_tax"):
            tax_sum = sum(filter(None, [
                extracted.get("sgst"), extracted.get("cgst"), 
                extracted.get("igst"), extracted.get("utgst"), extracted.get("cess")
            ]))
            extracted["total_tax"] = tax_sum if tax_sum > 0 else None
        
        return extracted

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date using multiple patterns, normalize to DD/MM/YYYY"""
        for pattern in self.date_patterns:
            match = pattern.search(text)
            if match:
                groups = match.groups()
                # Normalize based on pattern type
                if len(groups) == 3:
                    month_map = {'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                                 'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                                 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
                                 'january': '01', 'february': '02', 'march': '03', 'april': '04',
                                 'june': '06', 'july': '07', 'august': '08',
                                 'september': '09', 'october': '10', 'november': '11', 'december': '12'}
                    
                    # Check if first group is a year (ISO format: YYYY-MM-DD)
                    if len(groups[0]) == 4 and groups[0].isdigit():
                        return f"{groups[2]}/{groups[1]}/{groups[0]}"
                    
                    # Check if first group is a month NAME (Mon DD YYYY format)
                    elif groups[0].lower() in month_map:
                        month = month_map[groups[0].lower()]
                        day = groups[1]
                        year = groups[2]
                        return f"{day.zfill(2)}/{month}/{year}"
                    
                    # Check if second group is a month NAME (DD Mon YYYY format)
                    elif groups[1].lower() in month_map:
                        month = month_map[groups[1].lower()]
                        day = groups[0]
                        year = groups[2]
                        return f"{day.zfill(2)}/{month}/{year}"
                    
                    # Numeric format (DD/MM/YYYY)
                    else:
                        return f"{groups[0]}/{groups[1]}/{groups[2]}"
                        
                return match.group(0)
        return None

    def _extract_total(self, text: str) -> Optional[float]:
        """Extract grand total amount"""
        for pattern in self.total_patterns:
            match = pattern.search(text)
            if match:
                return self._parse_amount(match.group(1))
        return None

    def _extract_subtotal(self, text: str) -> Optional[float]:
        """Extract subtotal/taxable value"""
        match = self.subtotal_pattern.search(text)
        if match:
            return self._parse_amount(match.group(1))
        return None

    def _extract_invoice_no(self, text: str) -> Optional[str]:
        """Extract invoice/bill number"""
        for pattern in self.invoice_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_gstin(self, text: str) -> Optional[str]:
        """Extract and validate GSTIN"""
        match = self.gstin_pattern.search(text)
        if match:
            gstin = match.group(1)
            # Basic validation: first 2 digits should be valid state code (01-37)
            state_code = int(gstin[:2])
            if 1 <= state_code <= 37:
                return gstin
        return None

    def _extract_all_taxes(self, text: str) -> Dict[str, Optional[float]]:
        """Extract all tax components with rates and amounts"""
        taxes = {}
        
        for tax_name, pattern in self.tax_patterns.items():
            match = pattern.search(text)
            if match:
                rate = match.group(1)
                amount = match.group(2)
                
                # Store both rate and amount if available
                if amount:
                    taxes[tax_name] = self._parse_amount(amount)
                    if rate:
                        taxes[f"{tax_name}_rate"] = float(rate)
                elif rate:
                    # Only rate found, might be the amount itself
                    taxes[tax_name] = float(rate) if float(rate) > 50 else None  # If >50, likely amount not rate
                    taxes[f"{tax_name}_rate"] = float(rate) if float(rate) <= 50 else None
        
        # Try generic tax pattern
        if not any(taxes.get(k) for k in ['sgst', 'cgst', 'igst', 'gst']):
            match = self.generic_tax_pattern.search(text)
            if match:
                taxes["total_tax"] = self._parse_amount(match.group(1))
        
        return taxes

    def _extract_discount(self, text: str) -> Optional[float]:
        """Extract discount amount or percentage"""
        for pattern in self.discount_patterns:
            match = pattern.search(text)
            if match:
                return self._parse_amount(match.group(1))
        return None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number"""
        match = self.phone_pattern.search(text)
        if match:
            phone = re.sub(r'[\s\-]', '', match.group(0))
            if len(phone) >= 10:
                return phone[-10:]  # Return last 10 digits
        return None

    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address"""
        match = self.email_pattern.search(text)
        return match.group(1) if match else None

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string handling Indian number format (lakhs)"""
        if not amount_str:
            return None
        try:
            # Remove all commas and spaces
            cleaned = re.sub(r'[,\s]', '', amount_str)
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _extract_all_key_values(self, text: str) -> Dict[str, str]:
        """
        Generic key-value extractor for all 'Key: Value' patterns.
        Filters out noise and cleans up results.
        """
        matches = self.kv_pattern.findall(text)
        result = {}
        
        # Words to skip as keys (noise)
        skip_keys = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'page', 'of'}
        
        for key, value in matches:
            clean_key = key.strip()
            clean_val = value.strip()
            
            # Skip if key is too short, too long, or in skip list
            if (2 < len(clean_key) < 30 and 
                len(clean_val) > 0 and 
                clean_key.lower() not in skip_keys and
                not clean_key.isdigit()):
                result[clean_key] = clean_val
        
        return result

    def _heuristic_vendor_name(self, text_blocks: List[Dict], full_text: str) -> Optional[str]:
        """
        Extract vendor name using multiple heuristics:
        1. First large text block at top
        2. Text near "From:" or company indicators
        3. First line that looks like a business name
        """
        # Try to find "From:" or "Seller:" pattern
        from_pattern = re.compile(r'(?:From|Seller|Vendor|Company|Firm)[:\s]+([A-Z][A-Za-z0-9\s&.,]+)', re.IGNORECASE)
        match = from_pattern.search(full_text)
        if match:
            return match.group(1).strip()[:50]  # Limit length
        
        # Use text blocks (sorted by position)
        if text_blocks:
            # Sort by Y coordinate (top first)
            try:
                sorted_blocks = sorted(
                    [b for b in text_blocks if b.get("box") and len(b.get("box", [])) >= 4],
                    key=lambda b: b["box"][0][1] if isinstance(b["box"][0], list) else 0
                )
            except (KeyError, TypeError, IndexError):
                sorted_blocks = text_blocks[:5]
            
            for block in sorted_blocks[:5]:
                text = block.get("text", "")
                # Skip if it looks like a label or date
                if (len(text) > 3 and 
                    not re.search(r'invoice|bill|date|gstin|tax|total|receipt', text, re.IGNORECASE) and
                    not re.match(r'^\d', text)):
                    return text[:50]
        
        return None
