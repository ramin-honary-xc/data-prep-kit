#! /usr/bin/env python3

import sys
import os
import os.path
import re
from pathlib import PurePath
#import math
#import cv2 as cv
#import numpy as np
#from scipy.signal import argrelextrema

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
            print(f'Failed to load {str(self.display_pixmap_path.get_path())}')


class CropRectTool():
    """This class defines event handler functions that are called when
    the tool for selecting the cropping rectangle is selected.
    """

    def __init__(self, scene, app_model):
        self.scene = scene
        self.app_model = app_model

    def mousePressEvent(self, event):
        rect = self.app_model.get_crop_rect()
        if rect is None:
            rect = qcore.QRectF()
            pt = event.lastScenePos()
            rect.setBottomRight(pt)
            rect.setTopLeft(pt)
        else:
            rect.setTopLeft(event.lastScenePos())
        # Update the app_model.crop_rect
        self.app_model.set_crop_rect(rect)
        self.scene.update_crop_rect_item()
        event.accept()

    def mouseMoveEvent(self, event):
        rect = self.app_model.get_crop_rect()
        if rect is None:
            pass
        else:
            rect.setBottomRight(event.lastScenePos())
            self.app_model.set_crop_rect(rect)
            self.scene.update_crop_rect_item()
        event.accept()


class GeometryScene(qt.QGraphicsScene):
    """This is the scene controller used to manage mouse events on the
    image view and allows the user to draw annotating shapes over the
    image.
    """

    def __init__(self, app_model):
        super(GeometryScene, self).__init__()
        self.app_model = app_model
        self.graphics_view = None
        self.crop_rect_pen = qgui.QColor(255, 0, 0)
        self.event_handler = CropRectTool(self, app_model)
        self.pixmap_item = None
        self.crop_rect_item = None
        self.reset_view()

    def set_graphics_view(self, graphics_view):
        self.graphics_view = graphics_view

    def reset_view(self):
        """Re-read the pixmap from the app_model and prepare to install it
        into the scene.
        """
        pixmap    = self.app_model.get_display_pixmap()
        crop_rect = self.app_model.get_crop_rect()
        self.clear()
        if self.graphics_view is not None:
            self.graphics_view.resetTransform()
        #----------------------------------------
        if pixmap is not None:
            self.pixmap_item = qt.QGraphicsPixmapItem(pixmap)
            self.addItem(self.pixmap_item)
        else:
            self.pixmap_item = None
        #----------------------------------------
        if crop_rect is not None:
            self.crop_rect_item = \
                self.addRect( \
                    crop_rect, \
                    self.crop_rect_pen, \
                    qtgui.QBrush() \
                )
        else:
            self.crop_rect_item = None
        #----------------------------------------

    def update_crop_rect_item(self):
        """Updates the QGraphicsRectItem for the cropping rectangle in this
        scene with the latest value for
        self.app_model.get_crop_rect(). This function is called after
        an event handler updates the cropping rectangle.
        """
        if self.crop_rect_item:
            self.crop_rect_item.setRect(self.app_model.get_crop_rect())
        else:
            pass

    def mousePressEvent(self, event):
        print(f"GeometryScene.mousePressEvent({event})") #DEBUG
        self.event_handler.mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        print(f"GeometryScene.mouseReleaseEvent({event})") #DEBUG
        self.event_handler.mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        print(f"GeometryScene.mouseMoveEvent({event})") #DEBUG
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
        ## Action: Use as pattern
        self.use_as_pattern = qt.QAction("Use as pattern", self)
        self.use_as_pattern.setShortcut(qgui.QKeySequence.Find)
        self.use_as_pattern.triggered.connect(self.use_current_item_as_pattern)
        self.list_widget.addAction(self.use_as_pattern)
        self.image_preview.addAction(self.use_as_pattern)
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
        self.app_view.change_to_geometry_tab()

    def activate_selected_item(self):
        item = self.list_widget.currentItem()
        self.activate_handler(item)

    def item_change_handler(self, item, _old):
        if item is not None:
            self.image_preview.display_path(item.get_path())
        else:
            print('FilesTab.item_change_handler(item=None)')

    def use_current_item_as_pattern(self):
        item = self.list_widget.currentItem()
        path = item.get_path()
        self.app_model.set_selected_image(path)

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
        print(f'selected urls = {urls}')
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

class GeometryTab(qt.QWidget):
    """Display a list of images, and provide an image preview window to
    view each iamge. The set_graphics_view() function MUST be called
    with a QGraphicsView before objects of this class are ever used.
    """

    def __init__(self, app_model, parent):
        super(GeometryTab, self).__init__(parent)
        self.setObjectName('FilesTab')
        #---------- Setup visible widgets ----------
        self.app_model      = app_model
        self.app_view       = parent
        self.scene          = GeometryScene(self.app_model)
        self.image_preview  = qt.QGraphicsView(self.scene)
        self.image_preview.setObjectName('GeometryTab ImagePreview')
        self.scene.set_graphics_view(self.image_preview)
        self.layout         = qt.QHBoxLayout(self)
        self.layout.addWidget(self.image_preview)

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
        self.geometry_tab = GeometryTab(app_model, self)
        self.addTab(self.files_tab, "Search")
        self.addTab(self.geometry_tab, "Pattern")
        self.currentChanged.connect(self.change_tab_handler)

    def change_tab_handler(self, index):
        """Does the work of actually changing the GUI display to the "InspectTab".
        """
        super(ImageCropKit, self).setCurrentIndex(index)
        self.widget(index).update()

    def change_to_files_tab(self):
        self.change_tab_handler(0)

    def change_to_geometry_tab(self):
        self.change_tab_handler(1)

################################################################################

class MainAppModel():
    """This class creates objects that represents the state of the whole
    application.
    """

    def __init__(self):
        self.display_pixmap = None
        self.set_image_list([])
        self.set_shape_list([])
        self.set_selected_image(None)
        self.set_crop_rect(None)

    def set_display_pixmap(self, display_pixmap):
        self.display_pixmap = display_pixmap

    def get_display_pixmap(self):
        return self.display_pixmap

    def set_image_list(self, image_list):
        self.image_list = image_list

    def get_image_list(self):
        return self.image_list

    def set_shape_list(self, shape_list):
        self.shape_list = shape_list

    def get_shape_list(self):
        return self.shape_list

    def set_selected_image(self, selected_image):
         self.selected_image = selected_image

    def get_selected_image(self, selected_image):
         return self.selected_image

    def add_image_list(self, path_list):
        found_paths = search_target_images(path_list)
        self.image_list = self.image_list + found_paths

    def set_crop_rect(self, crop_rect):
        """this field is of type qtcore.QRectF
        """
        self.crop_rect = crop_rect

    def get_crop_rect(self):
        """this field is of type qtcore.QRectF
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
