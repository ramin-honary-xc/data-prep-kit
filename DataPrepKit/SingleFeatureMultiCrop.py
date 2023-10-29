import sys

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

