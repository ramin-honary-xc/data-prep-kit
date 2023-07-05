from DataPrepKit.FileSet import FileSet
from DataPrepKit.FileSetGUI import FileSetGUI
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader

class ImageDiff():
    """This class provides the model for the ImageDiffGUI controller.  The
    ImageDiff tool takes any one image as a reference and does a
    pixel-by-pixel comparison to whatever other image files you place
    into a list. The pixel comparison is computed by the
    square-difference equation.

    The intended use of this tool is to analyze the output of the
    "patmatkit.py" tool, which searches within a target image for a
    reference image, and any region of the target similar enough to the
    reference is cropped and saved to is owm file. All files produced
    are necesarily the same size as the reference image. This tool
    allows you to visualize the differences between the reference and
    each extracted region of the target.

    However, this program will of course work on any set of images,
    regardless of their origin.
    """

    def __init__(self, path=None, file_set=None):
        self.reference = CachedCVImageLoader(path)
        self.file_set = FileSet(initset=file_set)
        self.show_diff_enabled = True
            # ^ Set to False to show the image without comparison to the reference

    def enable_show_diff(self, boolean):
        """This is the state of the check box that enables or disables
        ordinary image view or difference image view."""
        self.show_diff_enabled = boolean

    def toggle_show_diff(self):
        self.show_diff_enabled = not self.show_diff_enabled

    def get_show_diff(self):
        return self.show_diff_enabled

    def get_fileset(self):
        return self.file_set

    def load_reference_image(self, path):
        self.reference.load_image(path=path)
        
