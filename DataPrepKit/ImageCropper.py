from copy import deepcopy
import os
from pathlib import (PurePath, Path)

import cv2 as cv

import traceback

####################################################################################################

class ImageWithORB():
    """This class defines an image object, provides an API to run ORB on
    the image, and to associate the ORB keypoints with the image."""

    def __init__(self, filepath):
        if isinstance(filepath, str):
            filepath = PurePath(filepath)
        elif not isinstance(filepath, PurePath):
            raise ValueError( \
                f'ImageWithORB.crop_and_save() method argument output_dir not a PurePath value'
              )
        else:
            pass
        self.filepath = filepath
        self.orb_config = None
        self.ORB = None
        self.keypoints = None
        self.descriptors = None
        self.midpoint = None
        self.init_crop_rect = None
        self.crop_rect = None

    def __hash__(self):
        return hash(self.filepath)

    def __getitem__(self, i):
        return self.keypoints[i]

    def __len__(self):
        if self.keypoints is None:
            return 0
        else:
            return len(self.keypoints)

    def __str__(self):
        return str(self.filepath)

    def __eq__(self, a):
        return \
            (a is not None) and \
            (self.filepath == a.filepath) and \
            (self.orb_config == a.orb_config)

    def __ne__(self, a):
        return not self.__eq__(a)

    def get_orb_config(self):
        return self.orb_config

    def get_filepath(self):
        return self.filepath

    def get_keypoints(self):
        return self.keypoints

    def get_midpoint(self):
        return self.midpoint

    def get_ORB(self):
        return self.ORB

    def get_descriptors(self):
        return self.descriptors

    def get_midpoint(self):
        return self.midpoint

    def get_crop_rect(self):
        """The crop rect is a 4-tuple (x, y, width, height)"""
        return self.crop_rect

    def set_crop_rect(self, rect):
        """The crop rect must be a 4-tuple (x, y, width, height). This
        function should be called when the end user draws a new crop
        rectangle on the "Reference" image view. Use
        "set_relative_crop_rect()" to compute the crop_rect relative to
        the keypoints found by the ORB algoirhtm.
        """
        if rect is None:
            self.crop_rect = None
        elif (not isinstance(rect, tuple)) or (len(rect) != 4):
            raise ValueError(f'ImageWithORB.set_crop_rect() expects 4-tuple value', rect)
        else:
            self.crop_rect = rect

    def set_relative_crop_rect(self, ref):
        """Compute the crop_rect for this item relative to a given reference item."""
        if ref is self:
            #print(f'ImageWithORB.set_relative_crop_rect(ref) #(ref is self)')
            pass
        elif ref is None:
            #print(f'ImageWithORB.set_relative_crop_rect(None)')
            pass
        elif not isinstance(ref, ImageWithORB):
            raise ValueError(
                'ImageWithORB.set_relative_crop_rect(ref): '
                'argument "ref" must be of type ImageWithORB',
                ref,
              )
        else:
            pass
        ##self.set_orb_config(ref.get_orb_config())
        ref_rect = ref.get_crop_rect()
        ref_midpoint = ref.get_midpoint()
        #print(f'ImageWithORB.set_relative_crop_rect({ref_rect}) #(midpoint = {ref_midpoint})')
        if (ref_rect is not None) and (ref_midpoint is not None):
            (ref_x, ref_y, ref_width, ref_height) = ref_rect
            (mid_x, mid_y) = ref_midpoint
            if self.midpoint is not None:
                (x, y) = self.midpoint
                self.crop_rect = \
                  ( ref_x - mid_x + x , \
                    ref_y - mid_y + y, \
                    ref_width, \
                    ref_height, \
                  )
            else:
                print(f'ImageWithORB.set_relative_crop_rect() #(failed to compute midpoint)')
        else:
            print(f'ImageWithORB.set_relative_crop_rect() #(crop_rect={ref_rect}, midpoint={ref_midpoint})')

    def reset_crop_rect(self):
        """If the "self.reference_image" is set, you can reset the crop rect to
        the exact size of the "self.reference_image" by calling this function."""
        self.crop_rect = self.init_crop_rect

    def set_orb_config(self, orb_config):
        #print(f'ImageWithORB.set_orb_config({orb_config})')
        if orb_config is None:
            self.orb_config = None
        elif (self.ORB is None) or \
             (self.orb_config is None) or \
             (self.orb_config != orb_config):
                self.force_run_orb(orb_config)
        else:
            #print(f'ImageWithORB.set_orb_config() #(ORB metadata already exists and is up-to-date)')
            pass

    def force_run_orb(self, orb_config):
        #print(f'ImageWithORB.force_run_orb() #(set self.orb_config {str(self.orb_config)})')
        self.orb_config = deepcopy(orb_config)
        path = os.fspath(self.filepath)
        pixmap = cv.imread(path, cv.IMREAD_GRAYSCALE)
        if pixmap is not None:
            # Set the init_crop_rect
            height, width = pixmap.shape
            self.init_crop_rect = (0, 0, width, height)
            # Run the ORB algorithm
            #print(f'ImageWithORB.force_run_orb({str(orb_config)})')
            ORB = cv.ORB_create( \
                nfeatures=orb_config.get_nFeatures(), \
                scaleFactor=orb_config.get_scaleFactor(), \
                nlevels=orb_config.get_nLevels(), \
                edgeThreshold=orb_config.get_edgeThreshold(), \
                firstLevel=orb_config.get_firstLevel(), \
                WTA_K=orb_config.get_WTA_K(), \
                scoreType=orb_config.get_scoreType(), \
                patchSize=orb_config.get_patchSize(), \
                fastThreshold=orb_config.get_fastThreshold(), \
              )
            keypoints, descriptor = ORB.detectAndCompute(pixmap, None)
            self.ORB = ORB
            self.keypoints = keypoints
            self.descriptor = descriptor
            num_points = len(self.keypoints)
            #print(f'ImageWithORB.force_run_orb() #(generated {num_points} keypoints)')
            x_sum = 0
            y_sum = 0
            for key in self.keypoints:
                (x, y) = key.pt
                x_sum = x_sum + x
                y_sum = y_sum + y
            if num_points > 0:
                self.midpoint = (x_sum / num_points, y_sum / num_points)
            else:
                print(f'ImageWithORB.force_run_orb() #(cannot find center of mass for zero points)')
                self.midpoint = None
        else:
            print(f'ImageWithORB.force_run_orb() #(failed to load pixmap for path {path}')

    def crop_and_save(self, output_dir):
        if self.crop_rect is not None:
            pixmap = cv.imread(os.fspath(self.filepath))
            if pixmap is not None:
                path = PurePath(output_dir) / self.filepath.name
                (x_min, y_min, width, height) = self.crop_rect
                x_max = round(x_min + width)
                y_max = round(y_min + height)
                x_min = round(x_min)
                y_min = round(y_min)
                #print(
                #    f'ImageWithORB.crop_and_save("{str(path)}") -> '
                #    f'x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max})' \
                #  )
                cv.imwrite(os.fspath(path), pixmap[ y_min:y_max , x_min:x_max ])
            else:
                raise ValueError( \
                    f'ImageWithORB("{str(self.filepath)}") failed to load file path as image' \
                  )
        else:
            raise ValueError( \
                f'ImageWithORB("{str(self.filepath)}").crop_and_save() failed,'
                f' undefined "crop_rect" value' \
              )

