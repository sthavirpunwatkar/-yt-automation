import cv2
import numpy as np
from pathlib import Path

def remove_watermark(image_path: Path, output_path: Path = None):
    """
    Attempts to heuristic-inpaint watermarks from an image using OpenCV.
    Uses Morphological Top-Hat transform to isolate semi-transparent white/gray text
    (typical of stock image watermarks), then applies Telea inpainting to blur them out.
    """
    if output_path is None:
        output_path = image_path

    # Read the image
    img = cv2.imread(str(image_path))
    if img is None:
        return

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Use Top-Hat transform to find light regions on a darker background.
    # We use a rectangular kernel to catch text structures.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)

    # Threshold the top-hat image to create a mask of the watermark candidates
    # Lowering the threshold catches fainter watermarks but increases false positives.
    _, mask = cv2.threshold(tophat, 60, 255, cv2.THRESH_BINARY)

    # Dilate the mask slightly to cover the semi-transparent anti-aliased edges of the text
    mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)

    # Use OpenCV's inpaint function to seamlessly clone over the masked areas
    inpainted = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)

    # Save the result
    cv2.imwrite(str(output_path), inpainted)

