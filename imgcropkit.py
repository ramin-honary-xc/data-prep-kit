#! /usr/bin/env python3

import sys
import os
import os.path
import re
from pathlib import PurePath
#import math
import cv2 as cv
import numpy as np

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

################################################################################

linebreak = re.compile('[\\n\\r]')

def split_linebreaks(str):
    return linebreak.split(str)

def search_target_images(filepath_args):
    result = []
    for filepath in filepath_args:
        if filepath == '':
            pass
        elif os.path.isdir(filepath):
            for root, _dirs, files in os.walk(filepath):
                root = PurePath(root)
                for filename in files:
                    filepath = PurePath(filename)
                    if filename_filter(filepath):
                        result.append(root / filepath)
                    else:
                        pass
        else:
            result.append(PurePath(filepath))
    return result

################################################################################

class ImagePreview(qt.QGraphicsView):

    def __init__(self, parent):
        super(ImagePreview, self).__init__(parent)
        self.preview_scene = qt.QGraphicsScene(self)
        self.display_pixmap = None
        self.pixmap_item = None
        self.setViewportUpdateMode(4) # 4: QGraphicsView::BoundingRectViewportUpdate
        self.setResizeAnchor(1) # 1: QGraphicsView::AnchorViewCenter
        self.setScene(self.preview_scene)
        self.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu

    def resizeEvent(self, newSize):
        super(ImagePreview, self).resizeEvent(newSize)
        if self.pixmap_item is not None:
            self.fitInView(self.pixmap_item, 1) # 1: qcore.AspectRatioMode::KeepAspectRatio

    def get_pixmap(self):
        return self.display_pixmap

    def set_pixmap(self, pixmap, path=None):
        self.resetTransform()
        self.display_pixmap = pixmap
        self.display_pixmap_path = path
        self.pixmap_item = qt.QGraphicsPixmapItem(self.display_pixmap)
        self.preview_scene.clear()
        #self.preview_scene.setSceneRect(qcore.QRectF())
        self.preview_scene.addItem(self.pixmap_item)
        self.fitInView(self.pixmap_item, 1)

    def display_path(self, path):
        self.display_pixmap_path = path
        self.display_pixmap = qgui.QPixmap()
        if self.display_pixmap.load(str(self.display_pixmap_path)):
            self.set_pixmap(self.display_pixmap)
        else:
            print(f'ImagePreview #(Failed to load {str(self.display_pixmap_path.get_path())})')


class CropRectTool():
    """This class defines event handler functions that are called when
    the tool for selecting the cropping rectangle is selected.
    """

    def __init__(self, scene, app_model):
        self.scene = scene
        self.app_model = app_model
        self.start_point = None
        self.end_point = None
        self.rect = None

    def mousePressEvent(self, event):
        pixmap_item = self.scene.get_reference_pixmap_item()
        bounds = None
        if pixmap_item:
            bounds = pixmap_item.boundingRect()
            point = event.lastScenePos()
            accept = ( \
                point.x() <= bounds.width() and \
                point.y() <= bounds.height() and \
                point.x() >= 0 and \
                point.y() >= 0 \
              )
            if accept:
                self.start_point = point
            else:
                self.start_point = None
        else:
            pass
        event.accept()

    def mouseMoveEvent(self, event):
        self.end_point = event.lastScenePos()
        if self.start_point and self.end_point:
            self.set_crop_rect()
        else:
            pass
        event.accept()

    def mouseReleaseEvent(self, event):
        self.end_point = event.lastScenePos()
        self.set_crop_rect()
        self.app_model.set_crop_rect(self.rect)
        self.start_point = None
        self.end_point = None
        event.accept()

    def set_crop_rect(self):
        pixmap_item = self.scene.get_reference_pixmap_item()
        bounds = None
        if pixmap_item:
            bounds = pixmap_item.boundingRect()
        else:
            pass
        if bounds and self.start_point and self.end_point:
            x_min = min(self.start_point.x(), self.end_point.x())
            y_min = min(self.start_point.y(), self.end_point.y())
            x_max = max(self.start_point.x(), self.end_point.x())
            y_max = max(self.start_point.y(), self.end_point.y())
            x_min = max(x_min, 0)
            y_min = max(y_min, 0)
            x_max = min(x_max, bounds.width())
            y_max = min(y_max, bounds.height())
            self.rect = (x_min, y_min, x_max-x_min, y_max-y_min)
            self.scene.set_crop_rect(qcore.QRectF(*self.rect))
        else:
            pass


