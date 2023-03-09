import os
import os.path
from pathlib import PurePath
import cv2 as cv
import numpy as np
from scipy.signal import argrelextrema

def float_to_uint32(input_image):
    height, width = input_image.shape
    output_image = np.empty((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            output_image[y,x] = round(input_image[y,x] * 255)
    return output_image

def crop_matched_patterns(\
        target_image_path=PurePath('./target.png'), \
        pattern_image_path=PurePath('./pattern.png'), \
        results_dir=PurePath('./cropped-matched'), \
        threshold=0.95
      ):

    filename_root, filename_ext = os.path.splitext(target_image_path)

    # Create results directory if it does not exist
    if not os.path.isdir(results_dir):
        os.mkdir(results_dir)

    # Read target
    target_image = cv.imread(target_image_path)
    target_height, target_width, target_depth = target_image.shape
    print( \
        f'target_image = {target_image_path},' + \
        f' width = {target_width},' + \
        f' height = {target_height},' + \
        f' depth = {target_depth}' \
      )

    # Read pattern
    pattern_image = cv.imread(pattern_image_path)
    pattern_height, pattern_width, pattern_depth = pattern_image.shape
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
    print('template convolution')
    result_image = cv.matchTemplate(target_image, pattern_image, cv.TM_SQDIFF_NORMED)

    result_height, result_width = result_image.shape
    print(f'result_width = {result_width}, result_height = {result_height}')

    print('normalize result')
    np.linalg.norm(result_image)

    ### To find a single point:
    # min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)
    # top_left = min_loc  # should be 'max_loc' if NOT using 'cv.TM_SQDIFF' or 'cv.TM_SQDIFF_NOREMD'
    # bottom_right = (top_left[0] + w, top_left[1] + h)

    # Show the convolution image:
    visible_result = float_to_uint32(result_image)
    cv.imwrite("./convolution.png", visible_result)

    # ----------------------------------------------------------------
    #img = np.arange(64 * 64).reshape(64, 64)
    #img_copy = np.arange(64 * 64).reshape(64, 64)

    # The "search_image" is a white image that is the smallest even
    # multiple of the pattern image that is larger than the
    # result_image.
    search_image = np.ones( \
        ( result_height - (result_height % -pattern_height), \
          result_width  - (result_width  % -pattern_width ), \
        ), \
        dtype=np.float32
      )
    search_height, search_width = search_image.shape
    print(f"search_height = {search_height}, search_width = {search_width}")

    # Copy the result into the "search_image".
    search_image[0:result_height, 0:result_width] = result_image

    # We use reshape to cut the search_image up into pieces exactly
    # equal in size to the pattern image.
    chunk_width  = round(search_width  / pattern_width)
    chunk_height = round(search_height / pattern_height)
    print(f"chunk_width = {chunk_height}, chunk_height = {chunk_width}")

    chunks = search_image.reshape(chunk_height, pattern_height, chunk_width, pattern_width)

    for y in range(chunk_height):
        for x in range(chunk_width):
            tile = chunks[y, :, x, :]
            visible_tile = float_to_uint32(tile)
            #cv.imwrite(f"./{x}x{y}.png", visible_tile)
            (min_y, min_x) = np.unravel_index(np.argmin(tile), (pattern_height, pattern_width))
            global_y = y * pattern_height + min_y
            global_x = x * pattern_width  + min_x
            if tile[min_y, min_x] <= (1.0 - threshold):
                print(f"argmin(chunk[{y},{x}]) -> ({global_x}, {global_y})")
                cut_file_name = f'{global_x:0>5}x{global_y:0>5}.png'
                cv.imwrite( \
                    cut_file_name, \
                    target_image[ \
                        global_y : global_y + pattern_height, \
                        global_x : global_x + pattern_width \
                      ] \
                  )
            else:
                pass

    # i = 0
    # for pt in zip(*matched_points):
    #     if not len(pt) == 2:
    #         print(f'got empty point for index {i}')
    #     else:
    #         x0 = pt[0]
    #         y0 = pt[1]
    #         x1 = x0 + pattern_width
    #         y1 = y0 + pattern_height
    #         cropped_path_name = PurePath( \
    #             filename_root + \
    #             ('_{:0>5}x{:0>5}'.format(x0, y0)) + \
    #             filename_ext \
    #           )
    #         cropped_path_full = str(results_dir/cropped_path_name)
    #         print( \
    #             { 'coords': [x0, y0, pattern_width, pattern_height], \
    #               'path'  : str(cropped_path_name) \
    #             } \
    #           )
    #         cropped = target_image[y0:y1, x0:x1]
    #         if len(cropped) > 0:
    #             cv.imwrite(cropped_path_full, cropped)
    #         else:
    #             print(f'{i}: {pt} yields empty crop')
    #     i = i + 1

def test_crop_matched_patterns():
    crop_matched_patterns( \
        target_image_path = './test-target.png', \
        pattern_image_path = './test-pattern.png', \
        results_dir = './test-results', \
        threshold = 0.75 \
      )

if __name__ == '__main__':
    test_crop_matched_patterns()
