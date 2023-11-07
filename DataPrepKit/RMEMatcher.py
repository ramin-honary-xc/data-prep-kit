import DataPrepKit.FileSet as fs
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader
from DataPrepKit.RegionSize import RegionSize
import DataPrepKit.utilities as util

import math
import os
import os.path
import sys
from pathlib import PurePath

import cv2 as cv
import numpy as np

####################################################################################################
# The pattern matcing program

class DistanceMap():
    """Construct DistanceMap() by providing a target image and a pattern
    matching image. For every point in the target image, the
    square-difference distance between the region of pixels at that
    point that overlap the pattern image and the pattern image iteself
    is computed and stored as a Float32 value in a "distance_map"
    image. All images are retained in memory and can be used to
    extract regions of the target image that most resemble the pattern
    image.

    The distance map is not computed if the pattern given is too large
    relative to the target. The threshold of a pattern's size is
    hard-coded to be 2/3rds the size of the target's size.
    """

    def __init__(self, target, pattern, write_file_suffix=None):
        """Takes two 2D-images, NumPy arrays loaded from files by
        OpenCV. Constructing this object computes the convolution and
        square-difference distance map. The "write_file_suffix" should
        be a string (without a dot) indicating the file type to
        create. The OpenCV backend for this program uses this suffix
        to decide how to encode the file, so for example "bmp" will
        construct a MS-Windows "Bitmap" encoded image file, "png" will
        construct a PNG encoded image file."""
        #----------------------------------------
        # Type checking
        if not isinstance(target, CachedCVImageLoader):
            raise ValueError(f'DistanceMap() argument "target" wrong type: {type(target)}')
        else:
            pass
        if not isinstance(pattern, CachedCVImageLoader):
            raise ValueError(f'DistanceMap() argument "reference" wrong type: {type(reference)}')
        else:
            pass
        #----------------------------------------
        self.target = target
        self.reference = pattern
        reference_image = pattern.get_image()
        pat_shape = reference_image.shape
        self.reference_height = pat_shape[0]
        self.reference_width  = pat_shape[1]
        print(
            f"reference_width = {self.reference_width},"
            f" reference_height = {self.reference_height},",
          )

        target_image = target.get_image()
        targ_shape = target_image.shape
        self.target_height = targ_shape[0]
        self.target_width  = targ_shape[1]
        print( \
            f"target_width = {self.target_width},"
            f" target_height = {self.target_height},",
          )

        # The target image might have also a cropping rectangle set to
        # limit the bounds of the reference matching. Apply this
        # cropping to the image buffer now.
        crop = target.get_crop_rect()
        if crop is not None:
            region = RegionSize(*crop)
            target_image = region.crop_image(target_image)
        else:
            pass

        # Here we check that the reference image size is not larger
        # than the target image size.

        if float(self.reference_width) > self.target_width or \
          float(self.reference_height) > self.target_height:
            raise ValueError(
                "reference image is too large relative to target image",
                {"reference_width": self.reference_width,
                 "reference_height": self.reference_height,
                 "target_width": self.target_width,
                 "target_height": self.target_height,
                },
              )
        else:
            pass

        # When searching the convolution result for local minima, we could
        # use a window size the same as the reference size, but a slightly
        # finer window size tends to have better results. If possible, halve
        # each dimension of reference size to define the window size.

        self.window_height = math.ceil(self.reference_height / 2) \
            if self.reference_height >= 4 else self.reference_height
        self.window_width  = math.ceil(self.reference_width  / 2) \
            if self.reference_width  >= 4 else self.reference_width

        print(f"window_height = {self.window_height}, window_width = {self.window_width}")

        ### Available methods for reference matching in OpenCV
        #
        # cv.TM_CCOEFF  cv.TM_CCOEFF_NORMED
        # cv.TM_CCORR   cv.TM_CCORR_NORMED
        # cv.TM_SQDIFF  cv.TM_SQDIFF_NORMED

        # Apply template Matching
        pre_distance_map = cv.matchTemplate(target_image, reference_image, cv.TM_SQDIFF_NORMED)
        pre_dist_map_height, pre_dist_map_width = pre_distance_map.shape
        print(f"pre_dist_map_height = {pre_dist_map_height}, pre_dist_map_width = {pre_dist_map_width}")

        # Normalize result
        np.linalg.norm(pre_distance_map)

        # The "search_image" is a white image that is the smallest
        # even multiple of the window size that is larger than the
        # distance_map.
        self.distance_map = np.ones( \
            ( pre_dist_map_height - (pre_dist_map_height % -self.window_height), \
              pre_dist_map_width  - (pre_dist_map_width  % -self.window_width ) \
            ), \
            dtype=np.float32,
          )
        print(f"dist_map_height = {pre_dist_map_height}, dist_map_width = {pre_dist_map_width}")

        # Copy the result into the "search_image".
        self.distance_map[0:pre_dist_map_height, 0:pre_dist_map_width] = pre_distance_map

        # The 'find_matching_points()' method will memoize it's results.
        self.memoized_regions = {}

    def same_inputs(self, reference, target):
        return \
            str(self.reference.get_path()) == str(reference.get_path()) and \
            str(self.target.get_path()) == str(target.get_path())

    def get_target(self):
        return self.target

    def get_reference(self):
        return self.reference

    def save_distance_map(self, file_path):
        """Write the distance map that was computed at the time this object
        was constructed to a grayscale PNG image file.
        """
        cv.imwrite(os.fspath(file_path), util.float_to_uint32(self.distance_map))

    def find_matching_points(self, threshold=0.95):
        """Given a 'distance_map' that has been computed by the
        'compute_distance_map()' function above, and a threshold
        value, return an iterator that produces all regions where the
        distance map is less or equal to the complement of the
        threshold value. """
        if threshold < 0.5:
            raise ValueError(
                "threshold {str(threshold)} too low, minimum is 0.5",
                {"threshold": threshold},
              )
        elif threshold in self.memoized_regions:
            print(f'DistanceMap.find_matching_points(threshold={threshold}) #(threshold memoized, returning list of {len(self.memoized_regions[threshold])} items)')
            return self.memoized_regions[threshold]
        else:
            pass

        # We use reshape to cut the search_image up into pieces exactly
        # equal in size to the reference image.
        dist_map_height, dist_map_width = self.distance_map.shape
        window_vcount = round(dist_map_height / self.window_height)
        window_hcount = round(dist_map_width  / self.window_width)

        tiles = self.distance_map.reshape(
            window_vcount, self.window_height,
            window_hcount, self.window_width
          )

        print(f'DistanceMap.find_matching_points(threshold={threshold}) #(searching image)')
        results = []  # used to memoize these results
        for y in range(window_vcount):
            for x in range(window_hcount):
                tile = tiles[y, :, x, :]
                (min_y, min_x) = np.unravel_index(
                    np.argmin(tile),
                    (self.window_height, self.window_width),
                  )
                global_y = y * self.window_height + min_y
                global_x = x * self.window_width  + min_x
                similarity = 1.0 - tile[min_y, min_x]
                if similarity >= threshold:
                    result = (global_x, global_y, similarity,)
                    results.append(result)
                    # RegionSize(
                    #     global_x, global_y,
                    #     self.reference_width, self.reference_height,
                    #   )
                else:
                    pass

        self.memoized_regions[threshold] = results
        print(f'DistanceMap.find_matching_points(threshold={threshold}) #(memoized list of {len(results)} results)')
        return results