class ReferenceImageScene(qt.QGraphicsScene):
    """This is the scene controller used to manage mouse events on the image
    view and allows the user to draw a crop rectangle over the image.
    """

    def __init__(self, app_model):
        super(ReferenceImageScene, self).__init__()
        self.app_model = app_model
        self.reference_filepath = None
        self.reference_pixmap = None
        self.reference_pixmap_item = None
        self.graphics_view = None
        self.crop_rect_pen = qgui.QPen(qgui.QColor(255, 0, 0))
        self.crop_rect_pen.setCosmetic(True)
        self.crop_rect_pen.setWidth(3)
        self.keypoint_pen = qgui.QPen(qgui.QColor(0, 255, 0))
        self.keypoint_pen.setWidth(1)
        self.keypoint_pen.setCosmetic(True)
        self.event_handler = CropRectTool(self, app_model)
        self.pixmap_item = None
        self.crop_rect = None
        self.crop_rect_item = None
        self.reset_view()

    def set_crop_rect(self, rect):
        self.crop_rect = rect
        if self.crop_rect_item is None:
            self.crop_rect_item = self.addRect(self.crop_rect, self.crop_rect_pen)
        else:
            self.crop_rect_item.setRect(self.crop_rect)

    def get_crop_rect(self):
        return self.crop_rect

    def set_graphics_view(self, graphics_view):
        self.graphics_view = graphics_view

    def set_display_reference(self, filepath):
        if filepath is None:
            self.reference_filepath = None
            self.reference_pixmap = None
            self.reference_pixmap_item = None
        else:
            self.reference_pixmap = qgui.QPixmap(str(filepath))
            self.reference_filepath = filepath
            self.reset_view()

    def get_reference_pixmap_item(self):
        return self.reference_pixmap_item

    def reset_view(self):
        """Re-read the pixmap from the app_model and prepare to install it
        into the scene.
        """
        self.clear()
        if self.graphics_view is not None:
            self.graphics_view.resetTransform()
        #----------------------------------------
        if self.reference_pixmap is not None:
            self.reference_pixmap_item = qt.QGraphicsPixmapItem(self.reference_pixmap)
            self.addItem(self.reference_pixmap_item)
            print("ReferenceImageScene #(inserted reference pixmap item into scene)")
        else:
            self.reference_pixmap_item = None
        #----------------------------------------
        rect = self.app_model.get_crop_rect()
        if rect:
            crop_rect = qcore.QRectF(*rect)
        else:
            crop_rect = None
        if crop_rect:
            self.set_crop_rect(crop_rect)
            self.crop_rect_item = self.addRect(crop_rect, self.crop_rect_pen)
        else:
            self.crop_rect_item = None
        #----------------------------------------
        keypoints = self.app_model.get_keypoints()
        if keypoints:
            print(f'ReferenceImageScene #(number of keypoints -> {len(keypoints)})')
            for key in keypoints:
                (x, y) = key.pt
                self.addRect(qcore.QRectF(x, y, 2, 2), self.keypoint_pen)
        else:
            print(f'ReferenceImageScene #(keypoints not defined)')

    def update_crop_rect_item(self):
        """Updates the QGraphicsRectItem for the cropping rectangle in this
        scene with the latest value for
        self.app_model.get_crop_rect(). This function is called after
        an event handler updates the cropping rectangle.
        """
        new_rect = self.app_model.get_crop_rect()
        if self.crop_rect_item and new_rect:
            self.crop_rect_item.setRect(new_rect)
        else:
            pass

    def mousePressEvent(self, event):
        #print(f"ReferenceImageScene.mousePressEvent({event})") #DEBUG
        self.event_handler.mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        #print(f"ReferenceImageScene.mouseReleaseEvent({event})") #DEBUG
        self.event_handler.mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        #print(f"ReferenceImageScene.mouseMoveEvent({event})") #DEBUG
        self.event_handler.mouseMoveEvent(event)


