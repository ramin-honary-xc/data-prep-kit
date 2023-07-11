from DataPrepKit.ImageDisplay import ImageDisplay
from DataPrepKit.ImageFileLayer import ImageFileLayer
from DataPrepKit.DragDropHandler import DragDropHandler

class SimpleImagePreview(ImageDisplay, DragDropHandler):
    """This class combines an 'ImageDisplay' with an 'ImageFileLayer', and
    provides methods for displaying images in the display by reading
    them from a file. DragDropHandler is also provided, see the
    documentation on that class for how to override drag and drop
    handler methods. Note that drag and drop is disabled by default,
    so you would need to call the "enable_drop_handlers()" method
    inherited from DragDropHandler.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        DragDropHandler.__init__(self)
        self.image_file_layer = ImageFileLayer(self.get_scene())
        #self.setViewportUpdateMode(4) # 4: QGraphicsView::BoundingRectViewportUpdate
        self.setResizeAnchor(1) # 1: QGraphicsView::AnchorViewCenter

    def get_image_layer(self):
        return self.image_file_layer

    def set_image_buffer(self, filepath, image_buffer):
        """Sets the image buffer (which must be an instance of QImage) and the
        filepath without loading the image buffer from the filepath."""
        self.image_file_layer.set_image_buffer(filepath, image_buffer)

    def resizeEvent(self, newSize):
        super(SimpleImagePreview, self).resizeEvent(newSize)
        self.center_view_on_image()

    def get_filepath(self):
        return self.image_file_layer.get_filepath()

    def set_filepath(self, filepath):
        print(f'SimpleImagePreview.set_filepath("{filepath!s}")')
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
