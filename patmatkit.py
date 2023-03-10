import os
import os.path
from pathlib import PurePath
import math
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

class RegionSize():
    def __init__(self, x, y, width, height):
        self.x_min = x
        self.y_min = y
        self.x_max = x + width
        self.y_max = y + height

    def crop_image(self, image):
        return image[ \
            self.y_min : self.y_max, \
            self.x_min : self.x_max \
          ]

    def as_file_name(self):
        return PurePath(f'{self.x_min:0>5}x{self.y_min:0>5}.png')

    def crop_write_image(self, image, results_dir):
        """Takes an image to crop, crops it with 'crop_image()', takes a
        PurePath() 'results_dir', writes the cropped image to the file
        path given by (results_dir/self.as_file_name()) using
        'cv.imwrite()'.
        """
        write_path = str(results_dir / self.as_file_name())
        print(f'crop_write_image -> {write_path}')
        cv.imwrite(write_path, self.crop_image(image))

class DistanceMap():
    """Construct DistanceMap() by providing a target image and a pattern
    matching image. For every point in the target image, the
    square-difference distance between the region of pixels at that
    point that overlap the pattern image and the pattern image iteself
    is computed and stored as a Float32 value in a "distance_map"
    image. All images are retained in memory and can be used to
    extract regions of the target image that most resemble the pattern
    image.
    """

    def __init__(self, target_image, pattern_image):
        """Takes two 2D-images, NumPy arrays loaded from files by
        OpenCV. Constructing this object computes the convolution and
        square-difference distance map.
        """
        pat_shape = pattern_image.shape
        self.pattern_height = pat_shape[0]
        self.pattern_width  = pat_shape[1]
        print( \
            f'pattern_width = {self.pattern_width},' + \
            f' pattern_height = {self.pattern_height},'
          )

        targ_shape = target_image.shape
        self.target_height = targ_shape[0]
        self.target_width  = targ_shape[1]
        print( \
            f'target_width = {self.target_width},' + \
            f' target_height = {self.target_height},'
          )

        if float(self.pattern_width)  > self.target_width  / 2 * 3 and \
           float(self.pattern_height) > self.target_height / 2 * 3 :
            raise ValueError(\
                "pattern image is too large relative to target image", \
                {'pattern_width': self.pattern_width, \
                 'pattern_height': self.pattern_height, \
                 'target_width': self.target_width, \
                 'target_height': self.target_height
                }
              )
        else:
            pass

        # When searching the convolution result for local minima, we could
        # use a window size the same as the pattern size, but a slightly
        # finer window size tends to have better results. If possible, halve
        # each dimension of pattern size to define the window size.

        self.window_height = math.ceil(self.pattern_height / 2) \
            if self.pattern_height >= 4 else self.pattern_height
        self.window_width  = math.ceil(self.pattern_width  / 2) \
            if self.pattern_width  >= 4 else self.pattern_width

        print(f'window_height = {self.window_height}, window_width = {self.window_width}')

        ### Available methods for pattern matching in OpenCV
        #
        # cv.TM_CCOEFF  cv.TM_CCOEFF_NORMED
        # cv.TM_CCORR   cv.TM_CCORR_NORMED
        # cv.TM_SQDIFF  cv.TM_SQDIFF_NORMED

        # Apply template Matching
        pre_distance_map = cv.matchTemplate(target_image, pattern_image, cv.TM_SQDIFF_NORMED)
        pre_dist_map_height, pre_dist_map_width = pre_distance_map.shape
        print(f"pre_dist_map_height = {pre_dist_map_height}, pre_dist_map_width = {pre_dist_map_width}")

        # Normalize result
        np.linalg.norm(pre_distance_map)

        # The "search_image" is a white image that is the smallest
        # even multiple of the window size that is larger than the
        # distance_map.
        self.distance_map = np.ones( \
            ( pre_dist_map_height - (pre_dist_map_height % -self.window_height), \
              pre_dist_map_width  - (pre_dist_map_width  % -self.window_width ), \
            ), \
            dtype=np.float32
          )
        print(f"dist_map_height = {pre_dist_map_height}, dist_map_width = {pre_dist_map_width}")

        # Copy the result into the "search_image".
        self.distance_map[0:pre_dist_map_height, 0:pre_dist_map_width] = pre_distance_map

        # The 'find_matching_regions()' method will memoize it's results.
        self.memoized_regions = {}

    def save_distance_map(self, file_path):
        """Write the distance map that was computed at the time this object
        was constructed to a grayscale PNG image file.
        """
        cv.imwrite(str(file_path), float_to_uint32(self.distance_map))

    def find_matching_regions(self, threshold=0.95):
        """Given a 'distance_map' that has been computed by the
        'compute_distance_map()' function above, and a threshold
        value, return a list of all regions where the distance map is
        less or equal to the complement of the threshold value.

        """
        if threshold < 0.5:
            raise ValueError("threshold too low, minimum is 0.5", {'threshold': threshold})
        elif threshold in self.memoized_regions:
            return this.memoized_regions[threshold]
        else:
            pass

        # We use reshape to cut the search_image up into pieces exactly
        # equal in size to the pattern image.
        dist_map_height, dist_map_width = self.distance_map.shape
        window_vcount = round(dist_map_height / self.window_height)
        window_hcount = round(dist_map_width  / self.window_width)
        print(f"window_hcount = {window_vcount}, window_vcount = {window_hcount}")

        tiles = self.distance_map.reshape( \
            window_vcount, self.window_height, \
            window_hcount, self.window_width \
          )

        results = []
        for y in range(window_vcount):
            for x in range(window_hcount):
                tile = tiles[y, :, x, :]
                #visible_tile = float_to_uint32(tile)
                #cv.imwrite(f"./{x}x{y}.png", visible_tile)
                (min_y, min_x) = np.unravel_index( \
                    np.argmin(tile), \
                    (self.window_height, self.window_width)
                  )
                global_y = y * self.window_height + min_y
                global_x = x * self.window_width  + min_x
                if tile[min_y, min_x] <= (1.0 - threshold):
                    print(f"argmin(tiles[{y},{x}]) -> ({global_x}, {global_y})")
                    results.append( \
                        RegionSize( \
                            global_x, global_y, \
                            self.pattern_width, self.pattern_height \
                          ) \
                      )
                else:
                    pass

        self.memoized_regions[threshold] = results
        return results

def test_crop_matched_patterns(
        target_image_path=PurePath('./test-target.png'), \
        pattern_image_path=PurePath('./test-pattern.png'), \
        results_dir=PurePath('./test-results'), \
        threshold=0.78, \
        save_distance_map=PurePath('./convolution.png') \
      ):
    # Create results directory if it does not exist
    if not os.path.isdir(results_dir):
        os.mkdir(results_dir)

    target_image  = cv.imread(str(target_image_path))
    if target_image is None:
        raise FileNotFoundError(target_image_path)
    else:
        pass

    pattern_image = cv.imread(str(pattern_image_path))
    if pattern_image is None:
        raise FileNotFoundError(pattern_image_path)
    else:
        pass

    distance_map  = DistanceMap(target_image, pattern_image)

    if save_distance_map is not None:
        # Save the convolution image:
        distance_map.save_distance_map(save_distance_map)
    else:
        pass

    regions = distance_map.find_matching_regions(threshold = threshold)
    for reg in regions:
        reg.crop_write_image(target_image, results_dir)

if __name__ == '__main__':
    test_crop_matched_patterns()
