import cv2
import numpy as np
import argparse
from pathlib import Path

def adjust_contrast(image_path, alpha, output_path=None):
    """
    Adjust the contrast of a TIF image.
    
    Args:
        image_path (str): Path to the input TIF image
        alpha (float): Contrast control (1.0 means no change)
            - alpha > 1 : increase contrast
            - 0 < alpha < 1 : decrease contrast
        output_path (str, optional): Path to save the adjusted image. If None,
            will save as 'input_name_contrast.tif' in the same directory.
    
    Returns:
        str: Path to the saved image
    """
    # Read the image
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    
    if img is None:
        raise ValueError(f"Could not read image from {image_path}")
    
    # Adjust contrast
    adjusted = cv2.convertScaleAbs(img, alpha=alpha, beta=0)
    
    # Determine output path
    if output_path is None:
        input_path = Path(image_path)
        output_path = input_path.parent / f"{input_path.stem}_contrast{input_path.suffix}"
    
    # Save the adjusted image
    cv2.imwrite(str(output_path), adjusted)
    
    return str(output_path)

def main():
    parser = argparse.ArgumentParser(description='Adjust contrast of a TIF image')
    parser.add_argument('image', type=str, help='Path to the TIF image')
    parser.add_argument('--alpha', type=float, default=1.5, 
                      help='Contrast factor. >1 increases contrast, <1 decreases contrast')
    parser.add_argument('--output', type=str, help='Output path (optional)')
    
    args = parser.parse_args()
    
    try:
        output_path = adjust_contrast(args.image, args.alpha, args.output)
        print(f"Saved contrast-adjusted image to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()