#---------------------------------------------------------------------------------------------------

def check_param(label, param, gte, lte):
    """This function is used mostly when setting arguments taken from the
    GUI. It raises a ValueError if the parameter is out of the bounds
    given by 'gte' and 'lte', the GUI even handler needs to catch this
    and report the error to the user."""
    if gte <= param and param <= lte:
        pass
    else:
        raise ValueError(
            f'Parameter "{label}" must be greater/equal to {gte} and less/equal to {lte}'
          )

class ORBConfig():
    """This data type contains values used to parameterize the ORB feature
    selection algorithm. It overrides the equality operator so that we
    can detect when the config has changed, and therefore when we need
    to re-run the ORB algorithm.
    """
    def __init__(self):
        self.nFeatures = 1000
        self.scaleFactor = 1.2
        self.nLevels = 8
        self.edgeThreshold = 31
        self.firstLevel = 0
        self.WTA_K = 2
        self.scoreType = 0 # O = HARRIS_SCORE (could also be 1 = FAST_SCORE)
        self.patchSize = 31
        self.fastThreshold = 20

    def __eq__(self, a):
        return (
            (a is not None) and \
            (self.nFeatures == a.nFeatures) and \
            (self.scaleFactor == a.scaleFactor) and \
            (self.nLevels == a.nLevels) and \
            (self.edgeThreshold == a.edgeThreshold) and \
            (self.firstLevel == a.firstLevel) and \
            (self.WTA_K == a.WTA_K) and \
            (self.scoreType == a.scoreType) and \
            (self.patchSize == a.patchSize) and \
            (self.fastThreshold == a.fastThreshold) \
          )

    def to_dict(self):
        return \
          { 'nFeatures': self.nFeatures,
            'scaleFactor': self.scaleFactor,
            'nLevels': self.nLevels,
            'edgeThreshold': self.edgeThreshold,
            'firstLevel': self.firstLevel,
            'WTA_K': self.WTA_K,
            'scoreType': self.scoreType,
            'patchSize': self.patchSize,
            'fastThreshold': self.fastThreshold,
          }

    def __str__(self):
        return str(self.to_dict())

    def get_nFeatures(self):
        return self.nFeatures

    def set_nFeatures(self, nFeatures):
        check_param('number of features', nFeatures, 20, 20000)
        self.nFeatures = nFeatures

    def get_scaleFactor(self):
        return self.scaleFactor

    def set_scaleFactor(self, scaleFactor):
        check_param('scale factor', scaleFactor, 1.0, 2.0)
        self.scaleFactor = scaleFactor

    def get_nLevels(self):
        return self.nLevels

    def set_nLevels(self, nLevels):
        check_param('number of levels', nLevels, 2, 32)
        self.nLevels = nLevels
        if self.firstLevel > nLevels:
            self.firstLevel = nLevels
        else:
            pass

    def get_edgeThreshold(self):
        return self.edgeThreshold

    def set_edgeThreshold(self, edgeThreshold):
        check_param('edge threshold', edgeThreshold, 2, 1024)
        self.edgeThreshold = edgeThreshold

    def get_firstLevel(self):
        return self.firstLevel

    def set_firstLevel(self, firstLevel):
        check_param('first level', firstLevel, 0, self.edgeThreshold)
        self.firstLevel = firstLevel

    def get_WTA_K(self):
        return self.WTA_K

    def set_WTA_K(self, WTA_K):
        check_param('"WTA" factor', WTA_K, 2, 4)
        self.WTA_K = WTA_K

    def get_scoreType(self):
        return self.scoreType

    def set_scoreType(self, scoreType):
        self.scoreType = scoreType

    def get_patchSize(self):
        return self.patchSize

    def set_patchSize(self, patchSize):
        check_param("patch size", patchSize, 2, 1024)
        self.patchSize = patchSize

    def get_fastThreshold(self):
        return self.fastThreshold

    def set_fastThreshold(self, fastThreshold):
        check_param('"FAST" threshold', fastThreshold, 2, 100)
        self.fastThreshold = fastThreshold