################################################################################

def gather_QUrl_local_files(qurl_list):
    """This function converts a list of URL values of type QUrl into a
    list of PurePaths. It is useful for constructing 'FileListItem's
    from the result of a file dialog selection.
    """
    urls = []
    for url in qurl_list:
        if url.isLocalFile():
            urls.append(PurePath(url.toLocalFile()))
    return urls

class FileListItem(qt.QListWidgetItem):
    """A QListWidgetItem for an element in the files list in the Files tab."""

    def __init__(self, path):
        super(FileListItem, self).__init__(str(path))
        self.path = path

    def get_path(self):
        return self.path


class FilesTab(qt.QWidget):
    """Display a list of images, and provide an image preview window to
    view each iamge.
    """

    def __init__(self, app_model, parent):
        super(FilesTab, self).__init__(parent)
        self.setObjectName('FilesTab')
        #---------- Setup visible widgets ----------
        self.app_model     = app_model
        self.app_view      = parent
        self.layout        = qt.QHBoxLayout(self)
        self.splitter      = qt.QSplitter(1, self)
        self.setAcceptDrops(True)
        self.splitter.setObjectName('FilesTab splitter')
        self.list_widget   = qt.QListWidget(self)
        self.list_widget.setObjectName('FilesTab list_widget')
        self.list_widget.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu
        self.image_preview  = ImagePreview(self)
        self.image_preview.setObjectName('FilesTab ImagePreview')
        self.splitter.addWidget(self.list_widget)
        self.splitter.addWidget(self.image_preview)
        self.layout.addWidget(self.splitter)
        self.display_pixmap_path = None
        #---------- Populate list view ----------
        self.reset_paths_list(self.app_model.get_image_list())
        #---------- Setup context menus ----------
        # ## Action: Use as pattern
        # self.use_as_pattern = qt.QAction("Use as pattern", self)
        # self.use_as_pattern.setShortcut(qgui.QKeySequence.Find)
        # self.use_as_pattern.triggered.connect(self.use_current_item_as_pattern)
        # self.list_widget.addAction(self.use_as_pattern)
        # self.image_preview.addAction(self.use_as_pattern)
        ## Action: Search within this image
        self.do_find_pattern = qt.QAction("Search within this image", self)
        self.do_find_pattern.setShortcut(qgui.QKeySequence.InsertParagraphSeparator)
        self.do_find_pattern.triggered.connect(self.activate_selected_item)
        self.list_widget.addAction(self.do_find_pattern)
        self.image_preview.addAction(self.do_find_pattern)
        ## Action: open image files
        self.open_image_files = qt.QAction("Open image files", self)
        self.open_image_files.setShortcut(qgui.QKeySequence.Open)
        self.open_image_files.triggered.connect(self.open_image_files_handler)
        self.list_widget.addAction(self.open_image_files)
        self.image_preview.addAction(self.open_image_files)
        #---------- Connect signal handlers ----------
        self.list_widget.currentItemChanged.connect(self.item_change_handler)
        self.list_widget.itemActivated.connect(self.activate_handler)

    def get_display_pixmap(self):
        return self.image_preview.get_pixmap()

    def activate_handler(self, item):
        path = item.get_path()
        self.use_path_as_pattern(path)

    def activate_selected_item(self):
        item = self.list_widget.currentItem()
        self.activate_handler(item)

    def item_change_handler(self, item, _old):
        if item is not None:
            self.image_preview.display_path(item.get_path())
        else:
            print('FilesTab.item_change_handler(item=None)')

    def use_path_as_pattern(self, path):
        print(f'FilesTab.use_current_item_as_pattern()')
        print(f'FilesTab -> app_model.set_display_pixmap(None, {path})')
        self.app_model.set_display_pixmap(None, path)
        path = self.app_model.get_display_pixmap_filepath()
        self.app_view.set_display_reference(path)

    def use_current_item_as_pattern(self):
        item = self.list_widget.currentItem()
        path = item.get_path()
        self.use_path_as_pattern(path)

    def reset_paths_list(self, paths_list):
        """Populate the list view with an item for each file path."""
        self.list_widget.clear()
        for item in paths_list:
            self.list_widget.addItem(FileListItem(item))

    def add_image_list(self, list):
        self.app_model.add_image_list(list)
        self.reset_paths_list(self.app_model.get_image_list())

    def open_image_files_handler(self):
        target_dir = os.getcwd()
        urls = \
            qt.QFileDialog.getOpenFileUrls( \
                self, "Open images in which to search for patterns", \
                qcore.QUrl(str(target_dir)), \
                'Images (*.png *.jpg *.jpeg)', '', \
                qt.QFileDialog.ReadOnly, \
                ["file"] \
              )
        print(f'FilesTab #(selected urls = {urls})')
        urls = urls[0]
        if len(urls) > 0:
            self.add_image_list(gather_QUrl_local_files(urls))
        else:
            pass

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls() or mime_data.hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            event.accept()
            self.add_image_list(gather_QUrl_local_files(mime_data.urls()))
        elif mime_data.hasText():
            event.accept()
            self.add_image_list(split_linebreaks(mime_data.text()))
        else:
            event.ignore()

