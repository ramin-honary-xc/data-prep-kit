import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

class CropRectTool():
    """This class defines event handler functions that are called when the
    tool for selecting the cropping rectangle is selected. Objects of
    this class act directly on a QGraphicsScene object. When the crop
    rectangle is changed, a callback function is called with the new
    rectangle. The constructor of this class takes 2 arguments:

       1. the QGraphicsScene in which the rectangle is visualized

       2. the closure to call with an updated rectangle when a mouse
          drag event comes to an end.

    NOTE: that this tool depends on the QGraphicsScene's sceneRect
    property to be set correctly in order to determine the min/max
    bounds of the cropping rectangle. Be sure that thi this property
    is set to a reasonable value at all times, or mouse events will
    not behave as expected.
    """

    def __init__(self, scene, on_change):
        self.scene = scene
        self.on_change = on_change
        self.start_point = None
        self.end_point = None
        self.crop_rect = None # is updated as the mouse is dragged.
        self.crop_rect_view = None 
        self.crop_rect_pen = qgui.QPen(qgui.QColor(255, 0, 0))
        self.crop_rect_pen.setCosmetic(True)
        self.crop_rect_pen.setWidth(3)

    def mousePressEvent(self, event):
        self.set_start_point(event.lastScenePos())
        event.accept()

    def mouseMoveEvent(self, event):
        self.end_point = event.lastScenePos()
        if self.start_point and self.end_point:
            self.update_rect()
        else:
            pass
        event.accept()

    def mouseReleaseEvent(self, event):
        self.end_point = event.lastScenePos()
        self.update_rect()
        self.on_change(self.crop_rect)
        self.start_point = None
        self.end_point = None
        event.accept()

    def set_start_point(self, point):
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

    def update_rect(self):
        """This function redraws the crop_rect when a mouse drag event
        ends. This function does not triggers the update callback,
        because it is meant to be called on every mouse motion event,
        and the update callback should only be called once the mouse
        motion has stopped and the rectangle size has been decided.
        """
        #TODO: should not depend on ReferenceImageScene. We need to
        # obtain the min/max bounds from some parameter other
        # than get_reference_pixmap_item()
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
            self.crop_rect = (x_min, y_min, x_max-x_min, y_max-y_min,)
            self.redraw()
        else:
            pass

    def get_crop_rect(self):
        return self.crop_rect

    def clear(self):
        self.set_crop_rect(None)

    def set_crop_rect(self, rect):
        """Set the current crop_rect value, and redraw the rectangle in the
        view. The rectangle change callback is not called."""
        self.crop_rect = rect
        self.redraw()

    def redraw(self):
        """This function redraws the crop_rect in the scene view. It usually
        is called in response to mouse-drag events, but is also called
        by draw_reference_crop_rect() when redrawing the view after
        some other part of the view is updated. """
        if self.crop_rect is not None:
            if self.crop_rect_view is not None:
                self.scene.removeItem(self.crop_rect_view)
            else:
                pass
            rect = qcore.QRectF(*(self.crop_rect))
            self.crop_rect_view = self.scene.addRect(rect, self.crop_rect_pen, qgui.QBrush())
        else:
            if self.crop_rect_view is not None:
                self.scene.removeItem(self.crop_rect_view)
            else:
                pass
