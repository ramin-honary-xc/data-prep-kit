from pathlib import PurePath
import cv2 as cv

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
               return False
        else:
            return True

    def crop_image(self, image):
        """Return a copy of the given image cropped to this object's
        rectangle. """
        if self.check_image_size(image):
            return image[ \
                self.y_min : self.y_max, \
                self.x_min : self.x_max \
              ]
        else:
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

    def as_file_name(self):
        """Return a string repreentation of this rectangle object that can be
        appended to a file name. This method is used to describe
        images that have been cropped from a larger image and written
        into a file.
        """
        return PurePath(f"{self.x_min:0>5}x{self.y_min:0>5}.png")

    def crop_write_image(self, image, results_dir, file_prefix=None):
        """Takes an image to crop, crops it with 'crop_image()', takes a
        PurePath() 'results_dir', writes the cropped image to the file
        path given by (results_dir/self.as_file_name()) using
        'cv.imwrite()'.
        """
        write_path = self.as_file_name()
        if file_prefix:
            write_path = PurePath(f"{file_prefix!s}_{write_path!s}")
        else:
            pass
        write_path = results_dir / write_path
        print(f"RegionSize.crop_write_image() #(write file: {write_path})")
        cv.imwrite(str(write_path), self.crop_image(image))

    def get_point_and_size(self):
        """Return a 4-tuple (x,y, width,height)"""
        return (self.x_min, self.y_min, self.x_max - self.x_min, self.y_max - self.y_min)
