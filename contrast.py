import cv2
import numpy as np
import argparse
from pathlib import Path

def adjust_contrast(image_path, method='linear', params=None, output_path=None):
    """
    Adjust the contrast of a TIF image using various methods.
    
    Args:
        image_path (str): Path to the input TIF image
        method (str): Method to use for contrast adjustment:
            - 'linear': Linear scaling with alpha and beta
            - 'sigmoid': Sigmoid function for smoother contrast
            - 'gamma': Gamma correction
            - 'equalize': Histogram equalization
        params (dict): Parameters for the selected method
        output_path (str, optional): Path to save the adjusted image. If None,
            will save as 'input_name_contrast.tif' in the same directory.
    
    Returns:
        str: Path to the saved image
    """
    # Read the image
    img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    
    if img is None:
        raise ValueError(f"Could not read image from {image_path}")
    
    # Get the image data type to preserve it
    original_dtype = img.dtype
    
    # Convert to float for processing
    img_float = img.astype(np.float32)
    
    # Apply contrast adjustment based on the selected method
    if method == 'linear':
        if params is None:
            params = {'alpha': 1.5, 'beta': 0}
        
        # Get min and max values to normalize
        min_val = np.min(img_float)
        max_val = np.max(img_float)
        
        # Normalize to 0-1 range
        if max_val > min_val:
            normalized = (img_float - min_val) / (max_val - min_val)
        else:
            normalized = img_float
        
        # Apply contrast adjustment (alpha)
        adjusted = params['alpha'] * (normalized - 0.5) + 0.5 + params['beta']
        
        # Clip to 0-1 range
        adjusted = np.clip(adjusted, 0, 1)
        
        # Scale back to original range
        adjusted = adjusted * (max_val - min_val) + min_val
        
    elif method == 'sigmoid':
        if params is None:
            params = {'gain': 5, 'cutoff': 0.5}
        
        # Normalize to 0-1 range
        min_val = np.min(img_float)
        max_val = np.max(img_float)
        
        if max_val > min_val:
            normalized = (img_float - min_val) / (max_val - min_val)
        else:
            normalized = img_float
        
        # Apply sigmoid function for contrast adjustment
        adjusted = 1 / (1 + np.exp(-params['gain'] * (normalized - params['cutoff'])))
        
        # Scale back to original range
        adjusted = adjusted * (max_val - min_val) + min_val
        
    elif method == 'gamma':
        if params is None:
            params = {'gamma': 0.5}
        
        # Normalize to 0-1 range
        min_val = np.min(img_float)
        max_val = np.max(img_float)
        
        if max_val > min_val:
            normalized = (img_float - min_val) / (max_val - min_val)
        else:
            normalized = img_float
        
        # Apply gamma correction
        adjusted = np.power(normalized, params['gamma'])
        
        # Scale back to original range
        adjusted = adjusted * (max_val - min_val) + min_val
        
    elif method == 'equalize':
        # Handle different channel counts
        if len(img.shape) == 2 or img.shape[2] == 1:  # Grayscale
            # Convert to 8-bit for histogram equalization
            img_8bit = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            adjusted = cv2.equalizeHist(img_8bit)
            
            # Scale back to original range
            min_val = np.min(img_float)
            max_val = np.max(img_float)
            adjusted = adjusted.astype(np.float32) / 255.0 * (max_val - min_val) + min_val
            
        else:  # Color image
            # Convert to YCrCb color space
            img_ycrcb = cv2.cvtColor(cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8), 
                                    cv2.COLOR_BGR2YCrCb)
            
            # Equalize the Y channel
            img_ycrcb[:, :, 0] = cv2.equalizeHist(img_ycrcb[:, :, 0])
            
            # Convert back to BGR
            adjusted = cv2.cvtColor(img_ycrcb, cv2.COLOR_YCrCb2BGR).astype(np.float32)
            
            # Scale back to original range
            min_val = np.min(img_float)
            max_val = np.max(img_float)
            adjusted = adjusted / 255.0 * (max_val - min_val) + min_val
    else:
        raise ValueError(f"Unknown contrast adjustment method: {method}")
    
    # Convert back to original data type
    if original_dtype == np.uint8:
        adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)
    elif original_dtype == np.uint16:
        adjusted = np.clip(adjusted, 0, 65535).astype(np.uint16)
    else:
        adjusted = adjusted.astype(original_dtype)
    
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
    parser.add_argument('--method', type=str, default='linear', 
                      choices=['linear', 'sigmoid', 'gamma', 'equalize'],
                      help='Method for contrast adjustment')
    parser.add_argument('--alpha', type=float, default=1.5, 
                      help='Contrast factor for linear method')
    parser.add_argument('--beta', type=float, default=0, 
                      help='Brightness adjustment for linear method')
    parser.add_argument('--gain', type=float, default=5, 
                      help='Gain factor for sigmoid method')
    parser.add_argument('--cutoff', type=float, default=0.5, 
                      help='Cutoff value for sigmoid method')
    parser.add_argument('--gamma', type=float, default=0.5, 
                      help='Gamma value for gamma correction')
    parser.add_argument('--output', type=str, help='Output path (optional)')
    
    args = parser.parse_args()
    
    # Set parameters based on the method
    params = {}
    if args.method == 'linear':
        params = {'alpha': args.alpha, 'beta': args.beta}
    elif args.method == 'sigmoid':
        params = {'gain': args.gain, 'cutoff': args.cutoff}
    elif args.method == 'gamma':
        params = {'gamma': args.gamma}
    
    try:
        output_path = adjust_contrast(args.image, args.method, params, args.output)
        print(f"Saved contrast-adjusted image to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()