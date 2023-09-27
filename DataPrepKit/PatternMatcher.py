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
        cv.imwrite(str(file_path), util.float_to_uint32(self.distance_map))

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

class SingleFeatureMultiCrop():
    """A model used by the pattern matcher for selecting a single
    "feature" region and multiple "crop" regions. This is because the
    patter matcher can only perform a single convolution, and thus is
    only able to work with one feature selection image. But once
    features are discovered, any number of croppings can be cut from
    the image. This is unlike the ORB algorithm which can use any
    number of feature regions to determine a more precise subset of
    candidate feature points are used for finding the pattern.

    State variables of this class include:

    - "feature_region" -- the region used to find patterns in target
      images. If set to "None" the whole reference is used as the pattern

    - "crop_regions" -- a dictionary with names as keys and rectangles
      as values. The rectangles will be used to crop-out portions of
      target images relative to the "feature_region". The names (keys
      of the dictionaries) not only uniquely identify each crop
      region, they also are used to create directories in the
      filesystem to hold the image files created from cropping them
      out of the target image.

    - "crop_region_selection" -- one of the "crop_regions" keys can be
      selected as an item to be modified.

    Note that the type of the actual region rectangles are never
    checked, so you can store anything into objects of this class. But
    this alllows the parts of the view that inherit this class, and
    the actual 'PatternMatcher' model which inherits this class, to
    each use whatever rectangle data types are most convenient. The
    API to access these rectangles is consistent across both the model
    and the view. """

    def __init__(self):
        self.feature_region = None
        self.crop_regions = {}
        self.crop_region_selection = None

    def get_crop_regions(self):
        """Get the whole dictionary that maps key names to rectangle values."""
        return self.crop_regions

    def set_crop_regions(self, crop_regions):
        """Set a whole new dictionary for mapping key names to rectangle values."""
        self.crop_regions = crop_regions

    def get_region_selection(self):
        return self.crop_region_selection

    def set_region_selection(self, label):
        """Set the 'self.crop_region_selection' which is the label of the
        rectangle within 'self.crop_regions' that is to be updated by
        mouse events handled by this tool."""
        print(f'CropRectTool.set_region_selection({label!r})')
        self.crop_region_selection = label

    def get_feature_region(self):
        return self.feature_region

    def set_feature_region(self, rect):
        """Set the current crop_rect value, and redraw the rectangle in the
        view. The rectangle change callback is not called."""
        self.feature_region = rect

    def add_crop_region(self, label, rect):
        print(f'{self.__class__.__name__}.add_crop_region({label!r}, {rect!r})')
        if label in self.crop_regions:
            self.print_state() 
            return False
        else:
            self.crop_regions[label] = rect
            self.print_state() 
            return True

    def set_crop_region(self, region_name, rect):
        """Change the rectangle of the named crop region."""
        if region_name is None:
            print(f'{self.__class__.__name__}.set_crop_region({region_name!r}, {rect}) #(set self.feature_region)')
            self.print_state()
            self.feature_region = rect
        if region_name in self.crop_regions:
            if region_name in self.crop_regions:
                print(f'{self.__class__.__name__}.set_crop_region({region_name!r}, {rect}) #(set self.crop_region[{region_name!r}])')
                self.print_state()
                self.crop_regions[region_name] = rect
            else:
                print(f'{self.__class__.__name__}.set_crop_region({region_name!r}, {rect}) #(failed, {region_name!r} not defined)')
                self.print_state()
                return False

    def get_crop_region_selection(self):
        if self.crop_region_selection is None:
            return self.feature_region
        else:
            if (self.crop_regions is None) or \
              (self.crop_region_selection not in self.crop_regions):
                return None
            else:
                return self.crop_regions[self.crop_region_selection]

    def set_crop_region_selection(self, rect):
        if self.crop_region_selection is None:
            self.feature_region = rect
        else:
            self.crop_regions[self.crop_region_selection] = rect

    def delete_crop_region(self, region_name):
        print(f'{self.__class__.__name__}.delete_crop_region({region_name!r})')
        if region_name is None:
            self.feature_region = None
            self.print_state()
            return True
        elif region_name in self.crop_regions:
            del self.crop_regions[region_name]
            self.print_state()
            return True
        else:
            return False

    def rename_crop_region(self, old_name, new_name):
        """Change the name of an existing crop region without changing its rectangle."""
        if self.crop_regions is None:
            self.crop_regions = {}
        else:
            pass
        if new_name is None:
            self.delete_crop_region(old_name)
            print(f'{self.__class__.__name__}.rename_crop_region({old_name!r}, {new_name!r}) #(crop_regions = {self.crop_regions})')
            self.print_state()
            return True
        elif (new_name in self.crop_regions):
            print(f'{self.__class__.__name__}.rename_crop_region({old_name!r}, {new_name!r}) #({new_name!r}) already exists)')
            return False
        else:
            if old_name in self.crop_regions:
                rect = self.crop_regions[old_name]
            else:
                rect = None
            del self.crop_regions[old_name]
            self.crop_regions[new_name] = rect
            if self.crop_region_selection == old_name:
                self.crop_region_selection = new_name
            else:
                pass
            print(f'{self.__class__.__name__}.rename_crop_region({old_name!r}, {new_name!r}) #(crop_regions = {self.crop_regions})')
            self.print_state()
            return True

    ###############  Iterating over point sets  ###############

    def iterate_feature_regions(self, point_list):
        """This is a generator function that takes a point_list and produces
        a list of rectangular regions over which you can iterate. The
        "point_list" argument here is actually a 3-tuple of (x, y, similarity)
        which is expected to have been returned by the
        "DistanceMap.find_matching_points()" method.

        The objects yielded by this generator are all 4-tuples of the
        form: (x, y, width, height).

        NOTE that if self.get_feature_region() returns None, this
        generator produces no values. The feature region MUST be
        defined for this to work.
        """
        ref_rect = self.get_feature_region()
        if ref_rect is None:
            return None
        else:
            (_x0, _y0, width, height) = ref_rect
            for (x,y,_similarity) in point_list:
                yield (x, y, width, height)

    def iterate_crop_regions(self, point_list):
        """This is a generator function that takes a point_list and produces a
        list of rectangular regions over which you can iterate. The
        "point_list" argument here is actually a 3-tuple of the form:
        (x, y, similarity)
        which is expected to have been returned by the
        "DistanceMap.find_matching_points()" method.

        The objects yielded by this generator are all tuples of the
        form: (region_name, (x, y, width, height)).

        NOTE that if there are no crop regions, the feature region is
        used as the one and only crop region, and the objects yielded
        by this generator are all tuples of the form:
        (None, (x, y, width, height)).

        NOTE that if self.get_feature_region() returns None, this
        generator produces no values. The feature region MUST be
        defined for this to work.

        """
        ref_rect = self.get_feature_region()
        if ref_rect is None:
            print(f'{self.__class__.__name__}.iterate_crop_regions() #(no reference rectangle set)')
            return None
        else:
            (x0, y0, width, height) = ref_rect
            crop_rect_iter = self.get_crop_regions()
            if (crop_rect_iter is None) or (len(crop_rect_iter) == 0):
                print(f'{self.__class__.__name__}.iterate_crop_regions() #(no crop regions, using feature region as single crop region)')
                crop_rect_iter = iter([(None, ref_rect)])
            else:
                print(f'{self.__class__.__name__}.iterate_crop_regions() #(iterating over {len(crop_rect_iter)} crop regions)')
                crop_rect_iter = crop_rect_iter.items()
            #----------------------------------------
            for (x,y,_similarity) in point_list:
                x_off = x - x0
                y_off = y - y0
                for (label, (crop_x, crop_y, width, height)) in crop_rect_iter:
                    yield (label, (crop_x+x_off, crop_y+y_off, width, height,),)

    ###############  Debugging methods  ###############

    def rect_to_str(self, rect):
        return repr(rect)

    def print_state(self, out=sys.stdout):
        out.write(f'  self.feature_region: {self.rect_to_str(self.feature_region)}\n')
        out.write(f'crop_region_selection: {self.crop_region_selection!r}\n')
        out.write( '    self.crop_regions: {\n')
        for name, rect in self.crop_regions.items():
            out.write(f'        {name!r}: {self.rect_to_str(rect)}\n')
        out.write( '      }\n')


