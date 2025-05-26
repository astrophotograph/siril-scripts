import cv2
import numpy as np

file = "/Users/erewhon/AstroPhotos/tmp/Lagoon_Nebula_334x10sec_T22C_2025-05-09_3340s_drizzle_2x_square_UC_BE_PS_CR_SPCC_StarSep_ST_StarComb_DG_UC.fit.tif"

# Function to map each intensity level to output intensity level.
MAX_VALUE = 255
max_v = 0
def pixelVal(pix, r1, s1, r2, s2):
    global max_v
    if pix > max_v:
        max_v = pix
    if 0 <= pix and pix <= r1:
        return (s1 / r1)*pix
    elif r1 < pix and pix <= r2:
        return ((s2 - s1)/(r2 - r1)) * (pix - r1) + s1
    else:
        return ((MAX_VALUE - s2)/(MAX_VALUE - r2)) * (pix - r2) + s2

img = cv2.imread(file)

r1 = 50
s1 = 0
r2 = 200
s2 = 255

pixelVal_vec = np.vectorize(pixelVal)
contrast_stretched = pixelVal_vec(img, r1, s1, r2, s2)

print(f"{max_v=}")

cv2.imshow("test.png", img)
cv2.imshow("test.png", contrast_stretched)

cv2.waitKey(0)
cv2.destroyAllWindows()