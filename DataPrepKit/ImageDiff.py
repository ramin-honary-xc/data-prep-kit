from DataPrepKit.FileSet import FileSet
from DataPrepKit.FileSetGUI import FileSetGUI
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader

import cv2 as cv
import numpy as np

####################################################################################################

def diff_images(refimg, srcimg, color_map=None):
    """Performs a difference on two images. No dimension checking is
    performed, both images must be the same size. For color images,
    averages each pixel, the returned image is always grayscale,
    unless color_map is supplied in which case the grayscale is
    converted back into a color image."""
    result_img = cv.absdiff(refimg, srcimg)
    shape = result_img.shape
    if (len(shape) == 3) and ((shape[2] == 3) or (shape[2] == 4)):
        result_img = cv.cvtColor(result_img, cv.COLOR_RGB2GRAY)
    elif len(shape) == 2:
        pass
    else:
        print(f'WARNING DataPrepKit.ImageDiff.diff_images(): unexpected result image shape {shape}')
        pass
    # TODO: apply the color_map
    return result_img

####################################################################################################

class ImageDiff():
    """This class provides the model for the ImageDiffGUI controller. The
    ImageDiff tool takes any one image as a reference and does a
    pixel-by-pixel comparison to whatever other image files you place
    into a list. The pixel comparison is computed by the
    square-difference equation.

    The intended use of this tool is to analyze the output of the
    "patmatkit.py" tool, which searches within a target image for a
    reference image, and any region of the target similar enough to
    the reference is cropped and saved to is owm file. All files
    produced are necesarily the same size as the reference image. This
    tool allows you to visualize the differences between the reference
    and each extracted region of the target.

    However, this program will of course work on any set of images,
    regardless of their origin. """

    def __init__(self, path=None, file_set=None):
        self.reference = CachedCVImageLoader(path=path)
        self.file_set = FileSet(initset=file_set)
        self.compare_image = CachedCVImageLoader();
        self.diff_image = CachedCVImageLoader()
        self.show_diff_enabled = True
            # ^ Set to False to show the image without comparison to the reference

    def enable_show_diff(self, boolean):
        """This is the state of the check box that enables or disables
        ordinary image view or difference image view. If set to enable
        and the current diff image has not been computed yet, it is
        computed before this function returns. """
        print(f'ImageDiff.enable_show_diff({boolean})')
        self.show_diff_enabled = boolean
        path = self.compare_image.get_path()
        if boolean and (path is not None):
            self.update_diff_image()
        else:
            pass

    def toggle_show_diff(self):
        """Like 'enable_show_diff()' but toggles rather than sets."""
        self.enable_show_diff(not self.show_diff_enabled)

    def get_show_diff(self):
        return self.show_diff_enabled

    def get_fileset(self):
        return self.file_set

    def get_reference(self):
        return self.reference

    def set_reference_image_path(self, path):
        print(f'ImageDiff.set_reference_image_path("{path!s}")')
        self.reference.load_image(path=path)

    def get_compare_image(self):
        return self.compare_iamge

    def get_diff_image(self):
        return self.diff_image

    def get_display_image(self):
        """This method will call 'get_diff_image()' or 'get_compare_image()'
        depending on whether 'enable_show_diff(True)' has been set. """
        if self.show_diff_enabled:
            return self.diff_image.get_raw_image()
        else:
            return self.compare_image.get_raw_image()

    def set_compare_image_path(self, path):
        """Set which path is to be compared to the reference image. If
        enable_show_diff(True) has been set, the diff image is also
        computed.
        """
        self.compare_image.load_image(path=path)
        if self.show_diff_enabled:
            self.update_diff_image()
        else:
            pass

    def update_diff_image(self):
        """Compute the difference between the current referene image and the
        given path."""
        ref_image = self.reference.get_raw_image()
        input_image = self.compare_image.get_raw_image()
        print(f'ImageDiff.update_diff_image() #(type(ref_image) = {type(ref_image)}, type(input_image) = {type(input_image)})')
        if (ref_image is not None) and (input_image is not None):
            image_buffer = diff_images(ref_image, input_image)
            path = self.compare_image.get_path()
            self.diff_image.set_image(path, image_buffer)
        else:
            print(f'WARNING: no reference image set, cannot compute image difference')
            pass
