from pathlib import Path, PurePath
import cv2 as cv

import os

#---------------------------------------------------------------------------------------------------

class RegionSize():
    """This class provides utilties for cropping images to the size of a
    rectangle. It is constructed from a rectangle with an offset and
    width and height. The image reference is not stored, you use the
    methods within to perform actions on an image using the rectangle.
    """

    def __init__(self, x, y, width, height):
        if width == 0 or height == 0:
            raise ValueError(
                "RegionSize too small",
                { "crop_width": width,
                  "crop_height": height,
                 },
              )
        else:
            self.x_min = round(min(x, x + width))
            self.y_min = round(min(y, y + height))
            self.x_max = round(max(x, x + width))
            self.y_max = round(max(y, y + height))

    def check_image_size(self, image):
        """Return True if this RegionSize fits within the bounds of the given image."""
        shape = image.shape
        image_height = shape[0]
        image_width = shape[1]
        if (self.x_min > image_width) or \
           (self.y_min > image_height) or \
           (self.x_max > image_width) or \
           (self.y_max > image_height):
               return None
        else:
            return (image_width, image_height)

    def crop_image(self, image, relative_rect=None):
        """Return a copy of the given image cropped to this object's
        rectangle. """
        if self.check_image_size(image):
            return image[ \
                self.y_min : self.y_max, \
                self.x_min : self.x_max \
              ]
        else:
           shape = image.shape
           image_height = shape[0]
           image_width = shape[1]
           x = relative_rect['x'] if relative_rect else 0
           y = relative_rect['y'] if relative_rect else 0
           raise ValueError(
               "pattern crop not fully contained within pattern image",
               {"image_width": image_width,
                "image_height": image_height,
                "crop_X": x,
                "crop_width": self.x_max - self.x_min,
                "crop_Y": y,
                "crop_height": self.y_max - self.y_min,
                },
             )

    def as_file_name(self, prefix=None, suffix='png'):
        """Return a string repreentation of this rectangle object that can be
        appended to a file name. This method is used to describe
        images that have been cropped from a larger image and written
        into a file.
        """
        coord_string = f'{self.x_min:0>5}x{self.y_min:0>5}'
        if prefix is not None and prefix != '':
            return PurePath(f'{prefix}_{coord_string}.{suffix}')
        else:
            return PurePath(f'{coord_string}.{suffix}')

    def crop_write_image(self, image, results_dir, file_prefix=None, file_suffix='png'):
        """Takes the following arguments:

         1. an image to crop, crops it with 'crop_image()'

         2. a dictionary of crop regions (keys are subdirectories in
            which to store cropped images, values are rectangles
            relative to this RegionSize). If this value is None, this
            RegionSize is used as a single crop region.

         3. takes a PurePath() 'results_dir'

         4. The 'file_suffix' must be an element of
            'DataPrepKit.FileSet.image_file_suffix_set', a file suffix
            with no dot (e.g. "png", "bmp", "jpg") indicating the file
            encoding to use according to the OpenCV imwrite()
            function. It defaults to "png".

         It will write the cropped image to the file path given by
         (results_dir/self.as_file_name()) using 'cv.imwrite()'.

        """
        write_path = self.as_file_name(file_prefix, file_suffix)
        write_path = Path(results_dir / write_path)
        #print(f"{self.__class__.__name__}.crop_write_image() #(write file: {write_path!r})")
        write_path.parent.mkdir(exist_ok=True, parents=True)
        cv.imwrite(os.fspath(write_path), self.crop_image(image))

    def get_point_and_size(self):
        """Return a 4-tuple (x,y, width,height)"""
        return (self.x_min, self.y_min, self.x_max - self.x_min, self.y_max - self.y_min)
