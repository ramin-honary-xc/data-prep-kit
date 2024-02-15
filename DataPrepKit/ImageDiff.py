from DataPrepKit.FileSet import FileSet
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader
import DataPrepKit.utilities as util
import DataPrepKit.Consts as const

import os
from pathlib import PurePath

import csv
import cv2 as cv
import numpy as np

####################################################################################################

def diff_images(refimg, srcimg, color_map=None):
    """Performs a difference on two images. No dimension checking is
    performed, both images must be the same size. For color images,
    averages each pixel, the returned image is always grayscale,
    unless color_map is supplied in which case the grayscale is
    converted back into a color image.

    A tuple is returned, with the first element being the new
    difference ndarray (possibly colorized), and the second being a
    percentage showing the "similarity" between the two images. The
    "similarity" is the 1.0 minus the average of all pixels in the
    difference image. """
    result_img = cv.absdiff(refimg, srcimg)
    shape = result_img.shape
    if (len(shape) == 3) and ((shape[2] == 3) or (shape[2] == 4)):
        result_img = cv.cvtColor(result_img, cv.COLOR_RGB2GRAY)
    elif len(shape) == 2:
        pass
    else:
        raise ValueError(
            f'unexpected result image shape {shape}',
          )
    (h, w) = (shape[0], shape[1])
    similarity = 1.0 - np.sum(result_img) / (h*w*255)
    if color_map is None:
        pass
    else:
        result_img = util.numpy_map_colors(result_img, color_map)
    return (result_img, similarity)

def rename_path_to_diff(path, output_dir=None):
    if output_dir is None:
        output_dir = path.parent
    else:
        pass
    return output_dir / PurePath(f'{path.stem}_diff{path.suffix}')

def _warn_different_shapes(ref_image, input_image):
    ref_image_buffer = ref_image.get_image()
    input_image_buffer = input_image.get_image()
    if ref_image_buffer.shape != input_image_buffer.shape:
        print(
            f'WARNING: reference image "{ref_image.get_path()}"'
            f' size {ref_image_buffer.shape}'
            f' does not match input image "{input_image.get_path()}"'
            f' size {input_image_buffer.shape}',
          )
        return True
    else:
        return False


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
        self.compare_image = CachedCVImageLoader()
        self.diff_image = CachedCVImageLoader()
        self.show_diff_enabled = True
        self.color_map = const.color_forest_fire
            # ^ Set to False to show the image without comparison to the reference
        self.similarity = None

    def enable_show_diff(self, boolean):
        """This is the state of the check box that enables or disables
        ordinary image view or difference image view. If set to enable
        and the current diff image has not been computed yet, it is
        computed before this function returns. """
        #print(f'ImageDiff.enable_show_diff({boolean})')
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
        #print(f'ImageDiff.set_reference_image_path("{path!s}")')
        self.reference.load_image(path=path)

    def get_compare_image(self):
        return self.compare_iamge

    def get_diff_image(self):
        return self.diff_image

    def get_display_image(self):
        """This method will call 'get_diff_image()' or 'get_compare_image()'
        depending on whether 'enable_show_diff(True)' has been set. """
        if self.show_diff_enabled:
            return (self.diff_image.get_raw_image(), self.similarity)
        else:
            return (self.compare_image.get_raw_image(), None)

    def get_similarity(self):
        return self.similarity

    def get_color_map(self):
        return self.color_map

    def set_color_map(self, color_map):
        if isinstance(color_map, np.ndarray) and \
          (color_map.dtype == np.uint8) and \
          (color_map.shape == (256,3)):
            self.color_map = color_map
        else:
            raise ValueError(
                'color scheme must be numpy.ndarray of dtype uint8 and shape (256,3)',
                color_map
              )

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
        if not self.show_diff_enabled:
            return
        else:
            pass
        input_image = self.compare_image.get_raw_image()
        #print(f'ImageDiff.update_diff_image() #(type(ref_image) = {type(ref_image)}, type(input_image) = {type(input_image)})')
        if (ref_image is None) or (input_image is None):
            print('WARNING: no reference image set, cannot compute image difference')
        elif _warn_different_shapes(self.reference, self.compare_image):
            self.diff_image.clear()
            self.similarity = None
        else:
            (image_buffer, similarity) = diff_images(ref_image, input_image, self.color_map)
            path = self.compare_image.get_path()
            diff_path = rename_path_to_diff(path)
            self.diff_image.set_image(diff_path, image_buffer)
            self.similarity = similarity

    def save_diff_image(self, filepath=None):
        """Save the image content currently in 'self.diff_image'."""
        image_buffer = self.diff_image.get_image()
        if filepath is None:
            filepath = self.diff_image.get_path()
        else:
            pass
        if image_buffer is None:
            raise ValueError(f'No image buffer. Cannot save image "{filepath!s}"')
        else:
            pass
        cv.imwrite(os.fspath(filepath), image_buffer)

    def save_all(self, output_dir=None):
        """This method will compute the difference between the reference and
        every single item in the 'self.file_set', and save each
        computed image in a file named with a string '_diff' appended
        to the file name before the file extension (for example:
        "input.png" becomes "input_diff.png")
        """
        if (output_dir is None) or isinstance(output_dir, PurePath):
            pass
        elif isinstance(output_dir, str):
            output_dir = PurePath(output_dir)
        else:
            raise ValueError('argument must be string or instance of PurePath', output_dir)
        ref_image = self.reference.get_image()
        if ref_image is None:
            raise ValueError('no reference image set')
        else:
            pass
        with \
          open(
            str(output_dir / PurePath('similarity.csv')),
            'w',
            newline='',
          ) as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',', quotechar='\\')
            img_loader = CachedCVImageLoader()
            for path in self.file_set:
                img_loader.load_image(path=path)
                input_image = img_loader.get_image()
                if input_image is None:
                    print(f'WARNING: failed to open image file "{path!s}"')
                elif _warn_different_shapes(self.reference, img_loader):
                    pass
                else:
                    (image_buffer, similarity) = \
                        diff_images(ref_image, input_image, self.color_map)
                    out_path = rename_path_to_diff(path, output_dir)
                    cv.imwrite(os.fspath(out_path), image_buffer)
                    csvwriter.writerow([similarity, out_path.name])
