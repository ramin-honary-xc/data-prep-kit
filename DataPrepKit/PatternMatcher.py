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

    def __init__(self, target, pattern, write_file_suffix=None):
        """Takes two 2D-images, NumPy arrays loaded from files by
        OpenCV. Constructing this object computes the convolution and
        square-difference distance map. The "write_file_suffix" should
        be a string (without a dot) indicating the file type to
        create. The OpenCV backend for this program uses this suffix
        to decide how to encode the file, so for example "bmp" will
        construct a MS-Windows "Bitmap" encoded image file, "png" will
        construct a PNG encoded image file."""
        self.target = target
        self.reference = pattern
        print(f'reference = {self.reference.get_path()!s}')
        self.target_image_path = target.get_path()
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

        # Here we check that the reference image size is not too large
        # relative to the target image size. The reference image size
        # threshold is hard-coded here (for now) as 2/3rds the size of
        # the target image size.

        if float(self.reference_width)  > self.target_width  / 2 * 3 or \
           float(self.reference_height) > self.target_height / 2 * 3 :
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
        cv.imwrite(str(file_path), util.float_to_uint32(self.distance_map))

    def find_matching_points(self, threshold=0.95):
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
        # equal in size to the reference image.
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
                    results.append((global_x, global_y,))
                    # RegionSize(
                    #     global_x, global_y,
                    #     self.reference_width, self.reference_height,
                    #   )
                else:
                    pass

        self.memoized_regions[threshold] = results
        return results

    def write_all_cropped_images(self, target_image, threshold, crop_regions, results_dir):
        print(
            f'threshold = {threshold!s}\n'
            f'target_image = {self.target_image_path!s}',
          )
        points = self.find_matching_points(threshold=threshold)
        prefix = self.target_image_path.stem
        if crop_regions is None or len(crop_regions) == 0:
            print(f'DistanceMap.write_all_cropped_images() #(no crop_regions, len(points) = {len(points)})')
            for (x,y) in points:
                reg = RegionSize(x, y, self.reference_width, self.reference_height)
                reg.crop_write_image(target_image, results_dir, prefix)
        else:
            print(f'DistanceMap.write_all_cropped_images() #(len(points) = {len(points)}, len(crop_regions) = {len(crop_regions)})')
            for (x,y) in points:
                for (label,(x_off, y_off, width, height)) in crop_regions.items():
                    reg = RegionSize(x+x_off, y+y_off, width, height)
                    reg.crop_write_image(target_image, results_dir/PurePath(label), prefix)

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
        self.target_matched_points = []
        self.file_encoding = 'png'
        self.crop_regions = {}
        self.reference = CachedCVImageLoader()
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
        self.set_file_encoding(config.encoding)
        # Load the reference right away, if it is not None
        self.reference_image_path = config.pattern
        if self.reference_image_path:
            self.reference.load_image(self.reference_image_path)
        else:
            pass

    def get_file_encoding(self):
        return self.file_encoding

    def set_file_encoding(self, encoding):
        encoding = encoding.lower()
        if encoding not in fs.image_file_suffix_set:
            raise ValueError(f'unknown image file encoding symbol "{self.file_encoding}"')
        else:
            self.file_encoding = encoding

    def get_reference(self):
        return self.reference

    def get_reference_image_path(self):
        return self.reference.get_path()

    def set_reference_image_path(self, path):
        self.reference_image_path = path
        if path:
            self.reference.load_image(path)
        else:
            pass

    def set_reference_pixmap(self, reference_path, pixmap):
        self.reference.set_image(reference_path, pixmap)

    def get_reference_rect(self):
        if self.reference is None:
            return None
        else:
            return self.reference.get_crop_rect()

    def set_reference_rect(self, rect):
        if rect is None:
            self.reference.set_crop_rect(None)
        elif isinstance(rect, tuple) and (len(rect) == 4):
            if self.reference is not None:
                self.reference.set_crop_rect(rect)
        else:
            raise ValueError(f'PatternMatcher.set_reference_rect() must take a 4-tuple', rect)

    def get_crop_regions(self):
        return self.crop_regions

    def set_crop_regions(self, crop_regions):
        self.crop_regions = crop_regions

    def set_results_dir(self, results_dir):
        self.results_dir = results_dir

    def add_crop_region(sefl, label, rect):
        self.crop_regions[label] = rect

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
        list in the "FilesTab". It starts running the pattern matching algorithm
        and changes the display of the GUI over to the "InspectTab".
        """
        patimg = self.reference.get_image()
        targimg = self.target.get_image()
        if patimg is None:
            print(f'PatternMatcher.match_on_file() #(self.reference.get_image() returned None)')
        elif targimg is None:
            print(f'PatternMatcher.match_on_file() #(self.target.get_image() returned None)')
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
                 print(f'PatternMatcher.change_threshold({threshold}) #(thrshold is already set to this value)')
        else:
            print(f'PatternMatcher.change_threshold() #(called before DistanceMap was constructed)')

    def get_matched_points(self):
        """This function returns the list of patterm matching regions that
        were most recently computed by running the
        self.distance_map.find_matching_region() function."""
        return self.target_matched_points

    def crop_matched_references(self, target_image_path):
        # Create results directory if it does not exist
        if not os.path.isdir(self.results_dir):
            os.mkdir(self.results_dir)
        else:
            pass
        target = CachedCVImageLoader()
        target.load_image(target_image_path)
        self.reference.load_image(self.reference_image_path)
        distance_map = DistanceMap(target, self.reference)
        if self.save_distance_map is not None:
            # Save the convolution image:
            distance_map.save_distance_map(self.save_distance_map)
        else:
            pass
        distance_map.write_all_cropped_images(
            target.get_image(),
            self.threshold,
            self.crop_regions,
            self.results_dir,
          )

    def batch_crop_matched_references(self):
        self.reference.load_image()
        for image in self.target_fileset:
            #print(
            #    f'image = {image!s}\n'
            #    f'results_dir = {self.results_dir}\n'
            #    f'threshold = {self.threshold}\n'
            #    f'save_distance_map = {self.save_distance_map}',
            #  )
            self.crop_matched_references(image)

    def load_image(self, path):
        self.reference.set_reference_image_path(path)
        self.reference.load_image()