################################################################################

class ReferenceImageTab(qt.QWidget):
    """Display the image used as the reference image, and provide an image
    preview window to view each iamge. It responds to mouse clicks to
    allow end users to define the cropping rectangle. The cropping
    rectangle will be centered around the key points found by the ORB
    algorithm. All other images selected for cropping will also run
    the ORB algorithm, and a similar croppiping rectangle will be
    cenetered around those key points.

    """

    def __init__(self, app_model, parent):
        super(ReferenceImageTab, self).__init__(parent)
        self.setObjectName('FilesTab')
        #---------- Setup visible widgets ----------
        self.app_model      = app_model
        self.app_view       = parent
        self.scene          = ReferenceImageScene(self.app_model)
        self.image_preview  = qt.QGraphicsView(self.scene)
        self.image_preview.setObjectName('ReferenceImageTab ImagePreview')
        self.scene.set_graphics_view(self.image_preview)
        self.scene.changed.connect(self.image_preview.updateScene)
        self.layout         = qt.QHBoxLayout(self)
        self.layout.addWidget(self.image_preview)

    def set_display_reference(self, filepath):
        self.scene.set_display_reference(filepath)


################################################################################

class ImageCropKit(qt.QTabWidget):
    """The Qt Widget containing the GUI for the pattern matching program.
    """

    def __init__(self, app_model, parent=None):
        super(ImageCropKit, self).__init__(parent)
        self.app_model = app_model
        #----------------------------------------
        # Setup the GUI
        self.setWindowTitle('Image Cropp Kit')
        self.resize(800, 600)
        #self.tab_bar = qt.QTabWidget()
        self.setTabPosition(qt.QTabWidget.North)
        self.files_tab = FilesTab(app_model, self)
        self.reference_image_tab = ReferenceImageTab(app_model, self)
        self.addTab(self.files_tab, "Search")
        self.addTab(self.reference_image_tab, "Reference")
        self.currentChanged.connect(self.change_tab_handler)

    def set_display_reference(self, filepath):
        self.reference_image_tab.set_display_reference(filepath)
        self.change_to_reference_tab()

    def change_tab_handler(self, index):
        """Does the work of actually changing the GUI display to the "InspectTab".
        """
        super(ImageCropKit, self).setCurrentIndex(index)
        self.widget(index).update()

    def change_to_files_tab(self):
        self.change_tab_handler(0)

    def change_to_reference_tab(self):
        self.change_tab_handler(1)

################################################################################

