from DataPrepKit.FileSet import FileSet, image_file_suffix_set
from pathlib import Path
import cv2 as cv

class BatchResize():
    """This class contains the variables and methods necessary to
    configure and run a batch resize process. The initializer takes an
    object constructed from an ArgumentParser, it is also possible to
    override the command line parameters or pass None as the command
    line paramters and only specify the width, height, and list of
    files on which to operate.
    """

    def __init__(
        self,
        config=None,
        fileset=None,
        output_dir=None,
        width=None,
        height=None,
        interpolate=None,
        encoding=None,
      ):
        """This initializer takes all of the input arguments and the arguments
        passed through "config" on the command line and merges them
        together.  Arguments passed to the initializer take priority
        over the "config". Once initialized, a batch process can
        begin. """
        cfg_w = None
        cfg_h = None
        if config is not None:
            cfg_w = config.width
            cfg_h = config.height
            self.output_dir = output_dir if output_dir is not None else config.output_dir
            self.interpolate = interpolate if interpolate is not None else config.interpolate
            self.encoding = encoding if encoding is not None else config.encoding
        else:
            self.output_dir = output_dir
            self.interpolate = iterp
        self.width = \
            width if width is not None else cfg_w
        self.height = \
            height if height is not None else cfg_h
        self.fileset = fileset
        if fileset is None:
            self.fileset = FileSet()
        else:
            pass
        self.fileset.merge(config.inputs)

    def get_fileset(self):
        return self.fileset

    def get_resize_width(self):
        return self.width

    def set_resize_width(self, width):
        self.width = width

    def get_resize_height(self):
        return self.height

    def set_resize_height(self, height):
        self.height = height

    def get_file_encoding(self):
        return self.encoding

    def set_file_encoding(self, encoding):
        encoding = encoding.lower()
        if encoding in image_file_suffix_set:
            self.encoding = encoding
        else:
            raise ValueError(f'unknown file encoding {encoding!r}')

    def set_output_dir(self, output_dir):
        self.output_dir = PurePath('./resized-images') if output_dir is None else output_dir

    def get_output_dir(self):
        return self.output_dir

    def batch_resize_images(self, output_dir=None):
        """Run resize on all files in "self.fileset"."""
        # Create a local copy of width and height in case these values
        # are changed in the GUI before the batch operation completes.
        width  = self.width
        height = self.height
        if self.output_dir:
            path = Path(self.output_dir)
            path.mkdir(parents=True, exist_ok=True)
        else:
            self.output_dir = Path('./results')
        for file in self.fileset:
            self.resize_image_file_and_save(file, size=(width,height,))

    def check_size_params(self, size=None):
        (width, height) = (self.width, self.height) if size is None else size
        if width is None:
            raise ValueError('scale "--width" ("-x") argument is not specified')
        elif height is None:
            raise ValueError('scale "--height" ("-y") argument is not specified')
        else:
            pass
        return (width, height)

    def resize_image_file_and_save(self, path, size=None):
        """Resize a single image file given the parameters defined at
        initialization time, or else with the given size
        parameter. This function is to be called from scripts, so
        usually avoids crashing on exceptions.
        """
        (width, height) = self.check_size_params(size)
        path = Path(path)
        if not path.is_file():
            print(f'ERROR: not a regular file {path!r}')
        else:
            try:
                write_path = Path(self.output_dir) / Path(f'{path.stem!s}.{self.encoding}')
                cv.imwrite(str(write_path), self.resize_image_buffer(cv.imread(str(path))))
                print(f'{write_path!s}')
            except Exception as e:
                print(f'ERROR: {e}')

    def resize_image_file(self, path, size=None):
        """Resize a single image file given the parameters defined at
        initialization time, or else with the given size
        parameter. This function is to be called from scripts, so
        usually avoids crashing on exceptions. This function does not
        write the resized image buffer, it merely returns it along
        with the original image buffer.
        """
        (width, height) = self.check_size_params(size)
        path = Path(path)
        if not path.is_file():
            print(f'ERROR: not a regular file {path!r}')
        else:
            try:
                input_buffer = cv.imread(str(path))
                return (input_buffer, self.resize_image_buffer(input_buffer))
            except Exception as e:
                print(f'ERROR: {e}')

    def resize_image_buffer(self, input_image):
        print(f'BatchResize.resize_image_buffer() #(image_buffer = {type(input_image)}, self.width = {self.width}, self.height = {self.height})')
        return cv.resize(
            input_image,
            (round(self.width), round(self.height)),
            0, 0,
            self.interpolate
          )
