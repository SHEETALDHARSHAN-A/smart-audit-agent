# Tesseract Installation Instructions

## Windows Installation

1. Download Tesseract installer from:
   https://github.com/UB-Mannheim/tesseract/wiki

2. Run the installer and note the installation path (usually: `C:\Program Files\Tesseract-OCR`)

3. Add Tesseract to your PATH or configure pytesseract:
   - Option A: Add to PATH environment variable
   - Option B: Set in code (already configured in hybrid_ocr.py)

4. Verify installation:
   ```powershell
   tesseract --version
   ```

## Alternative: Skip Tesseract
The hybrid OCR will fall back to PaddleOCR if Tesseract is not installed.
System will still work perfectly fine without it!

## TrOCR Model Download
TrOCR models will auto-download on first use (~400MB).
This is normal and only happens once.
