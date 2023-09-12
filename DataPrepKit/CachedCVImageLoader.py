from DataPrepKit.RegionSize import RegionSize

import cv2 as cv

#---------------------------------------------------------------------------------------------------

class CachedCVImageLoader():
    """A tool for loading and caching image from a file into an OpenCV image buffer.
    """

    def __init__(self, path=None, crop_rect=None):
        self.crop_rect = crop_rect
        self.path   = path
        self.image  = None

    def load_image(self, path=None, crop_rect=None):
        #print('CachedCVImageLoader.load_image(' +
        #      ('None' if path is None else f'"{path}"') +
        #      ')')
        self.crop_rect = crop_rect
        if path is None:
            path = self.path
            self.force_load_image(path)
        elif path != self.path:
            self.force_load_image(path)
        else:
            pass

    def force_load_image(self, path):
        self.image = cv.imread(str(path))
        if self.image is None:
            self.path = None
            raise ValueError(
                f"Failed to load image file {path!s}",
                path,
              )
        else:
            self.path = path
            #print(f'CachedCVImageLoader.force_load_image() #(success "{self.path}")')

    def get_path(self):
        return self.path

    def get_image(self):
        """This function returns the actual image buffer, and crops the image
        buffer if the set_crop_rect() method has been called to set a
        cropping region."""
        if self.image is None:
            print(f'WARNING: CachedCVImageLoader("{self.path!s}").get_image() returned None')
            return None
        elif self.crop_rect is not None:
            region = RegionSize(*(self.crop_rect))
            #print(f'CachedVCImageLoader.get_image() #(cropping to region {region})')
            return region.crop_image(self.image)
        else:
            return self.image

    def get_raw_image(self):
        """This method is like get_image() but never applies cropping."""
        return self.image

    def set_image(self, path, pixmap):
        self.path = path
        self.image = pixmap

    def clear(self):
        self.set_image(None, None)

    def get_crop_rect(self):
        """You can crop the image before performing processing on it, you can
        do this for true of both pattern and target images. If
        'set_crop_rect()' method has never been called for an object
        of this class, this method returns a rectangle that encompases
        the whole image. If the image is not loaded, this function
        returns None."""
        if self.crop_rect is None:
            if self.image is None:
                return None
            else:
                shape = self.image.shape
                return (0, 0, shape[1], shape[0])
        else:
            return self.crop_rect

    def set_crop_rect(self, crop_rect):
        """You may set the crop_rect to None, in this case the whole image
        will be used, rather than just the region specified by the
        rectangle."""
        self.crop_rect = crop_rect

