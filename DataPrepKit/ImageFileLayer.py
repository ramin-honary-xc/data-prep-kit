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

    def layer_bounds_scene_rect(self):
        """When this function is called, the QGraphcisScene.sceneRect property
        is set to the QPixmapItem.boundingRect property of this
        layer. If a QPixmap has not been loaded yet, this function
        does nothing."""
        if self.pixmap_item is not None:
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
        else:
            print(f'ImageFileLayer.layer_bounds_scene_rect() #(no image file has been loaded)')

    def get_filepath(self):
        return self.filepath

    def set_filepath(self, filepath):
        self.filepath = filepath
        self.redraw()

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
            print(f'ReferenceImageScene.setSceneRect({self.pixmap_item.boundingRect()})')
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
        else:
            self.clear()
