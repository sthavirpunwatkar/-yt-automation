import cv2
import numpy as np
import easyocr

# Initialize the OCR reader globally so it doesn't reload on every image
_reader = None

def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(['en'], gpu=False)
    return _reader

def remove_watermark(image_path: str, output_path: str):
    """Detects text in an image and uses OpenCV inpainting to remove it."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image at {image_path}")
        
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    
    reader = get_reader()
    results = reader.readtext(img)
    
    has_text = False
    for (bbox, text, prob) in results:
        # Ignore very short or low probability text
        if prob < 0.2 or len(text.strip()) < 2:
            continue
            
        pts = np.array(bbox, dtype=np.int32)
        cv2.fillPoly(mask, [pts], 255)
        has_text = True
        
    if not has_text:
        # No text detected, just return the original
        if image_path != output_path:
            cv2.imwrite(output_path, img)
        return

    # Expand the mask slightly to catch compression artifacts around the text
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=2)
    
    # Inpaint using Telea algorithm
    inpainted_img = cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)
    cv2.imwrite(output_path, inpainted_img)
