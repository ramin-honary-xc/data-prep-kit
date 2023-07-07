import DataPrepKit.FileSet as fs
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader
from DataPrepKit.RegionSize import RegionSize

import math
import os
import os.path
from pathlib import PurePath

import cv2 as cv
import numpy as np

####################################################################################################
# The pattern matcing program

def gather_QUrl_local_files(qurl_list):
    """This function converts a list of URL values of type QUrl into a
    list of PurePaths. It is useful for constructing 'FileListItem's
    from the result of a file dialog selection.
    """
    urls = []
    for url in qurl_list:
        if url.isLocalFile():
            urls.append(PurePath(url.toLocalFile()))
    return urls

#---------------------------------------------------------------------------------------------------

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

    def __init__(self, target, pattern):
        """Takes two 2D-images, NumPy arrays loaded from files by
        OpenCV. Constructing this object computes the convolution and
        square-difference distance map.
        """
        self.target = target
        self.pattern = pattern
        print(f'pattern = {self.pattern.get_path()!s}')
        self.target_image_path = target.get_path()
        pattern_image = pattern.get_image()
        pat_shape = pattern_image.shape
        self.pattern_height = pat_shape[0]
        self.pattern_width  = pat_shape[1]
        print(
            f"pattern_width = {self.pattern_width},"
            f" pattern_height = {self.pattern_height},",
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
        # limit the bounds of the pattern matching. Apply this
        # cropping to the image buffer now.
        crop = target.get_crop_rect()
        if crop is not None:
            region = RegionSize(*crop)
            target_image = region.crop_image(target_image)
        else:
            pass

        # Here we check that the pattern image size is not too large
        # relative to the target image size. The pattern image size
        # threshold is hard-coded here (for now) as 2/3rds the size of
        # the target image size.

        if float(self.pattern_width)  > self.target_width  / 2 * 3 or \
           float(self.pattern_height) > self.target_height / 2 * 3 :
            raise ValueError(
                "pattern image is too large relative to target image",
                {"pattern_width": self.pattern_width,
                 "pattern_height": self.pattern_height,
                 "target_width": self.target_width,
                 "target_height": self.target_height,
                },
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

        print(f"window_height = {self.window_height}, window_width = {self.window_width}")

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
              pre_dist_map_width  - (pre_dist_map_width  % -self.window_width ) \
            ), \
            dtype=np.float32,
          )
        print(f"dist_map_height = {pre_dist_map_height}, dist_map_width = {pre_dist_map_width}")

        # Copy the result into the "search_image".
        self.distance_map[0:pre_dist_map_height, 0:pre_dist_map_width] = pre_distance_map

        # The 'find_matching_regions()' method will memoize it's results.
        self.memoized_regions = {}

    def get_target(self):
        return self.target

    def get_pattern(self):
        return self.pattern

    def save_distance_map(self, file_path):
        """Write the distance map that was computed at the time this object
        was constructed to a grayscale PNG image file.
        """
        cv.imwrite(str(file_path), util.float_to_uint32(self.distance_map))

    def find_matching_regions(self, threshold=0.95):
        """Given a 'distance_map' that has been computed by the
        'compute_distance_map()' function above, and a threshold
        value, return a list of all regions where the distance map is
        less or equal to the complement of the threshold value.
        """
        if threshold < 0.5:
            raise ValueError(
                "threshold {str(threshold)} too low, minimum is 0.5",
                {"threshold": threshold},
              )
        elif threshold in self.memoized_regions:
            return self.memoized_regions[threshold]
        else:
            pass

        # We use reshape to cut the search_image up into pieces exactly
        # equal in size to the pattern image.
        dist_map_height, dist_map_width = self.distance_map.shape
        window_vcount = round(dist_map_height / self.window_height)
        window_hcount = round(dist_map_width  / self.window_width)

        tiles = self.distance_map.reshape(
            window_vcount, self.window_height,
            window_hcount, self.window_width
          )

        results = []
        for y in range(window_vcount):
            for x in range(window_hcount):
                tile = tiles[y, :, x, :]
                (min_y, min_x) = np.unravel_index(
                    np.argmin(tile),
                    (self.window_height, self.window_width),
                  )
                global_y = y * self.window_height + min_y
                global_x = x * self.window_width  + min_x
                if tile[min_y, min_x] <= (1.0 - threshold):
                    results.append(
                        RegionSize(
                            global_x, global_y,
                            self.pattern_width, self.pattern_height,
                          )
                      )
                else:
                    pass

        self.memoized_regions[threshold] = results
        return results

    def write_all_cropped_images(self, target_image, threshold, results_dir):
        print(
            f'threshold = {threshold!s}\n'
            f'target_image = {self.target_image_path!s}',
          )
        regions = self.find_matching_regions(threshold=threshold)
        prefix = self.target_image_path.stem
        for reg in regions:
            reg.crop_write_image(target_image, results_dir, prefix)

#---------------------------------------------------------------------------------------------------

