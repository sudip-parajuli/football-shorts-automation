import numpy as np

def make_rgb(frame):
    if len(frame.shape) == 2:
        # Grayscale to RGB
        return np.dstack([frame] * 3)
    elif len(frame.shape) == 3:
        if frame.shape[2] == 4:
            # RGBA to RGB
            return frame[:,:,:3]
        elif frame.shape[2] == 2:
            # Grayscale + Alpha to RGB
            # We take the first channel as grayscale and stack it
            return np.dstack([frame[:,:,0]] * 3)
        elif frame.shape[2] == 3:
            return frame
    
    # Fallback for any other weirdness
    if len(frame.shape) == 3 and frame.shape[2] > 3:
        return frame[:,:,:3]
    
    return frame

# Test Case 1: Grayscale
gray = np.zeros((10, 10))
rgb1 = make_rgb(gray)
assert rgb1.shape == (10, 10, 3)
print("Test Case 1 passed: Grayscale to RGB correctly.")

# Test Case 2: RGBA
rgba = np.zeros((10, 10, 4))
rgb2 = make_rgb(rgba)
assert rgb2.shape == (10, 10, 3)
print("Test Case 2 passed: RGBA to RGB correctly.")

# Test Case 3: 2-Channel (Grayscale + Alpha)
ga = np.zeros((10, 10, 2))
rgb3 = make_rgb(ga)
assert rgb3.shape == (10, 10, 3)
print("Test Case 3 passed: 2-Channel GA to RGB correctly.")

# Test Case 4: Already RGB
rgb_in = np.zeros((10, 10, 3))
rgb4 = make_rgb(rgb_in)
assert rgb4.shape == (10, 10, 3)
print("Test Case 4 passed: RGB remains RGB.")
