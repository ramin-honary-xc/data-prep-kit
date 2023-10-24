import cv2 as cv
import numpy as np
from pathlib import Path
import gc
import os

def checkImageFileType(path):
    return (
        path.suffix == '.png' or
        path.suffix == '.bmp' or
        path.suffix == '.jpg'
      )

def applyPixmapMask(sourcePath, maskImg, saveAs=None):
    if not (sourcePath.exists() and sourcePath.is_file()):
        raise Exception(f'file not found: {sourcePath!s}')
    else:
        pass
    if saveAs is None:
        saveAs = sourcePath.parent / Path('./masked_' + str(sourcePath.name))
    else:
        saveAs = saveAs / Path('./masked_' + str(sourcePath.name))
    sourceImg = cv.imread(os.fspath(sourcePath))
    if sourceImg is None:
        print(f'failed to load image path: {sourcePath!s}')
    else:
         sourceImg = sourceImg * np.float32(1.0 / 255.0)
         result = np.uint8(cv.multiply(sourceImg, maskImg) * np.float32(255.0))
         saveAs.parent.mkdir(parents=True, exist_ok=True)
         cv.imwrite(os.fspath(saveAs), result)

def applyMaskRecursive(dirPath, maskImg):
    for sourcePath in Path(dirPath).iterdir():
        if sourcePath.is_dir():
            applyMaskRecursive(sourcePath, maskImg)
        elif checkImageFileType(sourcePath):
            print(f'apply mask to: {sourcePath!s})')
            applyPixmapMask(sourcePath, maskImg)
            gc.collect()
        else:
            print(f'ignoring file of incorrect type: {sourcePath}')

def applyAllFiles(dirPath, maskPath):
    maskImg = None
    if not (maskPath.exists() and maskPath.is_file()):
        raise Exception(f'mask file not found: {maskPath!s}')
    else:
        pass
    maskImg  = cv.imread(os.fspath(maskPath))
    if maskImg is None:
        raise Exception(f'failed to load mask image: {maskPath!s}')
    else:
        pass
    maskImg = maskImg * np.float32(1.0 / 255.0)
    applyMaskRecursive(dirPath, maskImg)

#applyAllFiles(
#    Path('/home/ramin/Desktop/masking/inputs'),
#    Path('/home/ramin/Desktop/masking/mask.bmp'),
#  )
