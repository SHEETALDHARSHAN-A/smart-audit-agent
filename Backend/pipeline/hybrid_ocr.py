"""
Hybrid OCR Engine Router
Intelligently selects the best OCR engine based on document type and content
"""
import os
import logging
import time
import warnings
warnings.filterwarnings("ignore", message="Some weights of VisionEncoderDecoderModel")
from typing import Dict, List, Any, Tuple
import numpy as np

class HybridOCREngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.engines = {}
        self._trocr_unavailable = False  # Cache TrOCR availability to avoid repeated warnings
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Lazy-load OCR engines as needed"""
        try:
            from paddleocr import PaddleOCR
            self.engines['paddle'] = PaddleOCR(use_angle_cls=True, lang='en')
            self.logger.info("PaddleOCR initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize PaddleOCR: {e}")
    
    def _get_tesseract(self):
        """Lazy load Tesseract"""
        if 'tesseract' not in self.engines:
            try:
                import pytesseract
                from PIL import Image
                self.engines['tesseract'] = pytesseract
                self.engines['PIL'] = Image
                self.logger.info("Tesseract initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Tesseract: {e}")
                return None
        return self.engines.get('tesseract')
    
    def _get_local_model_path(self) -> str:
        """Get the path to the local TrOCR model directory"""
        # Check relative to project root (works for both development and deployment)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))  # Go up from Backend/pipeline
        return os.path.join(project_root, 'models', 'trocr-base-handwritten')
    
    def _is_trocr_available(self) -> tuple:
        """
        Check if TrOCR model is available locally or in HuggingFace cache.
        Returns: (is_available: bool, model_path: str or None)
        """
        # First check local models directory (production deployment)
        local_path = self._get_local_model_path()
        local_model_file = os.path.join(local_path, 'model.safetensors')
        local_config_file = os.path.join(local_path, 'config.json')
        
        if os.path.exists(local_model_file) and os.path.exists(local_config_file):
            return True, local_path
        
        # Fall back to HuggingFace cache
        try:
            from huggingface_hub import try_to_load_from_cache
            model_file = try_to_load_from_cache(
                'microsoft/trocr-base-handwritten', 
                'model.safetensors'
            )
            if model_file is not None and model_file != False:
                return True, 'microsoft/trocr-base-handwritten'
        except Exception:
            pass
        
        return False, None
    
    def _get_trocr(self):
        """Lazy load TrOCR for handwriting - from local models or HuggingFace cache"""
        # Return early if we already know TrOCR is unavailable
        if self._trocr_unavailable:
            return None
        
        if 'trocr' not in self.engines:
            # Check if model is available
            is_available, model_path = self._is_trocr_available()
            
            if not is_available:
                self.logger.warning(
                    "TrOCR model not found. Run 'download_trocr.bat' to download. "
                    "Using PaddleOCR in the meantime."
                )
                self._trocr_unavailable = True
                return None
            
            try:
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel
                
                # Determine if loading from local path or HuggingFace
                is_local = os.path.isdir(model_path) if model_path else False
                
                if is_local:
                    self.logger.info(f"Loading TrOCR model from local: {model_path}")
                    processor = TrOCRProcessor.from_pretrained(model_path, local_files_only=True)
                    model = VisionEncoderDecoderModel.from_pretrained(model_path, local_files_only=True)
                else:
                    self.logger.info("Loading TrOCR model from HuggingFace cache...")
                    processor = TrOCRProcessor.from_pretrained(model_path, local_files_only=True)
                    model = VisionEncoderDecoderModel.from_pretrained(model_path, local_files_only=True)
                
                # Dynamic Quantization (2-3x speedup on CPU)
                self.logger.info("Applying dynamic quantization to TrOCR...")
                import torch
                model = torch.quantization.quantize_dynamic(
                    model, {torch.nn.Linear}, dtype=torch.qint8
                )
                self.logger.info("TrOCR quantized successfully")
                
                self.engines['trocr'] = {'processor': processor, 'model': model}
                self.logger.info("TrOCR initialized successfully")
            except Exception as e:
                self.logger.warning(f"TrOCR not available: {e}. Falling back to PaddleOCR for all text.")
                self._trocr_unavailable = True  # Don't try again
                return None
        return self.engines.get('trocr')
    
    def detect_handwriting(self, image_path: str) -> bool:
        """
        Detect if image contains handwriting using heuristics.
        Returns True if handwriting is detected.
        """
        try:
            import cv2
            
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return False
            
            # Apply edge detection
            edges = cv2.Canny(img, 50, 150)
            
            # Calculate edge density
            edge_density = np.sum(edges > 0) / edges.size
            
            # Apply line detection
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                                    minLineLength=50, maxLineGap=10)
            
            # Handwriting indicators:
            # 1. Lower edge density (handwriting is more sparse)
            # 2. Fewer straight lines (handwriting is curved/irregular)
            # 3. High variance in stroke width
            
            num_lines = len(lines) if lines is not None else 0
            
            # Heuristic: if few straight lines and moderate edge density, likely handwriting
            is_handwritten = (num_lines < 20 and 0.02 < edge_density < 0.15)
            
            if is_handwritten:
                self.logger.info(f"Handwriting detected in {image_path}")
            
            return is_handwritten
            
        except Exception as e:
            self.logger.error(f"Handwriting detection failed: {e}")
            return False
    
    def extract_handwriting_batch(self, image_paths: List[str]) -> List[str]:
        """Extract handwritten text from a batch of images using TrOCR"""
        if not image_paths:
            return []
            
        trocr = self._get_trocr()
        if not trocr:
            return [""] * len(image_paths)
        
        try:
            from PIL import Image
            import torch
            
            # Load all images
            images = [Image.open(p).convert("RGB") for p in image_paths]
            
            # Process batch
            pixel_values = trocr['processor'](images, return_tensors="pt").pixel_values
            
            # Generate text (batch inference)
            generated_ids = trocr['model'].generate(pixel_values, max_length=128)
            texts = trocr['processor'].batch_decode(generated_ids, skip_special_tokens=True)
            
            return texts
            
        except Exception as e:
            self.logger.error(f"TrOCR batch extraction failed: {e}")
            return [""] * len(image_paths)

    def extract_handwriting_with_trocr(self, image_path: str) -> str:
        """Extract handwritten text using TrOCR (Single Image)"""
        results = self.extract_handwriting_batch([image_path])
        return results[0] if results else ""
    
    def detect_document_type(self, file_path: str) -> str:
        """Detect document type from file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        type_map = {
            '.pdf': 'pdf',
            '.png': 'image',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.tiff': 'image',
            '.bmp': 'image',
            '.docx': 'docx',
            '.doc': 'doc',
            '.xlsx': 'xlsx',
            '.xls': 'xls'
        }
        return type_map.get(ext, 'unknown')
    
    def extract_with_tesseract(self, image_path: str) -> str:
        """Extract text using Tesseract OCR"""
        tesseract = self._get_tesseract()
        if not tesseract:
            return ""
        
        try:
            from PIL import Image
            img = Image.open(image_path)
            text = tesseract.image_to_string(img, config='--psm 6')
            self.logger.info(f"Tesseract extracted {len(text)} characters")
            return text
        except Exception as e:
            self.logger.error(f"Tesseract extraction failed: {e}")
            return ""
    
    def extract_with_trocr(self, image_path: str) -> str:
        """Extract handwritten text using TrOCR"""
        trocr = self._get_trocr()
        if not trocr:
            return ""
        
        try:
            from PIL import Image
            import torch
            
            image = Image.open(image_path).convert("RGB")
            pixel_values = trocr['processor'](image, return_tensors="pt").pixel_values
            
            generated_ids = trocr['model'].generate(pixel_values)
            text = trocr['processor'].batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            self.logger.info(f"TrOCR extracted: {text}")
            return text
        except Exception as e:
            self.logger.error(f"TrOCR extraction failed: {e}")
            return ""
    
    def extract_tables(self, pdf_path: str) -> List[Dict]:
        """Extract tables from PDF using Camelot"""
        try:
            import camelot
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            result = []
            for i, table in enumerate(tables):
                result.append({
                    'table_number': i + 1,
                    'data': table.df.to_dict('records'),
                    'accuracy': table.accuracy
                })
            
            self.logger.info(f"Extracted {len(tables)} tables from PDF")
            return result
        except Exception as e:
            self.logger.error(f"Table extraction failed: {e}")
            return []
    
    def extract_from_docx(self, docx_path: str) -> str:
        """Extract text from Word document"""
        try:
            from docx import Document
            doc = Document(docx_path)
            text = '\n'.join([para.text for para in doc.paragraphs])
            self.logger.info(f"Extracted {len(text)} characters from DOCX")
            return text
        except Exception as e:
            self.logger.error(f"DOCX extraction failed: {e}")
            return ""
    
    def extract_from_xlsx(self, xlsx_path: str) -> Dict:
        """Extract data from Excel file"""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(xlsx_path)
            result = {}
            
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                data = []
                for row in sheet.iter_rows(values_only=True):
                    data.append(list(row))
                result[sheet_name] = data
            
            self.logger.info(f"Extracted {len(result)} sheets from XLSX")
            return result
        except Exception as e:
            self.logger.error(f"XLSX extraction failed: {e}")
            return {}
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, bool]:
        """Extract text from PDF, detect if scanned"""
        try:
            import pdfplumber
            text = ""
            is_scanned = True
            
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text += page_text + "\n"
                        is_scanned = False
            
            if is_scanned or len(text.strip()) < 50:
                self.logger.info("PDF appears to be scanned, will use OCR")
                return text, True
            else:
                self.logger.info(f"Extracted {len(text)} characters from text-based PDF")
                return text, False
                
        except Exception as e:
            self.logger.error(f"PDF text extraction failed: {e}")
            return "", True
    
    def get_text_blocks(self, file_path: str, use_hybrid: bool = True) -> List[Dict]:
        """
        Main method to extract text using appropriate engine(s)
        """
        doc_type = self.detect_document_type(file_path)
        self.logger.info(f"Processing {doc_type} document: {file_path}")
        
        text_blocks = []
        combined_text = ""
        
        # Handle different document types
        if doc_type == 'docx':
            combined_text = self.extract_from_docx(file_path)
            text_blocks = [{"text": combined_text, "confidence": 1.0, "box": []}]
            
        elif doc_type == 'xlsx':
            data = self.extract_from_xlsx(file_path)
            # Convert Excel data to text representation
            for sheet, rows in data.items():
                combined_text += f"\nSheet: {sheet}\n"
                for row in rows:
                    combined_text += " | ".join([str(cell) for cell in row if cell]) + "\n"
            text_blocks = [{"text": combined_text, "confidence": 1.0, "box": []}]
            
        elif doc_type == 'pdf':
            # Try text extraction first
            pdf_text, is_scanned = self.extract_text_from_pdf(file_path)
            
            if not is_scanned and pdf_text:
                # Text-based PDF
                text_blocks = [{"text": pdf_text, "confidence": 1.0, "box": []}]
            else:
                # Scanned PDF - convert pages to images and preprocess
                text_blocks = self._process_scanned_pdf(file_path)
        
        elif doc_type == 'image':
            # Use hybrid approach for images
            if use_hybrid:
                # Try PaddleOCR first (best for layout)
                if 'paddle' in self.engines:
                    result = self.engines['paddle'].ocr(file_path)
                    if result and result[0]:
                        for line in result[0]:
                            text_blocks.append({
                                "text": line[1][0],
                                "confidence": line[1][1],
                                "box": line[0]
                            })
                
                # Also try Tesseract for comparison
                tesseract_text = self.extract_with_tesseract(file_path)
                if tesseract_text and len(tesseract_text) > len(combined_text):
                    # If Tesseract found more text, use it
                    text_blocks.append({
                        "text": tesseract_text,
                        "confidence": 0.8,
                        "box": [],
                        "engine": "tesseract"
                    })
            else:
                # Default to PaddleOCR
                if 'paddle' in self.engines:
                    result = self.engines['paddle'].ocr(file_path)
                    if result and result[0]:
                        for line in result[0]:
                            text_blocks.append({
                                "text": line[1][0],
                                "confidence": line[1][1],
                                "box": line[0]
                            })
        
        return text_blocks if text_blocks else [{"text": "", "confidence": 0, "box": []}]
    
    def _process_scanned_pdf(self, pdf_path: str) -> List[Dict]:
        """Convert PDF pages to images, detect handwriting per region, run appropriate OCR"""
        text_blocks = []
        
        try:
            import fitz  # PyMuPDF
            import cv2
            import os
            from PIL import Image
            
            pdf_doc = fitz.open(pdf_path)
            temp_dir = "temp_processed"
            os.makedirs(temp_dir, exist_ok=True)
            
            for page_num, page in enumerate(pdf_doc):
                # Convert page to high-res image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_path = os.path.join(temp_dir, f"pdf_page_{page_num}.png")
                pix.save(img_path)
                
                # First pass: Use PaddleOCR to get text boxes and initial text
                paddle_results = []
                if 'paddle' in self.engines:
                    result = self.engines['paddle'].ocr(img_path)
                    if result and result[0]:
                        paddle_results = result[0]
                
                # Load the image for region extraction
                full_img = cv2.imread(img_path)
                
                start_time = time.time()
                
                # Analyze each text region
                regions_to_process = []  # Store metadata for batch processing
                
                for line in paddle_results:
                    box = line[0]  # [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                    paddle_text = line[1][0]
                    paddle_conf = line[1][1]
                    
                    # Extract region coordinates
                    x_coords = [p[0] for p in box]
                    y_coords = [p[1] for p in box]
                    x1, x2 = int(min(x_coords)), int(max(x_coords))
                    y1, y2 = int(min(y_coords)), int(max(y_coords))
                    
                    # Skip very small regions (likely noise or single characters)
                    if (x2 - x1) < 30 or (y2 - y1) < 15:
                        text_blocks.append({
                            "text": paddle_text, "confidence": paddle_conf, "box": box, "page": page_num + 1, "engine": "paddle_fast"
                        })
                        continue

                    # Add padding
                    pad = 5
                    x1, y1 = max(0, x1-pad), max(0, y1-pad)
                    x2, y2 = min(full_img.shape[1], x2+pad), min(full_img.shape[0], y2+pad)
                    
                    # Crop the text region
                    region = full_img[y1:y2, x1:x2]
                    
                    # Check if this region looks handwritten
                    is_handwritten = self._is_region_handwritten(region)
                    
                    if is_handwritten and paddle_conf < 0.9:
                        # Save for batch processing
                        region_path = os.path.join(temp_dir, f"region_{page_num}_{x1}_{y1}.png")
                        cv2.imwrite(region_path, region)
                        regions_to_process.append({
                            'path': region_path,
                            'box': box,
                            'paddle_text': paddle_text,
                            'paddle_conf': paddle_conf
                        })
                    else:
                        # Printed text directly
                        text_blocks.append({
                            "text": paddle_text,
                            "confidence": paddle_conf,
                            "box": box,
                            "page": page_num + 1,
                            "engine": "paddle"
                        })

                # Batch process collected handwritten regions
                if regions_to_process:
                    self.logger.info(f"Running TrOCR batch on {len(regions_to_process)} regions...")
                    batch_start = time.time()
                    paths = [r['path'] for r in regions_to_process]
                    
                    # Process in smaller chunks to avoid OOM
                    batch_size = 16
                    trocr_results = []
                    
                    for i in range(0, len(paths), batch_size):
                        chunk_paths = paths[i:i + batch_size]
                        chunk_results = self.extract_handwriting_batch(chunk_paths)
                        trocr_results.extend(chunk_results)
                    
                    batch_duration = time.time() - batch_start
                    self.logger.info(f"TrOCR batch finished in {batch_duration:.2f}s ({len(regions_to_process)} regions)")
                    
                    # Merge results
                    for i, result_text in enumerate(trocr_results):
                        meta = regions_to_process[i]
                        if result_text and len(result_text) > 0:
                            text_blocks.append({
                                "text": result_text,
                                "confidence": 0.85,
                                "box": meta['box'],
                                "page": page_num + 1,
                                "engine": "trocr_handwriting"
                            })
                        else:
                             # Fallback to paddle
                             text_blocks.append({
                                "text": meta['paddle_text'],
                                "confidence": meta['paddle_conf'],
                                "box": meta['box'],
                                "page": page_num + 1,
                                "engine": "paddle"
                            })
                
                self.logger.info(f"Processed PDF page {page_num + 1}: {len(paddle_results)} regions in {time.time() - start_time:.2f}s")
            
            pdf_doc.close()
            
        except Exception as e:
            self.logger.error(f"PDF preprocessing failed: {e}")
            # Fallback to direct OCR
            if 'paddle' in self.engines:
                result = self.engines['paddle'].ocr(pdf_path)
                if result and result[0]:
                    for line in result[0]:
                        text_blocks.append({
                            "text": line[1][0],
                            "confidence": line[1][1],
                            "box": line[0]
                        })
        
        return text_blocks
    
    def _is_region_handwritten(self, region) -> bool:
        """Detect if a small text region is handwritten"""
        try:
            import cv2
            
            if region is None or region.size == 0:
                return False
            
            # Convert to grayscale
            if len(region.shape) == 3:
                gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            else:
                gray = region
            
            # Handwriting detection heuristics for small regions:
            
            # 1. Edge irregularity - handwriting has more irregular edges
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # 2. Stroke width variation - handwriting has more variation
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Count horizontal runs to detect stroke consistency
            stroke_widths = []
            for row in binary:
                in_stroke = False
                width = 0
                for pixel in row:
                    if pixel > 0:
                        if not in_stroke:
                            in_stroke = True
                        width += 1
                    else:
                        if in_stroke:
                            stroke_widths.append(width)
                            width = 0
                            in_stroke = False
            
            if len(stroke_widths) > 5:
                stroke_std = np.std(stroke_widths)
                stroke_mean = np.mean(stroke_widths)
                stroke_variation = stroke_std / max(stroke_mean, 1)
            else:
                stroke_variation = 0
            
            # 3. Line straightness - handwriting has fewer straight horizontal lines
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=20, 
                                    minLineLength=max(10, region.shape[1]//4), maxLineGap=5)
            num_straight_lines = len(lines) if lines is not None else 0
            
            # Heuristics for handwriting (Strict Mode):
            # - Moderate edge density (not too clean, not too noisy)
            # - High stroke width variation (handwriting has varying pen pressure/width)
            # - Few straight lines (printed text has many straight lines)
            is_handwritten = (
                (0.02 < edge_density < 0.12) and  # Tighter upper bound (printed text is dense)
                (stroke_variation > 0.6 or num_straight_lines < 2)  # Higher variation required
            )
            return is_handwritten
            
        except Exception as e:
            self.logger.debug(f"Region handwriting detection failed: {e}")
            return False
    
    def _preprocess_image(self, image_path: str) -> str:
        """Apply image preprocessing for better OCR accuracy"""
        try:
            import cv2
            import os
            
            # Read image in grayscale
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return image_path
            
            # Upscale if small
            height, width = img.shape
            if height < 1000 or width < 1000:
                img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            
            # Denoise
            img = cv2.GaussianBlur(img, (3, 3), 0)
            
            # Adaptive thresholding for better handling of varying backgrounds
            img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 2)
            
            # Save preprocessed image
            temp_dir = "temp_processed"
            os.makedirs(temp_dir, exist_ok=True)
            filename = os.path.basename(image_path)
            save_path = os.path.join(temp_dir, f"prep_{filename}")
            cv2.imwrite(save_path, img)
            
            self.logger.info(f"Image preprocessed: {save_path}")
            return save_path
            
        except Exception as e:
            self.logger.error(f"Image preprocessing failed: {e}")
            return image_path


def download_trocr_model():
    """Download TrOCR model ahead of time to avoid blocking during document processing"""
    print("=" * 60)
    print("TrOCR Model Downloader")
    print("=" * 60)
    print("\nThis will download the TrOCR handwriting recognition model (~1.3GB)")
    print("from HuggingFace. Please ensure you have a stable internet connection.\n")
    
    try:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        
        print("[1/2] Downloading TrOCR Processor...")
        processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-handwritten')
        print("      ✓ Processor downloaded successfully")
        
        print("\n[2/2] Downloading TrOCR Model (this may take several minutes)...")
        model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-base-handwritten')
        print("      ✓ Model downloaded successfully")
        
        print("\n" + "=" * 60)
        print("TrOCR is ready to use! Restart the server to enable it.")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Error downloading TrOCR: {e}")
        print("\nTroubleshooting tips:")
        print("  1. Check your internet connection")
        print("  2. Try running: pip install --upgrade transformers huggingface_hub")
        print("  3. If behind a firewall, set HF_HUB_OFFLINE=0")
        return False


if __name__ == "__main__":
    download_trocr_model()

