import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

class PointCloudLayer():
    """This class is for displaying point clouds as a layer within a
    QGraphicsScene. This class provides a method add_point() which
    draws a single point into the QGraphicsScene. The clear() method
    allows all points to be removed.

    When initializing an ImageFileLayer, it is OK to pass None for the
    first argument only as long as you call the set_scene() method
    after initialization and before any other method of this class is
    evaluated.
    """

    def __init__(self, scene):
        self.scene = scene
        self.keypoint_pen = qgui.QPen(qgui.QColor(0, 255, 0))
        self.keypoint_pen.setWidth(1)
        self.keypoint_pen.setCosmetic(True)
        self.keypoint_items = []

    def set_scene(self, scene):
        self.scene = scene

    def get_scene(self):
        return self.scene

    def add_point(self, x, y):
        """Add a single point to the view."""
        self.keypoint_items.append(
            self.scene.addRect(qcore.QRectF(x, y, 2, 2), self.keypoint_pen)
          )

    def add_points(self, iter):
        """This function requires an iterable be passed as an argument, and
        each item taken from the iterable must provide a method
        'get_point()' which returns a tuple with the X,Y coordinates
        of the point to be added.
        """
        for pt in iter:
            (x,y) = pt.get_point()
            self.add_point(x,y)

    def clear(self):
        for item in self.keypoint_items:
            self.scene.removeItem(item)
        self.keypoint_items = []
