import cv2 as cv
import numpy as np
from pathlib import PurePath

def applyPixmapMask(sourcePath, maskPath, targetPath, saveAs=None):
  if saveAs is None:
    saveAs = PurePath('./masked_' + str(targetPath.name))
  else:
    pass
  sourceImg = cv.imread(str(sourcePath)) * np.float32(1.0 / 255.0)
  maskImg   = cv.imread(str(maskPath)) * np.float32(1.0 / 255.0)
  result = np.uint8(cv.multiply(sourceImg, maskImg) * np.float32(255.0))
  cv.imwrite(str(targetPath), result)

#applyPixmapMask(
#    PurePath('/home/ramin/Desktop/examples/david-revoy_001.png'),
#    PurePath('/home/ramin/Desktop/examples/david-revoy_001_mask.png'),
#    PurePath('/home/ramin/Desktop/examples/result.png'),
#  )
