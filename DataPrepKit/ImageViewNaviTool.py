import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

import math

class ImageViewNaviTool():
    """This class allows one to construct a "mouse mode" object for that
    allows the view to move around the image, which applies a
    translation to the transformation matrix of the view. You must
    pass a QGraphicsView object as an argument to construct objects of
    this class.

    When an object of this class is set as the mouse mode of an
    'ImageDisplay', when the end user drags the mouse, the experience
    will be that the image in the view is moving with the mouse cursor
    as though it is moving a sheet of paper with the tip of their
    finger.

    This tool also has it's own sub-modes. You can lock mouse motion
    to the X or Y axis.

    You can also set the zoom sub-mode, which increases or decreases
    the scaling of the image view, rather than the translation.

    """

    def __init__(self, view, view_rect=None):
        self._view = view
        self.view_rect = view_rect
        # This mouse mode can be set such that moving the mouse only
        # updates the X or Y position.
        self._lock_X = False
        self._lock_Y = False
        # When a drag event occurs, the starting point is recorded
        # here. The transform matrix of the current view is also
        # recorded at the start of the drag event because the event
        # will be updating the transform live, and we do not want
        # these upadtes to accumulate, we want to apply them only to
        # an initial transform.
        self._drag_start = None
        self._drag_transform = None
        # The drag update function sets the "sub-mode", it can be set
        # to either the 'translate_submode' or the 'scale_submode'.
        self._drag_update_function = self.__translate_submode

    def lock_to_X(self):
        """Allow motion only along the X (left-right) axis. Up-down motion
        becomes impossible."""
        self._lock_X = True
        self._lock_Y = False

    def lock_to_Y(self):
        """Allow motion only along the Y (up-down) axis. Left-right motion
        becomes impossible."""
        self._lock_X = False
        self._lock_Y = True

    def unlock_XY(self):
        """Remove any locking set by 'lock_to_X()' or 'lock_to_Y()'."""
        self._lock_X = False
        self._lock_Y = False

    def set_translate_submode(self):
        """Switch the sub-mode of this tool to translation mode, where mouse
        motion moves the view. This is the default mode. """
        self._drag_update_function = self.__translate_submode

    def set_scale_submode(self):
        """Switch the sub-mode of this tool to translation mode, where mouse
        motion moves the view. This is the default mode. """
        self._drag_update_function = self.__scale_submode

    def view_to_scene_point(self, point):
        """Translate a view point to a scene point."""

    def __translate_submode(self, start, end):
        pass

    def __scale_submode(self, start, end):
        start = self._drag_transform.map(start)
        end = self._drag_transform.map(end)
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        hypotenuse = math.sqrt(dx*dx + dy*dy)
        # TODO: the hypotenuse must be taken as a ratio to the view size.
        hypotenuse = hypotenuse * -1 if dy < 0 else hypotenuse
        temp_transform = self._drag_transform.copy()
        temp_transform.scale(hypotenuse, hypotenuse)
        self._view.setTransform(temp_transform)

    def accept_mouse_events(self):
        return \
            (self.view_rect is not None) and \
            (self._drag_update_function is not Null)

    def mousePressEvent(self, event):
        if self.accept_mouse_events():
            self._drag_start = event.lastScenePos()
            self._drag_transform = self._view.scene().transform()
        else:
            pass

    def mouseMoveEvent(self, event):
        if self.accept_mouse_events() and (self.__drag_start is not None):
            self._drag_update_function(self._drag_start, event.lastScenePos())
        else:
            pass

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        self._drag_transform = None