#---------------------------------------------------------------------------------------------------

class RMEMatcher():
    """Contains the state specific to the Root-Mean Error matching
    algorithm used. An instance of this class takes a reference to the
    SingleFeatureMultiCrop object that retains the shared state for
    the user interface (both GUI and CLI) of this application. This
    function also contains methods for actually executing a pattern
    match operation and caching the results -- in this case the cache
    is the DistanceMap generated. """

    def __init__(self, config):
        self.config = config
        self.distance_map = None
        self.threshold = config.get_threshold()
        self.target_matched_points = None

    def match_on_file(self):
        #target_image_path = self.target.get_path()
        print(f'{self.__class__.__name__}.match_on_file()')
        reference = self.config.get_reference()
        target    = self.config.get_target()
        suffix    = self.config.get_file_encoding()
        threshold = self.config.get_threshold()
        reference.assert_parameter('Pattern image')
        target.assert_parameter('Input image')
        if self.distance_map and self.distance_map.same_inputs(reference, target):
            pass
        else:
            self.distance_map = DistanceMap(target, reference, suffix)
            self.target_matched_points = \
                self.distance_map.find_matching_points(threshold)
        return self.target_matched_points

    def change_threshold(self, threshold):
        print(f'{self.__class__.__name__}.change_threshold({threshold})')
        if self.distance_map:
             if self.threshold != threshold:
                 self.target_matched_points = \
                     self.distance_map.find_matching_points(threshold)
                 self.threshold = threshold
             else:
                 print(f'RMEMatcher.change_threshold({threshold}) #(thrshold is already set to this value)')
        else:
            print(f'RMEMatcher.change_threshold() #(called before DistanceMap was constructed)')

    def get_matched_points(self):
        """This function returns the list of patterm matching regions that
        were most recently computed by running the
        self.distance_map.find_matching_region() function."""
        print(f'{self.__class__.__name__}.get_matched_points() #-> {self.target_matched_points}')
        return self.target_matched_points

    def save_calculations(self):
        """This function is called to save the intermediate steps used to
        comptue the pattern matching operation. In the case of the RME
        matching algorithm, the distance map is saved to a file. """
        interm_calc_path = PurePath(target_image_path)
        interm_calc_path = PurePath(
            interm_calc_path.parent / \
            ( interm_calc_path.stem + \
              '_diffmap' + \
              interm_calc_path.suffix \
            )
          )
        self.distance_map.save_distance_map(interm_calc_path)
