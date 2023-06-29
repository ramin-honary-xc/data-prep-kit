from DataPrepKit.ImageDisplay import ImageDisplay
from DataPrepKit.ImageFileLayer import ImageFileLayer

class SimpleImagePreview(ImageDisplay):
    """This class combines an 'ImageDisplay' with an 'ImageFileLayer', and
    provides methods for displaying images in the display by reading
    them from a file.
    """

    def __init__(self, parent=None):
        super(SimpleImagePreview, self).__init__(parent)
        self.image_file_layer = ImageFileLayer(self.get_scene())

    def get_filepath(self):
        return self.image_file_layer.get_filepath()

    def set_filepath(self, filepath):
        self.image_file_layer.set_filepath(filepath)

    def clear(self):
        self.image_file_layer.clear()

    def redraw(self):
        self.image_file_layer.redraw()
