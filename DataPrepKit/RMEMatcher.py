import DataPrepKit.FileSet as fs
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader
from DataPrepKit.RegionSize import RegionSize
from DataPrepKit.AbstractMatcher import AbstractMatcher, AbstractMatchCandidate
import DataPrepKit.utilities as util

import math
import os
import os.path
import sys
from pathlib import PurePath
#import traceback

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
        #print(
        #    f"reference_width = {self.reference_width},"
        #    f" reference_height = {self.reference_height},",
        #  )

        target_image = target.get_image()
        targ_shape = target_image.shape
        self.target_height = targ_shape[0]
        self.target_width  = targ_shape[1]
        #print( \
        #    f"target_width = {self.target_width},"
        #    f" target_height = {self.target_height},",
        #  )

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

        #print(f"window_height = {self.window_height}, window_width = {self.window_width}")

        ### Available methods for reference matching in OpenCV
        #
        # cv.TM_CCOEFF  cv.TM_CCOEFF_NORMED
        # cv.TM_CCORR   cv.TM_CCORR_NORMED
        # cv.TM_SQDIFF  cv.TM_SQDIFF_NORMED

        # Apply template Matching
        pre_distance_map = cv.matchTemplate(target_image, reference_image, cv.TM_SQDIFF_NORMED)
        pre_dist_map_height, pre_dist_map_width = pre_distance_map.shape
        #print(f"pre_dist_map_height = {pre_dist_map_height}, pre_dist_map_width = {pre_dist_map_width}")

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
        #print(f"dist_map_height = {pre_dist_map_height}, dist_map_width = {pre_dist_map_width}")

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
            #print(f'{self.__class__.__name__}.find_matching_points(threshold={threshold}) #(threshold memoized, returning list of {len(self.memoized_regions[threshold])} items)')
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

        #print(f'{self.__class__.__name__}.find_matching_points(threshold={threshold}) #(searching image)')
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
                    results.append(
                        RMECandidate(
                            ( global_x, global_y,
                              self.reference_width, self.reference_height,
                            ),
                            similarity,
                            self.target
                          ),
                      )
                    # RegionSize(
                    #     global_x, global_y,
                    #     self.reference_width, self.reference_height,
                    #   )
                else:
                    pass

        self.memoized_regions[threshold] = results
        #print(f'{self.__class__.__name__}.find_matching_points(threshold={threshold}) #(memoized list of {len(results)} results)')
        return results

#---------------------------------------------------------------------------------------------------

class RMECandidate(AbstractMatchCandidate):
    """Object instances of this class contain references to candidate
    matching points in the target image."""

    def __init__(self, rect, match_score, image):
        super().__init__()
        self.rect = rect
        self.match_score = match_score
        self.image = image
        (x, y, width, height) = rect
        self.x_min = round(min(x, x + width))
        self.y_min = round(min(y, y + height))
        self.x_max = round(max(x, x + width))
        self.y_max = round(max(y, y + height))

    def get_rect(self):
        return self.rect

    def get_match_score(self):
        return self.match_score

    def get_string_id(self):
        """See documentation for AbstractMatchCadndidate.get_string_id()"""
        (x, y, _width, _height) = self.rect
        return f'{x:05}x{x:05}'

    def check_crop_region_size(self, relative_rect=None):
        """Return ((x_min, x_max), (y_min, y_max)) for a bounding
        rectangle if this RegionSize fits within the bounds of the
        given image, otherwise returns None."""
        print(f'{self.__class__.__name__}.check_crop_region({relative_rect}) #(self.rect={self.rect})')
        (x_min, y_min, width, height) = self.rect
        if relative_rect is not None:
            (x, y, width, height) = relative_rect
            x_min += x
            y_min += y
        else:
            pass
        x_max = round(x_min + width)
        y_max = round(y_min + height)
        image = self.image.get_image()
        shape = image.shape
        image_height = shape[0]
        image_width = shape[1]
        result = ((x_min, x_max), (y_min, y_max))
        if(x_min < 0) or (x_min > image_width)  or \
          (y_min < 0) or (y_min > image_height) or \
          (x_max < 0) or (x_max > image_width)  or \
          (y_max < 0) or (y_max > image_height):
            return (False, result)
        else:
            return (True, result)

    def crop_image(self, relative_rect=None):
        """Return a copy of the given image cropped to this object's
        rectangle. """
        image = self.image.get_image()
        (ok, ((x_min, x_max), (y_min, y_max))) = self.check_crop_region_size(relative_rect)
        if ok:
            print(f'{self.__class__.__name__}.crop_image({relative_rect}) #(x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max})')
            return image[y_min:y_max, x_min:x_max]
        else:
            shape = image.shape
            image_height = shape[0]
            image_width  = shape[1]
            raise ValueError(
                "pattern crop not fully contained within pattern image",
                {"image_width": image_width,
                 "image_height": image_height,
                 "crop_X": x_min,
                 "crop_width": x_max - x_min,
                 "crop_Y": y_min,
                 "crop_height": y_max - y_min,
                 },
              )

    def crop_write_images(self, crop_rects, output_path):
        """See documentation for AbstractMatchCandidate.crop_write_image()."""
        #print(f'{self.__class__.__name__}.crop_write_images({crop_rects!r}), {str(output_path)!r})')
        (x0, y0, _width, _height) = self.rect
        for (label, rect) in crop_rects.items():
            (x,y,width,height) = rect
            x = round(x+x0)
            y = round(y+y0)
            image_ID = f'{x:05}x{y:05}'
            outpath = str(output_path).format(label=label, image_ID=image_ID)
            print(f'{self.__class__.__name__}.crop_write_images() #(save {outpath!r})')
            image = self.crop_image((x,y,width,height,))
            cv.imwrite(outpath, image)

