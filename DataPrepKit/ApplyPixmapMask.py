import cv2 as cv
import numpy as np
from pathlib import Path
from collections.abc import Iterable
import gc
import os

def checkImageFileType(path):
    suf = str(path.suffix).lower()
    return (
        suf == '.png' or
        suf == '.bmp' or
        suf == '.jpg'
      )

def getWidthHeight(img):
    shape = list(img.shape)
    return (shape[1], shape[0])


def applyPixmapMask(sourcePath, maskImg, saveAs=None, verbose=False):
    if not (sourcePath.exists() and sourcePath.is_file()):
        raise Exception(f'file not found: {sourcePath!s}')
    else:
        pass
    if saveAs is None:
        saveAs = sourcePath.parent / Path('./masked_' + str(sourcePath.name))
    else:
        saveAs = saveAs / Path('./masked_' + str(sourcePath.name))
    if verbose:
        print(f'Input: {sourcePath!s}')
    else:
        pass
    sourceImg = cv.imread(os.fspath(sourcePath))
    if sourceImg is None:
        print(f'ERROR: failed to load image path: {sourcePath!s}')
    else:
        sourceImg = sourceImg * np.float32(1.0 / 255.0)
        try:
            (h_in  , w_in  ) = getWidthHeight(sourceImg)
            (h_mask, w_mask) = getWidthHeight(maskImg)
            h = max(0, min(h_in, h_mask))
            w = max(0, min(w_in, w_mask))
            result = np.uint8(cv.multiply(sourceImg[0:h, 0:w], maskImg[0:h, 0:w]) * np.float32(255.0))
            if verbose:
                print(f'Output: {saveAs!s}')
            else:
                pass
            saveAs.parent.mkdir(parents=True, exist_ok=True)
            cv.imwrite(os.fspath(saveAs), result)
        except Exception as e:
            print(f'ERROR: on input {sourceImg!s}')
            print(e)

def applyMaskRecursive(dirPath, maskImg, verbose=False):
    if isinstance(dirPath, Iterable):
        for sourcePath in dirPath:
            applyMaskRecursive(sourcePath, maskImg, verbose=verbose)
    elif isinstance(dirPath, Path) and dirPath.is_dir():
        applyMaskRecursive(Path(dirPath).iterdir(), maskImg, verbose=verbose)
    elif checkImageFileType(dirPath):
        #print(f'apply mask to: {sourcePath!s})')
        applyPixmapMask(dirPath, maskImg, saveAs=None, verbose=verbose)
        gc.collect()
    else:
        print(f'WARNING: ignoring file with unrecognized suffix {sourcePath.suffix!r}: {sourcePath}')

def applyAllFiles(dirPath, maskPath, verbose=False):
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
    applyMaskRecursive(dirPath, maskImg, verbose=verbose)
