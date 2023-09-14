import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

from DataPrepKit.ImageDisplay import ImageDisplay
from DataPrepKit.ImageFileLayer import ImageFileLayer
from DataPrepKit.DragDropHandler import DragDropHandler

class ImagePreview(qt.QWidget):
    """An image preview is a SimpleImagePreview with a second widget above
    it to display information to the end user about what is being seen
    in the view. This class has the same API as 'SimpleImagePreview()'
    but adds the 'set_info_widget()' method for showing and hiding
    information about the view as well.
    """

    def __init__(self, info_widget=None, parent=None):
        super().__init__()
        qt.QWidget.__init__(self)
        DragDropHandler.__init__(self)
        self._display = SimpleImagePreview(parent=parent)
        self._display.setResizeAnchor(qt.QGraphicsView.AnchorViewCenter)
        self._splitter = qt.QVBoxLayout(self)
        self._splitter.setSizePolicy(
            QSizePolicy(
                qgui.QSizePolicy.Expanding,
                qgui.QSizePolicy.Preferred,
              ),
          )
        self._info_widget = None
        self.set_info_widget(info_widget)
        self._splitter.insertWidget(1, self._display)

    def set_info_widget(self, info_widget):
        """Show a widget in the region above the image view. Remove the widget
        by calling this function with None as the argument."""
        if self._info_widget is not None:
            self._info_widget.deleteLater()
        else:
            pass
        self._info_widget = info_widget
        if self._info_widget is not None:
            self._splitter.insertWidget(0, self._info_widget)
            self._info_widget.setParent(self)
            self._info_widget.show()
        else:
            pass

    def get_display(self):
        return self._display

    def get_image_layer(self):
        return self._display.get_image_layer()

    def set_image_buffer(self, filepath, image_buffer):
        self._display.set_image_buffer(filepath, image_buffer)

    def get_filepath(self):
        return self._display.get_filepath()

    def set_filepath(self, filepath):
        self._display.set_filepath(filepath)

    def center_view_on_image(self):
        self._display.center_view_on_image()

    def clear(self):
        self._display.clear()

    def redraw(self):
        self._display.redraw()

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
        self._image_file_layer = ImageFileLayer(self.get_scene())
        #self.setViewportUpdateMode(qt.QGraphicsView.BoundingRectViewportUpdate)
        self.setResizeAnchor(qt.QGraphicsView.AnchorViewCenter)
        self.setSizePolicy(
            qt.QSizePolicy(
                qt.QSizePolicy.Expanding,
                qt.QSizePolicy.Expanding,
              ),
          )

    def sizeHint(self):
        screen = qgui.QGuiApplication.primaryScreen().virtualSize()
        return qcore.QSize(screen.width(), screen.height())

    def resizeEvent(self, newSize):
        super(SimpleImagePreview, self).resizeEvent(newSize)
        self.center_view_on_image()

    def get_image_layer(self):
        return self._image_file_layer

    def set_image_buffer(self, filepath, image_buffer):
        """Sets the image buffer (which must be an instance of QImage) and the
        filepath without loading the image buffer from the filepath."""
        self._image_file_layer.set_image_buffer(filepath, image_buffer)
        if image_buffer is None:
            self.clear()
        else:
            pass

    def get_filepath(self):
        return self._image_file_layer.get_filepath()

    def set_filepath(self, filepath):
        #print(f'SimpleImagePreview.set_filepath("{filepath!s}")')
        self._image_file_layer.set_filepath(filepath)
        self.center_view_on_image()

    def center_view_on_image(self):
        """When this function is called, the QGraphcisView.sceneRect property
        is set to the QPixmapItem.boundingRect property of the image
        layer. If a QPixmap has not been loaded yet, this function
        does nothing."""
        if self._image_file_layer is not None:
            layer_item = self._image_file_layer.get_pixmap_item()
            if layer_item is not None:
                #self.setSceneRect(self._image_file_layer.get_image_bounds())
                self.fitInView(layer_item, 1) # 1: qcore.AspectRatioMode::KeepAspectRatio
            else:
                pass
        else:
            pass

    def clear(self):
        self._image_file_layer.clear()
        self.resetTransform()

    def redraw(self):
        self._image_file_layer.layer_bounds_scene_rect()
        self._image_file_layer.redraw()
