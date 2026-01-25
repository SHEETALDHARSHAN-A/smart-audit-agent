from paddleocr import PaddleOCR
import logging

class OCREngine:
    def __init__(self, lang='en'):
        # Initialize PaddleOCR
        # use_gpu=True if available, else False. Auto-detect usually works or defaults to False.
        # We can make this configurable.
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang)
        self.logger = logging.getLogger(__name__)

    def extract_text(self, image_path: str):
        """
        Runs PaddleOCR on the image.
        Returns the raw result structure.
        """
        self.logger.info(f"Running OCR on {image_path}")
        result = self.ocr.ocr(image_path)
        # PaddleOCR returns a list of lists (one for each page?), usually result[0] is the page.
        return result

    def get_text_blocks(self, image_path: str):
        """
        Returns a simplified list of text blocks.
        """
        result = self.extract_text(image_path)
        if not result or result[0] is None:
            return []
        
        # Structure: [[box, (text, confidence)], ...]
        text_blocks = []
        for line in result[0]:
            box = line[0]
            text, score = line[1]
            text_blocks.append({
                "text": text,
                "confidence": score,
                "box": box
            })
        return text_blocks
