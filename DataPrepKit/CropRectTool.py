import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui

def qcolorRepr(qcolor):
    if isinstance(qcolor, qgui.QPen):
        qcolor = qcolor.color()
    else:
        pass
    return f'QColor(r={qcolor.red()}, g={qcolor.green()}, b={qcolor.blue()})'

################################################################################

class CropRectTool():
    """This class creates a tool that can be used with instances of the
    "DataPrepKit.ImageDisplay" class. If your app model contains
    images over which rectangular regions need to be selected, where
    the end user would like to draw rectangles with a mouse to select
    these regions, this class provides the state variables and mouse
    event handler methods to do this. Create an object that
    instantiates this class, or a child of this class, and pass that
    object to the "ImageDisplay.set_mouse_mode()" method, and the
    "ImageDisplay" instance will respond to mouse events and update
    the display with rectangles accordingly.

    "CropRectTool" objects can only draw one rectangle at a time, as
    the end user can only update one rectangle at a time with the
    mouse. However if your app model requires updating many
    rectangles, it is necessary to subclass "CropRectTool" which has
    its own mechanism to switch between which rectanglular regions are
    selected. Then you must overload the following two abstract methods:

      - 'draw_rect_updated()' :: this method is called whenever the
        end user releases the mouse button after drawing a rectangular
        region with the mouse.

      - 'draw_rect_cleared()' :: this method is called when the end
        user clicks the mouse to draw a rectangle, whatever
        rectangular region is currently selected needs to be deleted
        and replaced.

    The constructor of this class requires only one argument: the
    "QGraphicsScene" in which the rectangle is visualized
    NOTE: that this tool depends on the QGraphicsScene's sceneRect
    property to be set correctly in order to determine the min/max
    bounds of the cropping rectangle. Be sure that thi this property
    is set to a reasonable value at all times, or mouse events will
    not behave as expected.

    """

    def __init__(self, scene): #(, on change)
        #super().__init__()
        self.scene = scene
        self.start_point = None
        self.end_point = None
        # The "draw_rect" is the rect currently being updated by mouse drag events.
        self.draw_rect = None
        self.draw_pen = CropRectTool._green_pen

    ###############  Methods specific drawing into the scene  ###############

    def set_scene(self, scene):
        self.scene = scene

    def get_scene(self):
        return self.scene

    ###############  Methods specific to handling pens  ###############

    def region_pen(color, width):
        if not isinstance(color, qgui.QColor):
            raise ValueError('arg 1 must be a QColor')
        elif not isinstance(width, int) and not isinstance(width, float):
            raise ValueError('arg 2 must be a number')
        else:
            pass
        pen = qgui.QPen(color)
        pen.setWidth(width)
        pen.setCosmetic(True)
        return pen

    _red_pen   = region_pen(qgui.QColor(255, 0, 0), 3)
    _green_pen = region_pen(qgui.QColor(0, 255, 0), 3)

    def get_draw_rect_pen(self):
        return self.draw_pen

    def set_draw_pen(self, pen):
        self.draw_pen = pen
        if (self.draw_rect is not None) and (self.draw_pen is not None):
            #print(f'{self.__class__.__name__}.set_draw_rect_pen() #(self.draw_pen = {qcolorRepr(pen.color())}, self.draw_rect is {self.draw_rect.rect()})')
            self.draw_rect.setPen(self.draw_pen)
        else:
            #if pen is not None:
            #    print(f'{self.__class__.__name__}.set_draw_rect_pen() #(self.draw_pen = {qcolorRepr(pen.color())})')
            #else:
            #    pass
            pass

    ###############  Methods specific to event handling  ###############

    def mousePressEvent(self, event):
        self.clear_draw_rect()
        self.set_start_point(event.lastScenePos())
        self.draw_rect_cleared()
        return event.accept()

    def mouseMoveEvent(self, event):
        self.end_point = event.lastScenePos()
        if self.start_point and self.end_point:
            self.update_rect()
        else:
            pass
        return event.accept()

    def mouseReleaseEvent(self, event):
        #print(f'{self.__class__.__name__}.mouseReleaseEvent({event.lastScenePos()!r})')
        self.set_end_point(event.lastScenePos())
        if self.draw_rect is not None:
            qrectf = self.draw_rect.rect()
            rect = (qrectf.x(), qrectf.y(), qrectf.width(), qrectf.height(),)
            self.draw_rect_updated(rect)
            self.clear_draw_rect()
        else:
            pass
        return event.accept()

    def set_start_point(self, point):
        #print(f'{self.__class__.__name__}.set_start_point({point!r})')
        bounds = self.scene.sceneRect()
        if bounds is not None:
            accept = (
                point.x() <= bounds.width() and \
                point.y() <= bounds.height() and \
                point.x() >= 0 and \
                point.y() >= 0 \
              )
            if accept:
                self.start_point = point
                return True
            else:
                self.start_point = None
                return False
        else:
            return False

    def set_end_point(self, point):
        #print(f'{self.__class__.__name__}.set_end_point({point!r})')
        self.end_point = point
        self.update_rect()
        #self.on_change(self.crop_rect)
        self.start_point = None
        self.end_point = None

    def set_draw_rect(self, rect):
        #print(f'{self.__class__.__name__}.set_draw_rect({rect!r})')
        scene = self.get_scene()
        if rect is None:
            self.clear_draw_rect()
        else:
            qrectf = qcore.QRectF(*rect)
            if self.draw_rect is not None:
                self.draw_rect.setRect(qrectf)
            else:
                self.draw_rect = scene.addRect(qrectf, self.draw_pen)

    def clear_draw_rect(self):
        if self.draw_rect is not None:
            #print(f'{self.__class__.__name__}.clear_draw_rect() #(self.draw_rect was {self.draw_rect.rect()!r})')
            scene = self.get_scene()
            scene.removeItem(self.draw_rect)
            self.draw_rect = None
        else:
            #print(f'{self.__class__.__name__}.clear_draw_rect() #(self.draw_rect was None)')
            pass

    def update_rect(self):
        """This function redraws the crop_rect when a mouse drag event
        ends. This function does not triggers the update callback,
        because it is meant to be called on every mouse motion event,
        and the update callback should only be called once the mouse
        motion has stopped and the rectangle size has been decided.
        """
        bounds = self.scene.sceneRect()
        if bounds and self.start_point and self.end_point:
            x_min = min(self.start_point.x(), self.end_point.x())
            y_min = min(self.start_point.y(), self.end_point.y())
            x_max = max(self.start_point.x(), self.end_point.x())
            y_max = max(self.start_point.y(), self.end_point.y())
            x_min = max(x_min, 0)
            y_min = max(y_min, 0)
            x_max = min(x_max, bounds.width())
            y_max = min(y_max, bounds.height())
            rect = (x_min, y_min, x_max-x_min, y_max-y_min,)
            self.set_draw_rect(rect)
            #self.redraw()
        else:
            pass

    def draw_rect_updated(self, rect):
        """This method is called after a mouse drag event that has changed the
        "self.draw_rect" has completed. Overload this method depending
        on the model you are using. """
        #print(f'{self.__class__.__name__}.draw_rect_updated({rect!r})')

    def draw_rect_cleared(self):
        """This method is called after a mouse down event where the end users
        wants to start drawing or re-drawing a rectangle, and the
        rectangle that existed prior needs to be deleted. """
        #print(f'{self.__class__.__name__}.draw_rect_cleared({rect!r})')

    def redraw(self):
        """This function redraws the crop_rect in the scene view. It usually
        is called in response to mouse-drag events, but is also called
        by draw_reference_crop_rect() when redrawing the view after
        some other part of the view is updated. """
        scene = self.get_scene()
        if scene is not None:
            scene.redraw()
        else:
            pass

    def clear(self):
        #print(f'{self.__class__.__name__}.clear()')
        self.clear_draw_rect()
