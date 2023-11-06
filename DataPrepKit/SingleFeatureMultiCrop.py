import DataPrepKit.FileSet as fs
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader
import sys

def check_algorithm_name(name):
    if isinstance(name, str):
        name = name.upper()
        if name == 'RME':
            return 'RME'
        elif name == 'ORB':
            return 'ORB'
        else:
            raise ValueError(f'unepxected algorithm "{algorithm}", must be one of "ORB" or "RME"')
    else:
        raise ValueError(f'check_algorithm_name() expects a string', name)

#---------------------------------------------------------------------------------------------------

class SingleFeatureMultiCrop():
    """This object is used to configure all of the parameters for the
    pattern matching computation. You can configure the computation by
    reading command line arguments, by reading JSON files, or by
    reading the state of the GUI. The GUI itself is a visualization of
    the configuration (the set of all parameters) for the pattern
    matching algorithm.
    """

    def __init__(self, algorithm, config=None):
        self.feature_region = None
        self.crop_regions = {}
        self.crop_region_selection = None
        self.file_encoding = 'png'
        self.results_dir = None
        self.set_target_fileset(None)
        self.results_dir = None
        self.save_distance_map = None
        self.target = CachedCVImageLoader()
        self.target_matched_points = []
        self.reference = CachedCVImageLoader()
        if config:
            self.set_config(config)
        else:
            self.config = None
        self.algorithm = algorithm
 
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
            self.feature_region = self.reference.get_crop_rect()
        else:
            pass
        if config.crop_regions_json:
            self.crop_regions = config.crop_regions_json
        else:
            pass
        self.algorithm = check_algorithm_name(self.config.algorithm)

    def set_results_dir(self, results_dir):
        self.results_dir = results_dir

    def get_file_encoding(self):
        return self.file_encoding

    def set_file_encoding(self, encoding):
        encoding = encoding.lower()
        if encoding not in fs.image_file_suffix_set:
            raise ValueError(f'unknown image file encoding symbol "{self.file_encoding}"')
        else:
            self.file_encoding = encoding

    def get_target(self):
        return self.target

    def get_target_image_path(self):
        return self.target.get_path()

    def set_target_image_path(self, path):
        #print(f'RMEMatcher.set_target_image_path("{path}")')
        self.target.load_image(path=path)

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
        #print(f'RMEMatcher.add_target_fileset("{path_list}")')
        self.target_fileset.merge_recursive(path_list)

    def remove_image_path(self, path):
        self.target_fileset.delete(path)

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
            self.reference.load_image(path=path, crop_rect=self.feature_region)
        else:
            pass
        self.set_feature_region(self.reference.get_crop_rect())

    def set_reference_pixmap(self, reference_path, pixmap):
        self.reference.set_image(reference_path, pixmap)

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

    ############  Calling into altogirhms  ############

    def match_on_file(self):
        self.algorithm.match_on_file()

    def get_matched_points(self):
        return self.algorithm.get_matched_points()

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

