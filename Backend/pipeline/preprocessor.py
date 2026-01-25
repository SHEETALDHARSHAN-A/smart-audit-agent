import cv2
import numpy as np

class ImagePreprocessor:
    def __init__(self):
        pass

    def preprocess(self, image_path: str) -> np.ndarray:
        """
        Reads an image and applies pre-processing steps:
        - Grayscale conversion
        - Upscaling (2x)
        - Gaussian Blur
        - Otsu's Thresholding (Binarization)
        """
        # Read image in grayscale
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Could not read image at {image_path}")

        # Upscale
        img_upscaled = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Denoise
        img_blurred = cv2.GaussianBlur(img_upscaled, (5, 5), 0)

        # Binarize
        _, img_thresh = cv2.threshold(img_blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return img_thresh

    def save_temp_image(self, img: np.ndarray, original_path: str) -> str:
        """
        Saves the processed image to a temp path for OCR consumption.
        """
        import os
        filename = os.path.basename(original_path)
        temp_dir = "temp_processed"
        os.makedirs(temp_dir, exist_ok=True)
        save_path = os.path.join(temp_dir, f"proc_{filename}")
        cv2.imwrite(save_path, img)
        return save_path