class MainAppModel():
    """This class creates objects that represents the state of the whole
    application.
    """

    def __init__(self):
        self.set_display_pixmap(None, None)
        self.set_crop_rect(None)
        self.set_image_list([])
        self.ORB = None
        self.keypoints = None
        self.descriptor = None
        self.match_group = None
        self.bfmatcher = cv.BFMatcher(cv.NORM_HAMMING, crossCheck=True)

    def set_display_pixmap(self, display_pixmap, filepath):
        """takes a pixmap that has been loaded into memory, and the file path
        from which it was loaded. You may pass None as the first
        argument, it will be loaded from the given filepath. You may
        not pass None for the second argument unless the first
        argument is also None.
        """
        print(f'MainAppModel.set_display_pixmap({filepath})')
        if filepath is None:
            if display_pixmap is None:
                self.display_pixmap = None
                self.display_pixmap_filepath = None
            else:
                raise ValueError("if display_pixmap is given, filepath must not be None")
        else:
            self.display_pixmap_filepath = filepath
            if display_pixmap is None:
                self.reload_display_pixmap()
            else:
                self.display_pixmap = display_pixmap
            self.run_orb()

    def get_display_pixmap(self):
        return self.display_pixmap

    def get_display_pixmap_filepath(self):
        return self.display_pixmap_filepath

    def reload_display_pixmap(self):
        """Given a filepath, load the filepath using cv.imread() and
        store the result in self."""
        self.display_pixmap = cv.imread(str(self.display_pixmap_filepath), cv.IMREAD_GRAYSCALE)
        self.run_orb()

    def get_image_list(self):
        return self.image_list

    def set_image_list(self, list):
        self.image_list = list

    def add_image_list(self, items):
        if isinstance(items, list):
            self.image_list = list(dict.fromkeys(self.image_list + items))
        else:
            self.image_list.append(items)

    def run_orb(self):
        """If the display image has been set, create a new ORB for it."""
        print(f'MainAppModel.run_orb()')
        pixmap = self.get_display_pixmap()
        if pixmap is not None:
            ORB = cv.ORB_create()
            keypoints, descriptor = ORB.detectAndCompute(pixmap, None)
            self.ORB = ORB
            self.keypoints = keypoints
            self.descriptor = descriptor
        else:
            print(f'MainAppModel #(failed to run_orb(), pixmap is {pixmap}')

    def get_keypoints(self):
        return self.keypoints

    def get_descriptor(self):
        return self.descriptor

    def run_bfmatcher(self, pixmap):
        """If the display image has been set, create a new bfmatcher for
        it. Pass a second pixmap that has been loaded with cv.imread()
        and then run the cv.BFMatcher.match() function to obtain a
        distance between the two images. Return the distance
        value. The calling context can then decide whether the
        distance is close enuogh to allow a cropping to occur.
        """
        if (self.descriptor is not None) and (self.bfmatcher is not None):
            ORB = cv.ORB_create()
            _keypoints, descriptor = ORB.detectAndCompute(pixmap, None)
            self.match_group = self.bfmatcher.match(self.descriptor, descriptor)
            if self.match_group is not None:
                self.match_group = \
                    cv.sorted( \
                        self.match_group, \
                        key = (lambda feature: feature.distance) \
                      )
        else:
            pass

    def reset_crop_rect(self):
        """If the "self.display_pixmap" is set, you can reset the crop rect to
        the exact size of the "self.display_pixmap" by calling this function."""
        if self.display_pixmap is not None:
            height, width = self.display_pixmap.shape
            self.crop_rect = (0, 0, width, height)

    def set_crop_rect(self, crop_rect):
        """this field is of type (x_pix_offset, y_pix_offset, pix_width, pix_height) or None
        """
        self.crop_rect = crop_rect

    def get_crop_rect(self):
        """this field is of type (x_pix_offset, y_pix_offset, pix_width, pix_height) or None
        """
        return self.crop_rect


################################################################################

def main():
    app_model = MainAppModel()
    app = qt.QApplication(sys.argv)
    app_window = ImageCropKit(app_model)
    app_window.show()
    sys.exit(app.exec_())

################################################################################

if __name__ == '__main__':
    main()
