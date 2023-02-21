import os
import os.path
from pathlib import PurePath
import cv2 as cv
import numpy as np

def crop_matched_patterns(\
        target_image_path=PurePath('./target.png'), \
        pattern_image_path=PurePath('pattern.png'), \
        results_dir=PurePath('./cropped-matched'), \
        threshold=0.85
      ):

    (filename_root, filename_ext) = os.path.splitext(target_image_path)

    # Read target
    target_image = cv.imread(target_image_path)
    target_width, target_height, target_depth = target_image.shape
    print( \
        f'target_image = {target_image_path},' + \
        f' width = {target_width},' + \
        f' height = {target_height},' + \
        f' depth = {target_depth}' \
      )

    # Read pattern
    pattern_image = cv.imread(pattern_image_path)
    pattern_width, pattern_height, pattern_depth = pattern_image.shape
    print( \
        f'pattern_image = {pattern_image_path},' + \
        f' width = {pattern_width},' + \
        f' height = {pattern_height},' + \
        f' depth = {pattern_depth}' \
      )

    ### Available methods for pattern matching in OpenCV
    #
    # cv.TM_CCOEFF  cv.TM_CCOEFF_NORMED
    # cv.TM_CCORR   cv.TM_CCORR_NORMED
    # cv.TM_SQDIFF  cv.TM_SQDIFF_NORMED

    # Apply template Matching
    result = cv.matchTemplate(target_image, pattern_image, cv.TM_SQDIFF_NORMED)
    result_width, result_height = result.shape
    print( \
        f'result_image:\n' + \
        f' width = {result_width},' + \
        f' height = {result_height},'
      )

    if not os.path.isdir(results_dir):
        os.mkdir(results_dir)

    ### To find a single point:
    # min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)
    # top_left = min_loc  # should be 'max_loc' if NOT using 'cv.TM_SQDIFF' or 'cv.TM_SQDIFF_NOREMD'
    # bottom_right = (top_left[0] + w, top_left[1] + h)

    cv.imwrite("convolution.png", result)

    for pt in np.where(result <= (1 - threshold)):
        print(pt)

    for pt in np.where(result <= (1 - threshold)):
        x0 = pt[0]
        y0 = pt[1]
        x1 = x0 + pattern_width
        y1 = y0 + pattern_height
        cropped_path_name = PurePath( \
            filename_root + \
            ('_{:0>5}x{:0>5}'.format(x0, y0)) + \
            filename_ext \
          )
        cropped_path_full = str(results_dir/cropped_path_name)
        print( \
            { 'coords': [x0, y0, pattern_width, pattern_height], \
              'path'  : str(cropped_path_name) \
            } \
          )
        cropped = target_image[y0:y1, x0:x1]
        cv.imwrite(cropped_path_full, cropped)

crop_matched_patterns( \
    target_image_path = './test-target.png', \
    pattern_image_path = './test-pattern.png', \
    results_dir = './test-results', \
    threshold = 0.85 \
  )