#---------------------------------------------------------------------------------------------------

class PatternMatcher(SingleFeatureMultiCrop):
    """The main app model contains the buffer for the reference image, and the memoized search
    results for every image that has been compared against the reference image for a particular
    threshold value."""

    def __init__(self, config=None):
        super().__init__()
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
        """This function sets the reference image path and also attempts to
        load the image from this path. Also the feature region is set
        to the value returned by
        "CachedCVImageLoader.get_crop_rect()", which is, when it is
        first loaded, always the rectangular region that circumscribes
        the full the image. """
        self.reference_image_path = path
        if path:
            self.reference.load_image(path)
        else:
            pass
        SingleFeatureMultiCrop.set_feature_region(self, self.reference.get_crop_rect())

    def set_reference_pixmap(self, reference_path, pixmap):
        self.reference.set_image(reference_path, pixmap)

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
            raise ValueError(f'PatternMatcher.set_feature_region() must take a 4-tuple', rect)
        SingleFeatureMultiCrop.set_feature_region(self, rect)

    def set_results_dir(self, results_dir):
        self.results_dir = results_dir

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
        print(f'{self.__class__.__name__}.crop_matched_references() #(before clean-up self.crop_regions)')
        self.print_state()
        self.crop_regions = util.dict_keep_defined(self.crop_regions)
        print(f'{self.__class__.__name__}.crop_matched_references() #(after clean-up self.crop_regions)')
        self.print_state()
        self.write_all_cropped_images(
            target.get_image(),
            distance_map,
            self.threshold,
            self.results_dir,
          )

    def write_all_cropped_images(self, target_image, distance_map, threshold, results_dir):
        print(
            f'threshold = {threshold!s}\n'
            f'target_image = {self.target_image_path!s}',
          )
        point_list = self.distance_map.find_matching_points(threshold=threshold)
        target_image_path = target_image.get_path()
        prefix = target_image_path.stem
        print(f'PatternMatcher.write_all_cropped_images()')
        for (label,(x_off, y_off, width, height)) in self.iterate_crop_regions(point_list):
            # Here we make use of the "iterate_crop_regions()" method
            # inherited from the "SingleFeatureMultiCrop" class.
            out_dir = result_dir / PurePath(label) if label is not None else results_dir
            reg = RegionSize(x+x_off, y+y_off, width, height)
            reg.crop_write_image(target_image, out_dir, prefix)

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
