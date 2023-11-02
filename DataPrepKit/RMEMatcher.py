import DataPrepKit.FileSet as fs
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader
from DataPrepKit.RegionSize import RegionSize
from DataPrepKit.SingleFeatureMultiCrop import SingleFeatureMultiCrop, check_algorithm_name
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

class RMEMatcher(SingleFeatureMultiCrop):
    """The main app model contains the buffer for the reference image, and the memoized search
    results for every image that has been compared against the reference image for a particular
    threshold value."""

    def __init__(self, config=None):
        super().__init__(config)
        self.distance_map = None
        self.threshold = 0.92

    def get_feature_region(self):
        """Overloads the "SingleFeatureMultiCrop.get_feature_region"
        method. The "SingleFeatureMultiCrop" member variable
        "feature_region" is still used in case the "self.reference"
        has not been set yet. But if there is a "self.reference"
        image, the reference image's crop region is used as the
        feature region."""
        if self.reference is None:
            SingleFeatureMultiCrop.get_feature_region(self)
        else:
            return self.reference.get_crop_rect()

    def set_feature_region(self, rect):
        """Overloads the "SingleFeatureMultiCrop.set_feature_region"
        method. The "SingleFeatureMultiCrop" member variable
        "feature_region" is still used in case the "self.reference"
        has not been set yet. But if there is a "self.reference"
        image, the reference image's crop region is used as the
        feature region. """
        if rect is None:
            self.reference.set_crop_rect(None)
        elif isinstance(rect, tuple) and (len(rect) == 4):
            if self.reference is not None:
                self.reference.set_crop_rect(rect)
            else:
                pass
        else:
            raise ValueError(f'RMEMatcher.set_feature_region() must take a 4-tuple', rect)
        SingleFeatureMultiCrop.set_feature_region(self, rect)

    def get_distance_map(self):
        return self.distance_map

    def match_on_file(self):
        """This function is triggered when you double-click on an item in the image
        list in the "FilesTab". It starts running the pattern matching algorithm
        and changes the display of the GUI over to the "InspectTab".
        """
        patimg = self.reference.get_image()
        targimg = self.target.get_image()
        if patimg is None:
            print(f'RMEMatcher.match_on_file() #(self.reference.get_image() returned None)')
        elif targimg is None:
            print(f'RMEMatcher.match_on_file() #(self.target.get_image() returned None)')
        else:
            target_image_path = self.target.get_path()
            self.distance_map = DistanceMap(self.target, self.reference)
            self.target_matched_points = \
                self.distance_map.find_matching_points(self.threshold)

    def change_threshold(self, threshold):
        if self.distance_map is not None:
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
        return self.target_matched_points

    def crop_matched_references(self, target_image_path):
        # Create results directory if it does not exist
        print(f'{self.__class__.__name__}.crop_matched_references({target_image_path!r}) #(after clean-up self.crop_regions)')
        if not os.path.isdir(self.results_dir):
            os.mkdir(self.results_dir)
        else:
            pass
        target = CachedCVImageLoader()
        target.load_image(path=target_image_path)
        self.reference.load_image(
            path=self.reference_image_path,
            crop_rect=self.feature_region,
          )
        distance_map = DistanceMap(target, self.reference)
        if self.save_distance_map is not None:
            # Save the convolution image:
            distance_map.save_distance_map(self.save_distance_map)
        else:
            pass
        self.crop_regions = util.dict_keep_defined(self.crop_regions)
        self.print_state()
        self.write_all_cropped_images(
            distance_map,
            self.threshold,
            self.results_dir,
          )

    def write_all_cropped_images(self, distance_map, threshold, results_dir):
        target_image = distance_map.get_target()
        target_image_path = target_image.get_path()
        prefix = target_image_path.stem
        print(f'{self.__class__.__name__}.write_all_cropped_images(target={target_image_path!r}, threshold={threshold!s}, results_dir={results_dir!r})')
        point_list = distance_map.find_matching_points(threshold=threshold)
        print(f'{self.__class__.__name__}.write_all_cropped_images()')
        print('  point_list')
        for (i, pt) in zip(range(0,len(point_list)), point_list):
            print(f'    {i}: {pt}')
        # -----------------------------------------------------------------------
        for (label,(x,y,width,height)) in self.iterate_crop_regions(point_list):
            # Here we make use of the "iterate_crop_regions()" method
            # inherited from the "SingleFeatureMultiCrop" class.
            out_dir = results_dir / PurePath(label) if label is not None else results_dir
            reg = RegionSize(x, y, width, height)
            try:
                reg.crop_write_image(
                    target_image.get_raw_image(),
                    out_dir,
                    file_prefix=prefix,
                    file_suffix=self.file_encoding,
                  )
            except Exception as e:
                print(f'ERROR: {target_image_path!r} {e}')

    def batch_crop_matched_patterns(self):
        self.reference.load_image(crop_rect=self.feature_region)
        print(f'{self.__class__.__name__}.batch_crop_matched_references() #(will operate on {len(self.target_fileset)} image files)')
        for image in self.target_fileset:
            #print(
            #    f'image = {image!s}\n'
            #    f'results_dir = {self.results_dir}\n'
            #    f'threshold = {self.threshold}\n'
            #    f'save_distance_map = {self.save_distance_map}',
            #  )
            self.crop_matched_references(image)