class PatternMatcher():
    """The main app model contains the buffer for the reference image, and the memoized search
    results for every image that has been compared against the reference image for a particular
    threshold value."""

    def __init__(self, config=None):
        self.distance_map = None
        self.config = None
        self.results_dir = None
        self.set_target_fileset(None)
        self.results_dir = None
        self.save_distance_map = None
        self.threshold = 0.78
        self.target = CachedCVImageLoader()
        self.target_matched_regions = []
        self.pattern = CachedCVImageLoader()
        if config:
            self.set_config(config)
        else:
            pass

    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config
        self.set_target_fileset(config.inputs)
        self.set_reference_image_path(config.pattern)
        self.results_dir = config.output_dir
        self.threshold = config.threshold
        self.save_distance_map = config.save_map
        # Load the pattern right away, if it is not None
        self.pattern_image_path = config.pattern
        if self.pattern_image_path:
            self.pattern.load_image(self.pattern_image_path)
        else:
            pass

    def get_pattern(self):
        return self.pattern

    def get_reference_image_path(self):
        return self.pattern.get_path()

    def set_reference_image_path(self, path):
        self.pattern_image_path = path
        if path:
            self.pattern.load_image(path)
        else:
            pass

    def set_pattern_pixmap(self, pattern_path, pixmap):
        self.pattern.set_image(pattern_path, pixmap)

    def get_pattern_rect(self):
        return self.pattern_rect

    def set_pattern_rect(self, rect):
        if rect is None:
            self.pattern.set_crop_rect(None)
        elif isinstance(rect, tuple) and (len(rect) == 4):
            if self.pattern is not None:
                self.pattern.set_crop_rect(rect)
        else:
            raise ValueError(f'PatternMatcher.set_pattern_rect() must take a 4-tuple', rect)

    def get_target(self):
        return self.target

    def get_target_image_path(self):
        return self.target.get_path()

    def set_target_image_path(self, path):
        #print(f'PatternMatcher.set_target_image_path("{path}")')
        self.target.load_image(path)

    def get_target_fileset(self):
        return self.target_fileset

    def set_target_fileset(self, path_list):
        self.target_fileset = \
            fs.FileSet(filter=fs.filter_image_files_by_ext)
        if path_list:
            self.target_fileset.merge_recursive(path_list)
        else:
            pass

    def add_target_fileset(self, path_list):
        #print(f'PatternMatcher.add_target_fileset("{path_list}")')
        self.target_fileset.merge_recursive(path_list)

    def remove_image_path(self, path):
        self.target_fileset.delete(path)

    def get_distance_map(self):
        return self.distance_map

    def match_on_file(self):
        """This function is triggered when you double-click on an item in the image
        list in the "FilesTab". It starts running the pattern matching algorithm and
        changes the display of the GUI over to the "InspectTab".
        """
        patimg = self.pattern.get_image()
        targimg = self.target.get_image()
        if patimg is None:
            print(f'PatternMatcher.match_on_file() #(self.pattern.get_image() returned None)')
        elif targimg is None:
            print(f'PatternMatcher.match_on_file() #(self.target.get_image() returned None)')
        else:
            target_image_path = self.target.get_path()
            self.distance_map = DistanceMap(self.target, self.pattern)
            self.target_matched_regions = \
                self.distance_map.find_matching_regions(self.threshold)

    def change_threshold(self, threshold):
        if self.distance_map is not None:
             if self.threshold != threshold:
                 self.target_matched_regions = \
                     self.distance_map.find_matching_regions(threshold)
                 self.threshold = threshold
             else:
                 print(f'PatternMatcher.change_threshold({threshold}) #(thrshold is already set to this value)')
        else:
            print(f'PatternMatcher.change_threshold() #(called before DistanceMap was constructed)')

    def get_matched_regions(self):
        """This function returns the list of patterm matching regions that
        were most recently computed by running the
        self.distance_map.find_matching_region() function."""
        return self.target_matched_regions

    def crop_matched_patterns(self, target_image_path):
        # Create results directory if it does not exist
        if not os.path.isdir(self.results_dir):
            os.mkdir(self.results_dir)
        else:
            pass
        target = CachedCVImageLoader()
        target.load_image(target_image_path)
        self.pattern.load_image(self.pattern_image_path)
        distance_map = DistanceMap(target, self.pattern)
        if self.save_distance_map is not None:
            # Save the convolution image:
            distance_map.save_distance_map(self.save_distance_map)
        else:
            pass
        distance_map.write_all_cropped_images(target.get_image(), self.threshold, self.results_dir)

    def batch_crop_matched_patterns(self):
        self.pattern.load_image()
        for image in self.target_fileset:
            #print(
            #    f'image = {image!s}\n'
            #    f'results_dir = {self.results_dir}\n'
            #    f'threshold = {self.threshold}\n'
            #    f'save_distance_map = {self.save_distance_map}',
            #  )
            self.crop_matched_patterns(image)

    def load_image(self, path):
        self.pattern.set_reference_image_path(path)
        self.pattern.load_image()
