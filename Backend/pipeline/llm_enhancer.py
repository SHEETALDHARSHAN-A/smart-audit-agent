import os
from groq import Groq
import json
import logging
import re

class LLMEnhancer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Initialize Groq client
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            self.logger.warning("GROQ_API_KEY not set. LLM enhancement will be disabled.")
            self.client = None
        else:
            self.client = Groq(api_key=api_key)
    
    def _clean_json_response(self, text: str) -> str:
        """Clean and fix common JSON issues from LLM responses"""
        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].strip()
        
        # Fix common issues
        text = text.replace("'", '"')  # Single to double quotes
        text = re.sub(r',\s*}', '}', text)  # Remove trailing commas
        text = re.sub(r',\s*]', ']', text)  # Remove trailing commas in arrays
        text = re.sub(r'\\n', ' ', text)  # Remove escaped newlines
        
        return text
    
    def enhance_extraction(self, ocr_text: str, basic_extraction: dict) -> dict:
        """
        Use Groq LLM to enhance field extraction with better accuracy.
        Returns enhanced data with confidence scores.
        """
        if not self.client:
            self.logger.info("Groq not configured, returning basic extraction")
            return {"data": basic_extraction, "confidence": 0.7, "enhanced": False}
        
        try:
            prompt = f"""Extract invoice/bill information from the following OCR text.
Return ONLY a valid JSON object with these fields (use null if not found):
- date: string in DD/MM/YYYY format
- vendor_name: string
- gstin: string (15 characters)
- invoice_no: string
- total: number
- tax: number
- line_items: array of objects with description, qty, rate, amount

OCR Text:
{ocr_text[:2500]}

Return ONLY the JSON object, no explanations."""
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You extract structured data from invoices. Return ONLY valid JSON, nothing else."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            # Parse response
            result_text = response.choices[0].message.content.strip()
            result_text = self._clean_json_response(result_text)
            
            try:
                enhanced_data = json.loads(result_text)
            except json.JSONDecodeError:
                # Try to extract JSON object with regex
                json_match = re.search(r'\{[^{}]*\}', result_text, re.DOTALL)
                if json_match:
                    enhanced_data = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse JSON from response")
            
            self.logger.info("LLM enhancement successful")
            
            return {
                "data": enhanced_data,
                "confidence": 0.95,
                "enhanced": True,
                "model": "llama-3.3-70b-versatile"
            }
            
        except Exception as e:
            self.logger.error(f"LLM enhancement failed: {e}")
            return {"data": basic_extraction, "confidence": 0.7, "enhanced": False, "error": str(e)}

