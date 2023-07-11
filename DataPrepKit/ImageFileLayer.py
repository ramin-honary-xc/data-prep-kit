import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

class ImageFileLayer():
    """This class defines methods for loading an image from a file path
    and displaying it as a layer in a QGraphicsScene. The logic of
    these layer keeps the image buffered until it is removed from the
    scene. Methods are provided to change which image file is
    displayed in a layer without needing to remove the layer or
    reconstruct the entire QGraphicsScene.

    When initializing an ImageFileLayer, it is OK to pass None for the
    first argument only as long as you call the set_scene() method
    after initialization and before any other method of this class is
    evaluated.
    """

    def __init__(self, scene, filepath=None):
        self.filepath = filepath
        self.scene = scene
        self.pixmap = None
        self.pixmap_item = None
        self.redraw()

    def set_scene(self, scene):
        self.scene = scene

    def get_scene(self):
        return self.scene

    def get_pixmap_item(self):
        return self.pixmap_item

    def get_image_bounds(self):
        """Return a bounding QRectF for the image."""
        if self.pixmap_item is None:
            return None
        else:
            return self.pixmap_item.boundingRect()

    def layer_bounds_scene_rect(self):
        """When this function is called, the QGraphcisScene.sceneRect property
        is set to the QPixmapItem.boundingRect property of this
        layer. If a QPixmap has not been loaded yet, this function
        does nothing."""
        if self.pixmap_item is not None:
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            #print(f'ReferenceImageScene.setSceneRect({self.pixmap_item.boundingRect()})')
        else:
            #print(f'ImageFileLayer.layer_bounds_scene_rect() #(no image file has been loaded)')
            pass

    def get_filepath(self):
        return self.filepath

    def set_filepath(self, filepath):
        self.filepath = filepath
        self.redraw()

    def set_image_buffer(self, filepath, image_buffer):
        """Sets the image buffer (which must be an instance of QImage) and the
        filepath without loading the image buffer from the filepath."""
        if image_buffer is None:
            if self.pixmap_item is not None:
                print(f'ImageFileLayer.set_image_buffer("{filepath!s}") #(self.scene.removeItem())')
                self.scene.removeItem(self.pixmap_item)
            else:
                pass
            return
        elif isinstance(image_buffer, qgui.QPixmap):
            pass
        else:
            raise ValueError(
                f'image_buffer argument type is {type(image_buffer)}, '
                f'not an instance of QPixmap',
                image_buffer,
              )
        if self.pixmap_item is not None:
            print(f'ImageFileLayer.set_image_buffer("{filepath!s}") #(self.scene.removeItem())')
            self.scene.removeItem(self.pixmap_item)
        else:
            pass
        self.pixmap = image_buffer
        self.pixmap_item = self.scene.addPixmap(self.pixmap)
        self.filepath = filepath

    def clear(self):
        if self.pixmap_item is not None:
            self.removeItem(self.pixmap_item)
        else:
            pass
        self.pixmap = None
        self.pixmap_item = None
        
    def redraw(self):
        if self.filepath is not None:
            # If our cached reference is different from the
            # current app model reference image, load it from the
            # file and draw it.
            if self.pixmap_item is not None:
                self.scene.removeItem(self.pixmap_item)
            else:
                pass
            self.pixmap = qgui.QPixmap(str(self.filepath))
            self.pixmap_item = qt.QGraphicsPixmapItem(self.pixmap)
            # Now place the item back into the scene and reset the
            # sceneRect property.
            self.scene.addItem(self.pixmap_item)
        else:
            if self.pixmap_item is not None:
                self.scene.removeItem(self.pixmap_item)
            else:
                pass
