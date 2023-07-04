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
        #self.setViewportUpdateMode(4) # 4: QGraphicsView::BoundingRectViewportUpdate
        self.setResizeAnchor(1) # 1: QGraphicsView::AnchorViewCenter

    def resizeEvent(self, newSize):
        super(SimpleImagePreview, self).resizeEvent(newSize)
        self.center_view_on_image()

    def get_filepath(self):
        return self.image_file_layer.get_filepath()

    def set_filepath(self, filepath):
        self.image_file_layer.set_filepath(filepath)
        self.center_view_on_image()

    def center_view_on_image(self):
        """When this function is called, the QGraphcisView.sceneRect property
        is set to the QPixmapItem.boundingRect property of the image
        layer. If a QPixmap has not been loaded yet, this function
        does nothing."""
        if self.image_file_layer is not None:
            layer_item = self.image_file_layer.get_pixmap_item()
            if layer_item is not None:
                #self.setSceneRect(self.image_file_layer.get_image_bounds())
                self.fitInView(layer_item, 1) # 1: qcore.AspectRatioMode::KeepAspectRatio
            else:
                pass
        else:
            pass

    def clear(self):
        self.image_file_layer.clear()
        self.resetTransform()

    def redraw(self):
        self.image_file_layer.layer_bounds_scene_rect()
        self.image_file_layer.redraw()
