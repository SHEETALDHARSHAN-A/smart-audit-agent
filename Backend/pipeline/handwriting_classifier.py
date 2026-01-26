"""
Fast Handwriting vs Printed Text Classifier
Uses gradient-based features for real-time inference (No GPU required)
Optimized for speed with numpy vectorization
"""
import numpy as np
import cv2
from typing import Tuple, List
import logging


class HandwritingClassifier:
    """
    Fast ML-free classifier using statistical features
    Inference: ~2-5ms per region on CPU
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Thresholds tuned for invoice/bill documents
        self.thresholds = {
            'stroke_var': 0.35,      # Variance threshold for stroke width
            'edge_density_low': 0.02,
            'edge_density_high': 0.18,
            'line_ratio': 0.15,      # Ratio of straight lines to total contours
            'aspect_irregularity': 0.4,
            'contour_complexity': 0.3
        }
    
    def classify_region(self, region: np.ndarray) -> Tuple[str, float]:
        """
        Fast classification of a text region.
        
        Args:
            region: BGR or Grayscale image of text region
            
        Returns:
            Tuple of (type: 'handwritten'|'printed'|'mixed', confidence: 0.0-1.0)
        """
        if region is None or region.size == 0:
            return ('printed', 0.5)
        
        try:
            features = self.get_features(region)
            return self._classify_from_features(features)
        except Exception as e:
            self.logger.debug(f"Classification failed: {e}")
            return ('printed', 0.5)
    
    def get_features(self, region: np.ndarray) -> np.ndarray:
        """
        Extract 8-feature vector for classification (vectorized for speed)
        
        Features:
        0. Edge density
        1. Stroke width variance
        2. Horizontal line ratio
        3. Contour complexity
        4. Character spacing variance
        5. Ink density
        6. Gradient direction variance
        7. Aspect ratio irregularity
        """
        # Convert to grayscale if needed
        if len(region.shape) == 3:
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        else:
            gray = region.copy()
        
        h, w = gray.shape
        
        # Quick return for very small regions
        if h < 10 or w < 15:
            return np.zeros(8)
        
        # 1. Edge density (fast Sobel)
        sobel_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
        edges = np.sqrt(sobel_x.astype(np.float32)**2 + sobel_y.astype(np.float32)**2)
        edge_density = np.mean(edges > 50) 
        
        # 2. Stroke width variance using distance transform
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
        stroke_pixels = dist[dist > 0]
        stroke_var = np.std(stroke_pixels) / (np.mean(stroke_pixels) + 1e-6) if len(stroke_pixels) > 10 else 0
        
        # 3. Horizontal line ratio (detect printed text lines)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w//4, 10), 1))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
        h_line_ratio = np.sum(horizontal > 0) / (np.sum(binary > 0) + 1e-6)
        
        # 4. Contour complexity (handwriting has more complex contours)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            total_area = sum(cv2.contourArea(c) for c in contours)
            total_perimeter = sum(cv2.arcLength(c, True) for c in contours)
            contour_complexity = total_perimeter / (np.sqrt(total_area) + 1e-6) if total_area > 0 else 0
        else:
            contour_complexity = 0
        
        # 5. Character spacing variance (printed text is more uniform)
        col_profile = np.sum(binary, axis=0)
        gaps = np.diff(np.where(col_profile > 0)[0]) if np.any(col_profile > 0) else np.array([])
        spacing_var = np.std(gaps) / (np.mean(gaps) + 1e-6) if len(gaps) > 2 else 0
        
        # 6. Ink density
        ink_density = np.sum(binary > 0) / binary.size
        
        # 7. Gradient direction variance (handwriting has varied directions)
        angles = np.arctan2(sobel_y.astype(np.float32), sobel_x.astype(np.float32) + 1e-6)
        significant = edges > 30
        grad_var = np.std(angles[significant]) if np.sum(significant) > 20 else 0
        
        # 8. Aspect ratio irregularity of connected components
        if contours:
            aspect_ratios = []
            for c in contours[:20]:  # Limit for speed
                x, y, cw, ch = cv2.boundingRect(c)
                if ch > 0:
                    aspect_ratios.append(cw / ch)
            aspect_irreg = np.std(aspect_ratios) if len(aspect_ratios) > 2 else 0
        else:
            aspect_irreg = 0
        
        return np.array([
            edge_density,
            stroke_var,
            h_line_ratio,
            contour_complexity / 20,  # Normalize
            spacing_var,
            ink_density,
            grad_var,
            aspect_irreg
        ], dtype=np.float32)
    
    def _classify_from_features(self, features: np.ndarray) -> Tuple[str, float]:
        """
        Rule-based classification with confidence scoring
        Faster than ML model, works without training data
        """
        edge_density = features[0]
        stroke_var = features[1]
        h_line_ratio = features[2]
        contour_complexity = features[3]
        spacing_var = features[4]
        ink_density = features[5]
        grad_var = features[6]
        aspect_irreg = features[7]
        
        # Scoring system: positive = handwritten, negative = printed
        score = 0.0
        
        # Stroke width variance (handwriting varies more)
        if stroke_var > 0.5:
            score += 0.25
        elif stroke_var < 0.2:
            score -= 0.2
        
        # Edge density in handwriting range
        if 0.02 < edge_density < 0.15:
            score += 0.15
        elif edge_density > 0.2:
            score -= 0.15  # Dense printed text
        
        # Horizontal lines (printed text has more)
        if h_line_ratio > 0.3:
            score -= 0.2
        elif h_line_ratio < 0.1:
            score += 0.1
        
        # Contour complexity (handwriting more complex)
        if contour_complexity > 0.4:
            score += 0.2
        elif contour_complexity < 0.2:
            score -= 0.1
        
        # Spacing variance (handwriting more irregular)
        if spacing_var > 0.5:
            score += 0.15
        elif spacing_var < 0.2:
            score -= 0.1
        
        # Gradient direction variance (handwriting has varied strokes)
        if grad_var > 0.8:
            score += 0.15
        elif grad_var < 0.4:
            score -= 0.1
        
        # Aspect ratio irregularity
        if aspect_irreg > 0.5:
            score += 0.1
        
        # Convert score to classification
        confidence = min(abs(score) / 0.6, 1.0)  # Normalize to 0-1
        
        if score > 0.15:
            return ('handwritten', confidence)
        elif score < -0.15:
            return ('printed', confidence)
        else:
            return ('mixed', 0.5 + abs(score))
    
    def classify_regions_batch(self, regions: List[np.ndarray]) -> List[Tuple[str, float]]:
        """
        Batch classification for multiple regions (parallel-ready)
        """
        return [self.classify_region(r) for r in regions]


# Fast utility functions for number recognition
def is_likely_number_region(region: np.ndarray) -> bool:
    """Quick check if region likely contains numbers (amounts/quantities)"""
    if region is None or region.size == 0:
        return False
    
    # Numbers tend to have:
    # - Consistent height
    # - Regular spacing
    # - Limited character set
    
    if len(region.shape) == 3:
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    else:
        gray = region
    
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Check aspect ratio (numbers are usually wider than tall for multi-digit amounts)
    h, w = binary.shape
    if w > h * 0.5:  # Reasonable aspect for numbers
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if 1 <= len(contours) <= 15:  # Reasonable number of digits
            return True
    
    return False
