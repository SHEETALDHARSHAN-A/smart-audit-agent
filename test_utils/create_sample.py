import cv2
import numpy as np
import os

def create_sample_invoice(output_path="sample_invoice.png"):
    # Create a white image
    img = np.ones((800, 600), dtype=np.uint8) * 255

    # Define font and layout
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Header
    cv2.putText(img, "INVOICE", (200, 50), font, 1.5, (0), 2)
    cv2.putText(img, "Tech Solutions Inc.", (50, 100), font, 0.8, (0), 2)
    cv2.putText(img, "123 Innovation Dr, Tech City", (50, 130), font, 0.6, (0), 1)
    
    # Invoice Details
    cv2.putText(img, "Invoice No: INV-2023-001", (350, 100), font, 0.6, (0), 1)
    cv2.putText(img, "Date: 25/01/2026", (350, 130), font, 0.6, (0), 1)
    
    # Line Items Header
    cv2.putText(img, "Description       Qty    Price    Amount", (50, 200), font, 0.6, (0), 2)
    cv2.line(img, (50, 210), (550, 210), (0), 1)
    
    # Items
    cv2.putText(img, "Wireless Mouse    2      500.00   1000.00", (50, 240), font, 0.6, (0), 1)
    cv2.putText(img, "USB Hub           1      350.50   350.50", (50, 270), font, 0.6, (0), 1)
    
    # Total
    cv2.line(img, (50, 300), (550, 300), (0), 1)
    cv2.putText(img, "Total: 1350.50", (350, 330), font, 0.8, (0), 2)
    
    # Footer
    cv2.putText(img, "Thank you for your business!", (150, 400), font, 0.6, (0), 1)
    
    cv2.imwrite(output_path, img)
    print(f"Created {output_path}")

if __name__ == "__main__":
    create_sample_invoice()