#---------------------------------------------------------------------------------------------------

class ImageCropper():
    """This class creates objects that represents the state of the whole
    application.
    """

    def __init__(self):
        self.orb_config = ORBConfig()
        self.image_list = []
        self.reference_image = None
        self.selected_image = None
        
    def get_selected_image(self):
        return self.selected_image

    def set_selected_image(self, selected_image):
        if isinstance(selected_image, ImageWithORB):
            #print(f'ImageCropper.set_selected_image("{str(selected_image.get_filepath())}")')
            self.selected_image = selected_image
            if self.reference_image is not None:
                self.selected_image.set_orb_config(self.orb_config)
                self.selected_image.set_relative_crop_rect(self.reference_image)
            else:
                #print(f'ImageCropper.set_selected_image() #(no reference image, not updating crop rect)')
                pass
        else:
            raise ValueError(
                f'ImageCropper.set_selected_image() '
                f'#(called with argument of type {str(type(selected_image))})'
              )

    def get_image_list(self):
        return self.image_list

    def add_image_list(self, items):
        """Takes a list of file paths or strings, converts them to
        ImageWithORB values, and appends them to the image_list."""
        if isinstance(items, list):
            self.image_list = \
                list(
                    dict.fromkeys(
                        self.image_list + \
                        [ImageWithORB(str(item)) for item in items]
                      )
                  )
        elif isinstance(items, ImageWithORB):
            self.image_list.append(items)
        else:
            raise ValueError(
                f'ImageCropper.add_image_list() expects ImageWithORB or list of ImageWithORB'
              )

    def get_orb_config(self):
        return self.orb_config

    def set_orb_config(self, orb_config):
        #print(f'ImageCropper.set_orb_config({orb_config})')
        if (orb_config is not None) and (not isinstance(orb_config, ORBConfig)):
            raise ValueError(
                f'MainAppMode.set_orb_config() called with value of type {str(type(orb_config))}',
                orb_config,
              )
        elif self.reference_image is not None:
            self.reference_image.set_orb_config(orb_config)
        else:
            pass
        #print(f'ImageCropper.set_orb_config() #(set self.orb_config = {orb_config})')
        self.orb_config = deepcopy(orb_config)

    def get_crop_rect(self):
        """this field is of type (x_pix_offset, y_pix_offset, pix_width, pix_height) or None
        """
        print(f'MainAppMode.get_crop_rect() #(type(self.reference_image) = {type(self.reference_image)})')
        if self.reference_image is not None:
            return self.reference_image.get_crop_rect()
        else:
            return None

    def set_crop_rect(self, crop_rect):
        if self.reference_image is not None:
            self.reference_image.set_crop_rect(crop_rect)
            if self.selected_image is not None:
                self.selected_image.set_relative_crop_rect(self.reference_image)
        else:
            print(f'ImageCropper.set_crop_rect() #(cannot set crop_rect, no reference image)')

    def get_reference_image(self):
        return self.reference_image

    def set_reference_image(self, item):
        """Takes a ImageWithORB item and makes it the reference image. This
        will call reset_all_crop_rects()
        """
        if item is self.reference_image:
            print(f'ImageCropper.set_reference_image("{str(item.get_filepath())}") #(already using this item as the reference image)')
            return
        elif isinstance(item, PurePath):
            self.reference_image = ImageWithORB(item)
        elif isinstance(item, str):
            self.reference_image = ImageWithORB(item)
        elif isinstance(item, ImageWithORB):
            self.reference_image = item
        else:
            raise ValueError( \
                f'ImageCropper.set_reference_image() expects filepath or '
                f'ImageWithORB, was instead passed argument of type {type(item)}' \
              )
        print(f'ImageCropper.set_reference_image("{str(item.get_filepath())}")')
        # Now reset the crop_rect and orb_config of all items in the image_list
        #----------------------------------------
        # Set the ORB config for the reference image, this may trigger
        # a new ORB calculation if the config has changed since it was
        # last calculated for this image.
        self.reference_image.set_orb_config(self.orb_config)
        #----------------------------------------
        # Also update the orb_config and crop_rect of the selected
        # image.
        self.selected_image.set_orb_config(self.orb_config)
        self.selected_image.set_relative_crop_rect(self.reference_image)

    def get_reference_image_filepath(self):
        return self.reference_image_filepath

    def get_keypoints(self):
        if self.reference_image is not None:
            return self.reference_image.get_keypoints()
        else:
            return None

    def get_descriptor(self):
        if self.reference_image is None:
            return None
        else:
            return self.reference_image.get_descriptor()

    def crop_and_save_all(self, output_dir):
        Path(output_dir).mkdir(exist_ok=True)
        for item in self.image_list:
            item.crop_and_save(output_dir)
