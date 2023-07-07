import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

def left_mouse_button(event):
    """Returns true if the given QGraphicsSceneMouseEvent is for a left
    mouse click. Scenes have context menu actions attached to them
    still trigger event handlers on right mouse clicks, so these
    clicks need to be filtered.
    """
    return event.button() == 0x00000001

class ImageDisplay(qt.QGraphicsView):
    """This class simplifies the Qt APIs for graphics by combining a
    QGraphicsView and a QGraphicsScene object into a single object. It
    allocates its own QGraphicsScene. Important methods provided:

      - clear() and redraw() methods which can (and usually should) be
        overridden by child classes. 

      - the set_mouse_mode() method which defines the mouse mode tool
        to use, for example image navigation, or cropping rectangle
        drawing tools.

      - mouse event handlers that overload mousePressEvent,
        mouseReleaseEvent, mouseMoveEvent, automatically setting these
        methods to call the correct callbacks based on the mouse mode.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = LayeredGraphicsScene(self)
        super(ImageDisplay, self).setScene(self._scene)
        super(LayeredGraphicsScene, self._scene).changed.connect(self.updateScene)
        self.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu

    def get_mouse_mode(self):
        return self._scene.get_mouse_mode()

    def set_mouse_mode(self, mouse_mode):
        print(f'ImageDisplay.set_mouse_mode() #(type(self) -> {type(self)}))')
        self._scene.set_mouse_mode(mouse_mode)

    def create_layer(self, layer):
        """This function takes any object with a 'set_scene()' method and
        calls this function with the QGraphicsScene object contained
        within this object. It then returns the layer object. The
        purpose is to use it like so:

            class MyDisplay(ImageDisplay):
                def __init__(self):
                    self.some_layer_obj = self.create_layer(SomeLayerObject(None))

        This function does NOT store any of the layers given to it in
        any internal state. It is up to the child that inherits this
        class to keep track of it's own layers.
        """
        print(f'ImageDisplay.create_layer() #(type(layer) -> {type(layer)})')
        layer.set_scene(self.get_scene())
        return layer

    def get_scene(self):
        return self._scene

    def set_scene(self, scene):
        """BE WARNED that this function will not set all of the scenes that
        were updated by the 'create_layer()' function. The class that
        inherits this class must overload this function to do that.
        """
        print(f'ImageDisplay.set_scene() #(type(scene) -> {type(scene)})')
        if not isinstance(self.scene, LayeredGraphicsScene):
            self._scene = scene
            super(ImageDisplay, self).setScene(scene)
        else:
            raise ValueError(f'self.scene is not a LayeredGraphicsScene')

    def clear(self):
        self._scene.clear()

    def redraw(self):
        self._scene.redraw()

class LayeredGraphicsScene(qt.QGraphicsScene):
    """This class provides a simplified wrapper around a QGraphicsScene
    with a "mouse mode" object that can be set to enable different
    "mousePressEvent()", "mouseMoveEvent()", and "mouseReleaseEvent()"
    handlers. There is no need to overload these methods, simply
    setting the mouse mode object using the "set_mouse_mode()" is good
    enough.

      - the set_mouse_mode() method which defines the mouse mode tool
        to use, for example image navigation, or cropping rectangle
        drawing tools.

      - mouse event handlers that overload mousePressEvent,
        mouseReleaseEvent, mouseMoveEvent, automatically setting these
        methods to call the correct callbacks based on the mouse mode.
    """

    def __init__(self, graphics_view, mouse_mode=None):
        super(LayeredGraphicsScene, self).__init__(graphics_view)
        self.mouse_mode = mouse_mode
        self.layers = []
        self.drop_handler = None

    def get_mouse_mode(self):
        return self.mouse_mode

    def set_mouse_mode(self, mouse_mode):
        # TODO: do some basic type checking here
        self.mouse_mode = mouse_mode

    def set_drop_handler(self, handler):
        """This function enables drag-drop events on the scene and sets a
        handler for them. You can pass None to disable drag-drop events."""
        self.drop_handler = handler
        self.setAcceptDrops(handler is not None)

    def redraw(self):
        for layer in self.layers:
            layer.redraw()

    def clear(self):
        for layer in self.layers:
            layer.clear
        super(LayeredGraphicsScene, self).clear()

    def mousePressEvent(self, event):
        #print(f"ReferenceImageScene.mousePressEvent({event})") #DEBUG
        if self.mouse_mode and left_mouse_button(event):
            self.mouse_mode.mousePressEvent(event)
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        #print(f"ReferenceImageScene.mouseReleaseEvent({event})") #DEBUG
        if self.mouse_mode and left_mouse_button(event):
            self.mouse_mode.mouseReleaseEvent(event)
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        #print(f"ReferenceImageScene.mouseMoveEvent({event})") #DEBUG
        if self.mouse_mode and left_mouse_button(event):
            self.mouse_mode.mouseMoveEvent(event)
        else:
            event.ignore()

    def dropEvent(self, event):
        if self.drop_handler is not None:
            self.drop_handler(event)
        else:
            event.ignore()
