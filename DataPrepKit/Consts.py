import numpy as np

def __color_forest_fire():
    a = np.empty((256, 3), np.uint8)
    for i in range(0,256):
        a[i,0] = 0 if i < 64 else 4*(i-64) if i < 128 else 255
        a[i,1] = 4*i if i < 64 else 255 if i < 128 else 255 - 2*i
        a[i,2] = 0
    return a

color_forest_fire = __color_forest_fire()
