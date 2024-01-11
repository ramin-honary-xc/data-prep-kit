import DataPrepKit.FileSet as fs
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader
from DataPrepKit.RMEMatcher import RMEMatcher
from DataPrepKit.ORBMatcher import ORBMatcher
from DataPrepKit.RegionSize import RegionSize
from pathlib import Path, PurePath
from DataPrepKit.utilities import bounding_rect
import sys
import traceback

def algorithm_name(name, get_constr=False):
    if isinstance(name, str):
        name = name.upper()
        if name == 'RME':
            return 'RME' if not get_constr else RMEMatcher.__init__
        elif name == 'ORB':
            return 'ORB' if not get_constr else ORBMatcher.__init__
        else:
            raise ValueError(f'unepxected algorithm "{algorithm}", must be one of "ORB" or "RME"')
    else:
        raise ValueError(f'algorithm_name() expects a string', name)

#---------------------------------------------------------------------------------------------------

class SingleFeatureMultiCrop():
    """This object is used to configure all of the parameters for the
    pattern matching computation. You can configure the computation by
    reading command line arguments, by reading JSON files, or by
    reading the state of the GUI. The GUI itself is a visualization of
    the configuration (the set of all parameters) for the pattern
    matching algorithm.
    """

    def __init__(self, cli_config=None):
        self.feature_region = None
        self.crop_regions = {}
        self.file_encoding = 'png'
        self.output_dir = Path.cwd()
        self.set_target_fileset(None)
        self.output_dir = None
        self.save_distance_map = None
        self.target = CachedCVImageLoader()
        self.target_matched_points = []
        self.target_image = CachedCVImageLoader()
        self.reference_image = CachedCVImageLoader()
        self.threshold = 0.92
        self.rme_matcher = None
        self.orb_matcher = None
        self.algorithm = None
        self.cli_config = None
        if cli_config:
            self.set_cli_config(cli_config)
        else:
            pass
        if self.algorithm is None:
            self.set_algorithm('ORB')
        else:
            pass
 
    def get_cli_config(self):
        return self.cli_config

    def set_cli_config(self, config):
        self.cli_config = config
        self.set_target_fileset(config.inputs)
        # Load the reference right away, if it is not None
        if config.pattern is None:
            pass
        else:
            self.reference_image.load_image(path=config.pattern)
        self.output_dir = Path(config.output_dir)
        self.threshold = config.threshold
        self.file_encoding = config.encoding
        self.save_distance_map = config.save_map
        self.set_file_encoding(config.encoding)
        self.threshold = config.threshold
        if config.crop_regions_json:
            self.crop_regions = config.crop_regions_json
        else:
            pass
        self.set_algorithm(str(config.algorithm).upper())

    def get_orb_matcher(self):
        return self.orb_matcher

    def get_rme_matcher(self):
        return self.rme_matcher

    def get_algorithm(self):
        return self.algorithm

    def set_algorithm(self, algorithm_label):
        if algorithm_label == 'RME':
            if not self.rme_matcher:
                self.rme_matcher = RMEMatcher(self)
            else:
                pass
            self.algorithm = self.rme_matcher
        elif algorithm_label == 'ORB':
            if not self.orb_matcher:
                self.orb_matcher = ORBMatcher(self)
            else:
                pass
            self.algorithm = self.orb_matcher
        else:
            raise ValueError(
                f'unexpected algorithm "{config.algorithm}", must be one of "ORB" or "RME"'
              )

    def get_threshold(self):
        """Return the threshold as a value betwee 0.0 and 1.0"""
        return self.threshold

    def set_threshold(self, threshold):
        """Set the threshold as a value betwee 0.0 and 1.0"""
        if threshold > 1.0:
            raise ValueError('threshold value out of range (0.0, 1.0)', threshold)
        else:
            self.threshold = threshold
            target = self.get_target_image()
            reference = self.get_reference_image()
            if (target is not None) and \
              (target.get_image() is not None) and \
              (reference is not None) and \
              (reference.get_image() is not None):
                return self.algorithm.set_threshold(threshold)
            else:
                return None

    def get_file_encoding(self):
        return self.file_encoding

    def set_file_encoding(self, encoding):
        self.file_encoding = fs.image_file_format_suffix(encoding)

    def get_target_image(self):
        return self.target_image

    def set_target_image(self, target):
        if isinstance(target, CachedCVImageLoader):
            self.target_image = target
        elif isinstance(target, PurePath) or isinstance(target, str):
            self.target_image.load_image(path=target)
        else:
            raise ValueError('value of incorrect type for "target" image', target)

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

    def get_reference_image(self):
        return self.reference_image

    def set_reference_image(self, reference):
        if isinstance(reference, str):
            reference = CachedCVImageLoader(path=Path(str))
        elif isinstance(reference, Path) or isinstance(reference, PurePath):
            reference = CachedCVImageLoader(path=reference)
        elif isinstance(reference, CachedCVImageLoader):
            pass
        else:
            raise ValueError('expecting CachedCVImageLoader or Path as argument')
        self.reference_image = reference
        if reference is not None and reference.get_path() is not None:
            #print(f'{self.__class__.__name__}.set_reference_image({reference.get_path()!r})')
            self.algorithm.update_reference_image()
        else:
            pass

    def get_output_dir(self):
        return self.output_dir

    def set_output_dir(self, output_dir):
        #print(f'{self.__class__.__name__}.set_output_dir({str(output_dir)!r})')
        self.output_dir = Path(output_dir)

    def guess_compute_steps(self):
        if self.algorithm is not None:
            return self.algorithm.guess_compute_steps()
        else:
            return None

    ###############  Setting up feature and crop regions  ###############

    def get_crop_regions(self):
        """Get the whole dictionary that maps key names to rectangle values."""
        return self.crop_regions

    def set_crop_regions(self, crop_regions):
        """Set a whole new dictionary for mapping key names to rectangle values."""
        self.crop_regions = util.dict_keep_defined(self.crop_regions)

    def get_feature_region(self):
        return self.feature_region

    def set_feature_region(self, rect):
        """Set the current crop_rect value, and redraw the rectangle in the
        view. The rectangle change callback is not called."""
        if self.reference:
            self.reference.set_crop_rect(rect)
        else:
            pass
        self.feature_region = self.reference.get_crop_rect()

    def new_crop_region(self, label, rect):
        #print(f'{self.__class__.__name__}.new_crop_region({label!r}, {rect!r})')
        if not label:
            raise ValueError('cannot create crop region "None" as label')
        elif label in self.crop_regions:
            self.print_state() 
            return False
        else:
            self.crop_regions[label] = rect
            self.print_state() 
            return True

    def set_crop_region(self, region_name, rect):
        """Change the rectangle of the named crop region. If the 'region_name'
        given is None, this function calls 'set_feature_region()' instead."""
        if region_name is None:
            #print(f'{self.__class__.__name__}.set_crop_region({region_name!r}, {rect}) #(set self.feature_region)')
            self.print_state()
            self.feature_region = rect
        if region_name in self.crop_regions:
            if region_name in self.crop_regions:
                #print(f'{self.__class__.__name__}.set_crop_region({region_name!r}, {rect}) #(set self.crop_region[{region_name!r}])')
                self.print_state()
                self.crop_regions[region_name] = rect
            else:
                #print(f'{self.__class__.__name__}.set_crop_region({region_name!r}, {rect}) #(failed, {region_name!r} not defined)')
                self.print_state()
                return False

    def delete_crop_region(self, region_name):
        #print(f'{self.__class__.__name__}.delete_crop_region({region_name!r})')
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
            result = self.delete_crop_region(old_name)
            #print(f'{self.__class__.__name__}.rename_crop_region({old_name!r}, {new_name!r}) #(crop_regions = {self.crop_regions})')
            self.print_state()
            return result
        elif (new_name in self.crop_regions):
            #print(f'{self.__class__.__name__}.rename_crop_region({old_name!r}, {new_name!r}) #({new_name!r} already exists)')
            return False
        else:
            if old_name in self.crop_regions:
                rect = self.crop_regions[old_name]
            else:
                rect = None
            del self.crop_regions[old_name]
            self.crop_regions[new_name] = rect
            #print(f'{self.__class__.__name__}.rename_crop_region({old_name!r}, {new_name!r}) #(crop_regions = {self.crop_regions})')
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
        defined for this to work. """
        ref_rect = self.get_feature_region()
        if ref_rect is None:
            #print(f'{self.__class__.__name__}.iterate_crop_regions() #(no reference rectangle set)')
            return None
        else:
            (x0, y0, width, height) = ref_rect
            crop_rect_iter = self.get_crop_regions()
            if (crop_rect_iter is None) or (len(crop_rect_iter) == 0):
                #print(f'{self.__class__.__name__}.iterate_crop_regions() #(no crop regions, using feature region as single crop region)')
                crop_rect_iter = iter([(None, ref_rect)])
            else:
                #print(f'{self.__class__.__name__}.iterate_crop_regions() #(iterating over {len(crop_rect_iter)} crop regions)')
                crop_rect_iter = crop_rect_iter.items()
            #----------------------------------------
            for (x,y,_similarity) in point_list:
                x_off = x - x0
                y_off = y - y0
                for (label, (crop_x, crop_y, width, height)) in crop_rect_iter:
                    yield (label, (crop_x+x_off, crop_y+y_off, width, height,),)

    ############  Calling into algorithms  ############

    def match_on_file(self, progress=None):
        """See documentation for DataPrepKit.AbstractMatcher.match_on_file()."""
        return self.algorithm.match_on_file(progress=progress)

    def get_matched_points(self):
        #print(f'{self.__class__.__name__}.get_matched_points()')
        return self.algorithm.get_matched_points()

    def save_selected(self, target_image=None, crop_regions=None, output_dir=None):
        #print(f'{self.__class__.__name__}.save_selected()')
        match_item_list = self.algorithm.match_on_file()
        #print(f'{self.__class__.__name__}.save_selected() #(match_on_file() -> {len(match_item_list)} matches)')
        #for (i, pt) in zip(range(0,len(match_item_list)), match_item_list):
        #    print(f'    {i}: {pt}')
        # -----------------------------------------------------------------------
        target_image = self.target_image if target_image is None else target_image
        output_dir = self.get_output_dir() if output_dir is None else output_dir
        if not output_dir.is_dir():
            self.results.mkdir(parents=True, exist_ok=True)
        else:
            pass
        crop_regions = self.get_crop_regions() if crop_regions is None else crop_regions
        if self.save_distance_map:
            self.algorithm.save_calculation(target_image)
        else:
            pass
        #print(f'{self.__class__.__name__}.save_selected() #(output_dir = {str(output_dir)!r})')
        target_image_path = target_image.get_path()
        for match_item in match_item_list:
            # Here we make use of the "iterate_crop_regions()" method
            # inherited from the "SingleFeatureMultiCrop" class.
            #output_dir = output_dir / PurePath(label) if label is not None else output_dir
            suffix = self.get_file_encoding()
            suffix = target_image_path.suffix \
                if (suffix == '(same)') or (suffix is None) else f'.{suffix}'
            try:
                if (crop_regions is None) or (len(crop_regions) == 0):
                    output_path = output_dir / PurePath(
                        target_image_path.stem + '{image_ID}' + suffix
                      )
                    feature_region = self.reference_image.get_crop_rect()
                    #print(f'{self.__class__.__name__}.save_selected() #(output_dir = {str(output_path)!r})')
                    match_item.crop_write_images({'': feature_region}, str(output_path))
                else:
                    output_path = output_dir / PurePath('{label}') / PurePath(
                        target_image_path.stem + f'{image_ID}' + suffix
                      )
                    #print(f'{self.__class__.__name__}.save_selected() #(output_dir = {str(output_path)!r})')
                    match_item.crop_write_image(crop_regions, str(output_path))
            except OSError as err:
                traceback.print_exception(err)

    def crop_matched_references(self, target_image_path=None, output_dir=None):
        # Create results directory if it does not exist
        #print(f'{self.__class__.__name__}.crop_matched_references({target_image_path!r}) #(after clean-up self.crop_regions)')
        target_image = None
        if target_image_path is None:
            target_image = self.target
        else:
            target_image = CachedCVImageLoader(
                path=target_image_path,
                crop_rect=self.target.get_crop_rect(),
              )
        self.print_state()
        self.save_selected(target_image, output_dir)

    def batch_crop_matched_patterns(self, target_fileset=None, output_dir=None, progress=None):
        """Pass an optional 'FileSet' object, the 'target_fileset' field of
        this class is used by default. Pass an optional 'output_dir'
        file path, the (output_dir' field is used by default. This
        method will run pattern matching on each image in the fileset,
        and then crop and save all matched images to a result
        directory. """
        target_fileset = self.target_fileset if target_fileset is None else target_fileset
        self.reference_image.load_image(crop_rect=self.feature_region)
        #print(f'{self.__class__.__name__}.batch_crop_matched_references() #(will operate on {len(self.target_fileset)} image files)')
        for image in target_fileset:
            #print(
            #    f'image = {image!s}\n'
            #    f'output_dir = {self.output_dir}\n'
            #    f'threshold = {self.threshold}\n'
            #    f'save_distance_map = {self.save_distance_map}',
            #  )
            if progress is not None:
                progress.update_progress(1, label=f'{str(image)!r}')
            else:
                pass
            try:
                self.crop_matched_references(image, output_dir)
            except Exception as err:
                if progress is not None:
                    progress.reject()
                else:
                    pass
                raise err
        if progress is not None:
            progress.accept()
        else:
            pass

    ###############  Debugging methods  ###############

    def rect_to_str(self, rect):
        return repr(rect)

    def print_state(self, out=sys.stdout):
        out.write(f'self.feature_region: {self.rect_to_str(self.feature_region)}\n')
        out.write( '  self.crop_regions: {\n')
        for name, rect in self.crop_regions.items():
            out.write(f'      {name!r}: {self.rect_to_str(rect)}\n')
        out.write( '    }\n')