#---------------------------------------------------------------------------------------------------

class RMEMatcher(AbstractMatcher):
    """Contains the state specific to the Root-Mean Error matching
    algorithm used. An instance of this class takes a reference to the
    SingleFeatureMultiCrop object that retains the shared state for
    the user interface (both GUI and CLI) of this application. This
    function also contains methods for actually executing a pattern
    match operation and caching the results -- in this case the cache
    is the DistanceMap generated. """

    def __init__(self, app_model):
        self.app_model = app_model
        self.distance_map = None
        self.target_matched_points = None

    def configure_to_json(self):
        threshold = self.app_model.get_threshold()
        return {'threshold': threshold}

    def configure_from_json(self, config):
        if isinstance(config, dict):
            for (key,value) in config.items():
                lkey = key.lower()
                if lkey == 'threshold':
                    if isinstance(value, int) or isinstance(value, float):
                        self.app_model.set_threshold(value)
                    else:
                        raise ValueError('RME algorithm config parameter "threshold" is not a number', value, config)
                else:
                    raise ValueError('RME algorithm config, unknown parameter', key, config)
        else:
            raise ValueError('RME algorithm config parameters is not a dictionary', config)

    def get_reference_image(self):
        return self.app_model.get_reference()

    def set_reference_image(self, reference):
        """Does not need to do anything, the reference is taken from self.app_model on demand."""
        pass

    def needs_refresh(self):
        """Conditions that would return True include when the match has not
        been run yet, when the target or reference images have
        changed, or when the threshold has changed. """
        # ------------------------------------------------------------
        # NOTE: the threshold is not actually considered because it is
        # cached separately in the 'DistanceMap' object, so we return
        # False (does not need refresh) regardless of whether the
        # threshold has changed or not, and allow the 'DistanceMap' to
        # check whether it has points cached for the current threshold value.
        return AbstractMatcher(self, needs_refresh)

    def guess_compute_steps(self):
        return 1

    def update_reference_image(self, reference=None):
        """Nothing needs to be computed on the referene image."""
        pass

    def match_on_file(self, progress=None):
        """See documentation for DataPrepKit.AbstractMatcher.match_on_file()."""
        #traceback.print_stack()
        #print(f'{self.__class__.__name__}.match_on_file()')
        reference = self.app_model.get_reference_image()
        reference.load_image()
        target    = self.app_model.get_target_image()
        target.load_image()
        suffix    = self.app_model.get_file_encoding()
        threshold = self.app_model.get_threshold()
        reference.assert_parameter('Pattern image')
        target.assert_parameter('Input image')
        self._update_inputs(target, reference)
        self.distance_map = DistanceMap(target, reference, suffix)
        if progress is not None:
            progress.update_progress(1)
        else:
            pass
        return AbstractMatcher._update_matched_points(
            self, 
            self.distance_map.find_matching_points(threshold),
          )

    def get_matched_points(self):
        """See documentation for DataPrepKit.AbstractMatcher.get_matched_points()."""
        return AbstractMatcher.get_matched_points(self)

    def set_threshold(self, _threshold):
        return self.match_on_file()

    def save_calculations(self):
        """See documentation for DataPrepKit.AbstractMatcher.save_calculations."""
        interm_calc_path = PurePath(target_image_path)
        interm_calc_path = PurePath(
            interm_calc_path.parent / \
            ( interm_calc_path.stem + \
              '_diffmap' + \
              interm_calc_path.suffix \
            )
          )
        self.distance_map.save_distance_map(interm_calc_path)
