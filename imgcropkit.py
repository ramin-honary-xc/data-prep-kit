#! /usr/bin/env python3

import sys
import os
import os.path
import re
from pathlib import (PurePath, Path)
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

def check_param(label, param, gte, lte):
    """This function is used mostly when setting arguments taken from the
    GUI. It raises a ValueError if the parameter is out of the bounds
    given by 'gte' and 'lte', the GUI even handler needs to catch this
    and report the error to the user."""
    if gte <= param and param <= lte:
        pass
    else:
        raise ValueError(
            f'Parameter "{label}" must be greater/equal to {gte} and less/equal to {lte}'
          )

################################################################################

class ImagePreview(qt.QGraphicsView):
    """This is a QGraphicsView that displays an image. Images are loaded
    by filepath."""

    def __init__(self, parent, app_model):
        super(ImagePreview, self).__init__(parent)
        self.app_model = app_model
        self.preview_scene = qt.QGraphicsScene(self)
        self.display_pixmap = None
        self.display_pixmap_item = None
        self.crop_rect_item = None
        self.current_item = None
        self.setViewportUpdateMode(4) # 4: QGraphicsView::BoundingRectViewportUpdate
        self.setResizeAnchor(1) # 1: QGraphicsView::AnchorViewCenter
        self.setScene(self.preview_scene)
        self.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu
        self.crop_rect_pen = qgui.QPen(qgui.QColor(255, 0, 0))
        self.crop_rect_pen.setCosmetic(True)
        self.crop_rect_pen.setWidth(3)

    def resizeEvent(self, newSize):
        super(ImagePreview, self).resizeEvent(newSize)
        if self.display_pixmap is not None:
            self.fitInView(self.display_pixmap_item, 1) # 1: qcore.AspectRatioMode::KeepAspectRatio

    def set_display_item(self, item):
        """This function takes a FileListItem and displays it in the scene. If
        the given item is already set as the current display item, it
        will update the crop rect visualization."""
        print(f'ImagePreview.display_item({item})')
        if (item is not None) and (item is self.current_item):
            self.resetTransform()
            if self.crop_rect_item is not None:
                rect = item.get_crop_rect()
                rect = qcore.QRectF(*rect)
                self.crop_rect_item.setRect(rect)
                self.setSceneRect(rect)
            else:
                rect = item.get_crop_rect()
                rect = qcore.QRectF(*rect)
                self.crop_rect_item = self.preview_scene.addRect(rect, self.crop_rect_pen)
                self.setSceneRect(rect)
        else:
            self.current_item = item
            self.preview_scene.clear()
            self.resetTransform()
            if item is not None:
                image_with_orb = item.get_image_with_orb()
                if image_with_orb is not None:
                    image_with_orb.set_relative_crop_rect( \
                        self.app_model.get_reference_image(), \
                        self.app_model.get_orb_config(), \
                      )
                else:
                    pass
                path = str(item.get_filepath())
                print(f'ImagePreview #(load image for preview "{path}")')
                self.display_pixmap = qgui.QPixmap(path)
                self.display_pixmap_item = qt.QGraphicsPixmapItem(self.display_pixmap)
                self.preview_scene.addItem(self.display_pixmap_item)
                rect = item.get_crop_rect()
                if rect is not None:
                    rect = qcore.QRectF(*rect)
                    self.setSceneRect(rect)
                    self.crop_rect_item = self.preview_scene.addRect(rect, self.crop_rect_pen)
                else:
                    print(f'ImagePreview #(scene rect not set, no crop rect defined for item)')
                    size = self.display_pixmap.size()
                    self.setSceneRect(0, 0, size.width(), size.height())
            else:
                print(f'ImagePreview.set_display_item(None)')


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
    """This is the scene controller used to manage mouse events on the
    image view and allows the user to draw a crop rectangle over the
    image. This class is the view and controller for the ImageWithORB
    model.
    """

    def __init__(self, app_model):
        super(ReferenceImageScene, self).__init__()
        self.app_model = app_model
        # We keep a copy of the current reference image. If any part
        # of this view changes, the model reference image is compared
        # to the cached image, if anything has changed, the view is
        # redrawn.
        self.cached_image = app_model.get_reference_image()
        self.pixmap = None
        self.pixmap_item = None
        self.graphics_view = None
        self.crop_rect_pen = qgui.QPen(qgui.QColor(255, 0, 0))
        self.crop_rect_pen.setCosmetic(True)
        self.crop_rect_pen.setWidth(3)
        self.keypoint_pen = qgui.QPen(qgui.QColor(0, 255, 0))
        self.keypoint_pen.setWidth(1)
        self.keypoint_pen.setCosmetic(True)
        self.event_handler = CropRectTool(self, app_model)
        self.set_display_reference(self.app_model.get_reference_image())

    def set_crop_rect(self, rect):
        """Takes a QRectF, immediately update the crop_rect in the current
        cached_image if it exists. Also update the crop_rect view at
        the same time.
        """
        if self.cached_image is not None:
            self.cached_image.set_crop_rect(rect)
            self._draw_crop_rect(self.cached_image)
        else:
            print('#(ReferenceImageScene.set_crop_rect() failed, no cached image)')

    def get_crop_rect(self):
        if self.cached_image:
            return self.cached_image.get_crop_rect()
        else:
            return None

    def set_graphics_view(self, graphics_view):
        """The graphics view is created after this ReferenceImageScene object,
        but we still need a reference to it to respond to certain
        events that may trigger changes on the view. This function
        should be called only once in the constructor of the widget
        that contains this scene, and it should be called with the
        QGraphicsView once it has been constructed.
        """
        self.graphics_view = graphics_view

    def set_display_reference(self, orb_image):
        """Takes an ImageWithORB object, if it is different from the
        cached_image, the reset_view() is called."""
        if orb_image is None:
            self.clear()
            self.cached_image is None
            self.pixmap = None
            self.pixmap_item = None
        else:
            print(f'ReferenceImageScene.set_display_reference({str(orb_image.get_filepath())})')
            if self.cached_image is None:
                self.clear()
                self._draw_pixbuf(orb_image)
            else:
                # Here we know either the crop_rect or keypoints set (or
                # both) have changed, but not the QPixmap. In this case,
                # we need to protect the QPixmap from being deleted by
                # removing it from the QGraphicsScene before we call
                # clear().
                if self.cached_image.get_filepath() == orb_image.get_filepath():
                    orb_config = orb_image.get_orb_config()
                    if self.cached_image.get_orb_config() != orb_config:
                        self.removeItem(self.pixmap_item)
                        self.clear()
                        self.addItem(self.pixmap_item)
                    else:
                        self._draw_crop_rect(orb_image)
                        return
                else:
                    self.clear()
                    self._draw_pixbuf(orb_image)
            self._draw_keypoints(orb_image)
            self._draw_crop_rect(orb_image)
            self.cached_image = orb_image

    def get_reference_pixmap_item(self):
        """In order to set the bounds of the QGraphicsView, the parent needs
        access to the QPixmapItem of this class."""
        return self.pixmap_item

    def _draw_pixbuf(self, orb_image):
        """This function assumes the self.cached_image is not None."""
        filepath = orb_image.get_filepath()
        if filepath is not None:
            self.pixmap = qgui.QPixmap(str(filepath))
            self.pixmap_item = qt.QGraphicsPixmapItem(self.pixmap)
            self.addItem(self.pixmap_item)
            print("ReferenceImageScene #(inserted reference pixmap item into scene)")
        else:
            self.pixmap = None
            self.pixmap_item = None

    def _draw_keypoints(self, orb_image):
        keypoints = orb_image.get_keypoints()
        if keypoints is not None:
            print(f'ReferenceImageScene #(number of keypoints -> {len(keypoints)})')
            for key in keypoints:
                (x, y) = key.pt
                self.addRect(qcore.QRectF(x, y, 2, 2), self.keypoint_pen)
        else:
            print(f'ReferenceImageScene #(keypoints not defined)')

    def _draw_crop_rect(self, orb_image):
        rect = orb_image.get_crop_rect()
        if rect is not None:
            rect = qcore.QRectF(*rect)
            if self.rect_view is None:
                self.rect_view = \
                    qt.QGraphicsRectItem(rect, self.crop_rect_pen, qt.QBrush())
            else:
                self.rect_view.setRect(rect)
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

    def __init__(self, image_with_orb):
        super(FileListItem, self).__init__(str(image_with_orb.get_filepath()))
        self.image_with_orb = image_with_orb

    def get_image_with_orb(self):
        return self.image_with_orb

    def get_crop_rect(self):
        return self.image_with_orb.get_crop_rect()

    def get_keypoints(self):
        return self.image_with_orb.get_keypoints()

    def get_filepath(self):
        return self.image_with_orb.get_filepath()

    def crop_and_save(self, output_dir):
        self.image_with_orb.crop_and_save(output_dir)

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
        self.image_preview  = ImagePreview(self, self.app_model)
        self.image_preview.setObjectName('FilesTab ImagePreview')
        self.splitter.addWidget(self.list_widget)
        self.splitter.addWidget(self.image_preview)
        self.layout.addWidget(self.splitter)
        self.display_pixmap_path = None
        #---------- Populate list view ----------
        self.reset_paths_list()
        #---------- Setup context menus ----------
        # ## Action: Use as pattern
        # self.use_as_pattern = qt.QAction("Use as pattern", self)
        # self.use_as_pattern.setShortcut(qgui.QKeySequence.Find)
        # self.use_as_pattern.triggered.connect(self.use_current_item_as_pattern)
        # self.list_widget.addAction(self.use_as_pattern)
        # self.image_preview.addAction(self.use_as_pattern)
        ## Action: Search within this image
        self.use_as_refimg_action = qt.QAction("Search within this image", self)
        self.use_as_refimg_action.setShortcut(qgui.QKeySequence.InsertParagraphSeparator)
        self.use_as_refimg_action.triggered.connect(self.activate_selected_item)
        self.list_widget.addAction(self.use_as_refimg_action)
        self.image_preview.addAction(self.use_as_refimg_action)
        ## Action: open image files
        self.open_image_files = qt.QAction("Open image files", self)
        self.open_image_files.setShortcut(qgui.QKeySequence.Open)
        self.open_image_files.triggered.connect(self.open_image_files_handler)
        self.list_widget.addAction(self.open_image_files)
        self.image_preview.addAction(self.open_image_files)
        ## Action: save image files
        self.save_image_action = qt.QAction("Crop and save this image", self)
        self.save_image_action.setShortcut(qgui.QKeySequence.Save)
        self.save_image_action.triggered.connect(self.do_save_image)
        self.list_widget.addAction(self.save_image_action)
        self.image_preview.addAction(self.save_image_action)
        ## Action: save all image files
        self.save_all_images_action = qt.QAction("Crop and save this image", self)
        self.save_all_images_action.setShortcut(qgui.QKeySequence.SaveAs)
        self.save_all_images_action.triggered.connect(self.do_save_all_images)
        self.list_widget.addAction(self.save_all_images_action)
        self.image_preview.addAction(self.save_all_images_action)
        #---------- Connect signal handlers ----------
        self.list_widget.currentItemChanged.connect(self.item_change_handler)
        self.list_widget.itemActivated.connect(self.activate_handler)

    def get_current_item(self):
        return self.list_widget.currentItem()

    def activate_handler(self, item):
        self.use_item_as_reference(item)

    def activate_selected_item(self):
        self.activate_handler(self.get_current_item())

    def item_change_handler(self, item, _old):
        if item is not None:
            print(f'FilesTab.item_change_handler({item.get_filepath()})')
            self.image_preview.set_display_item(item)
        else:
            print('FilesTab.item_change_handler(item=None)')

    def use_current_item_as_reference(self):
        item = self.list_widget.currentItem()
        self.use_item_as_pattern(item)

    def use_item_as_reference(self, item):
        image_with_orb = item.get_image_with_orb()
        self.app_model.set_reference_image(image_with_orb)
        self.app_view.reset_reference_image()
        self.app_view.change_to_reference_tab()

    def reset_paths_list(self):
        """Populate the list view with an item for each file path."""
        self.list_widget.clear()
        item_list = self.app_model.get_image_list()
        for item in item_list:
            self.list_widget.addItem(FileListItem(item))

    def add_image_list(self, images):
        self.app_model.add_image_list(images)
        self.reset_paths_list()

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

    def modal_prompt_get_directory(self, init_dir):
        output_dir = \
            qt.QFileDialog.getExistingDirectory( \
                self, "Write images to directory", \
                init_dir, \
                qt.QFileDialog.ShowDirsOnly \
          )
        return PurePath(output_dir)

    def do_save_image(self):
        item = self.get_current_item()
        if item is not None:
            output_dir = self.modal_prompt_get_directory(None)
            item.crop_and_save(output_dir)
        else:
            print(f'#(cannot save, no item selected)')

    def do_save_all_images(self):
        output_dir = self.modal_prompt_get_directory(None)
        self.app_model.crop_and_save_all(output_dir)

    def update_crop_rect_item(self):
        """Update the crop rectangle in the scene. This will inspect the
        app_model.crop_rect to see if it has changed and update the
        scene if so."""
        item = self.list_widget.currentItem()
        self.image_preview.set_display_item(item)

    def focusInEvent(self, _event):
        """Here the focusInEvent is overridden, but the parent method is also
        called. If the app_model has been changed (in particular, the
        crop_rect) while the ReferenceImageTab was visible, this tab
        also needs to update it's view.
        """
        print(f'FilesTab.focusInEvent()')
        self.update_crop_rect_item()
        super(FilesTab, self).focusInEvent(event)

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

    def set_display_reference(self, orb_image):
        self.scene.set_display_reference(orb_image)

    def reset_reference_image(self):
        orb_image = self.app_model.get_reference_image()
        if orb_image is not None:
            self.set_display_reference(orb_image)
        else:
            print(f'ReferenceImageTabe.reset_reference_image() #(no reference orb_image)')

################################################################################

class ConfigTab(qt.QWidget):
    """This appears as a tab in the GUI where you can set the
    configuration options that tweak the settings for the ORB algorithm."""

    def __init__(self, app_model, parent):
        super(ConfigTab, self).__init__(parent)
        self.app_view = parent
        self.app_model = app_model
        self.orb_config = ORBConfig()
        self.orb_config_undo = []
        self.orb_config_redo = []
        self.notify = qt.QErrorMessage(self)
        ##-------------------- The text fields --------------------
        self.fields = qt.QWidget(self)
        self.nFeatures = qt.QLineEdit(str(self.orb_config.get_nFeatures()))
        self.nFeatures.editingFinished.connect(self.check_nFeatures)
        self.scaleFactor = qt.QLineEdit(str(self.orb_config.get_scaleFactor()))
        self.scaleFactor.editingFinished.connect(self.check_scaleFactor)
        self.nLevels = qt.QLineEdit(str(self.orb_config.get_nLevels()))
        self.nLevels.editingFinished.connect(self.check_nLevels)
        self.edgeThreshold = qt.QLineEdit(str(self.orb_config.get_edgeThreshold()))
        self.edgeThreshold.editingFinished.connect(self.check_edgeThreshold)
        #self.firstLevel = qt.QLineEdit(str(self.orb_config.get_firstLevel()))
        self.WTA_K = qt.QLineEdit(str(self.orb_config.get_WTA_K()))
        self.WTA_K.editingFinished.connect(self.check_WTA_K)
        self.patchSize = qt.QLineEdit(str(self.orb_config.get_patchSize()))
        self.patchSize.editingFinished.connect(self.check_patchSize)
        self.fastThreshold = qt.QLineEdit(str(self.orb_config.get_fastThreshold()))
        self.fastThreshold.editingFinished.connect(self.check_fastThreshold)
        ## -------------------- the form layout --------------------
        self.form_layout = qt.QFormLayout(self.fields)
        self.form_layout.setFieldGrowthPolicy(qt.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form_layout.setLabelAlignment(qcore.Qt.AlignmentFlag.AlignRight)
        self.form_layout.setFormAlignment(qcore.Qt.AlignmentFlag.AlignLeft)
        self.form_layout.addRow('Number of Features (>20, <20000)', self.nFeatures)
        self.form_layout.addRow('Number of Levels (>1, <64)', self.nLevels)
        self.form_layout.addRow('Scale Factor (>1.0, <2.0)', self.scaleFactor)
        self.form_layout.addRow('Edge Threshold (>2, <1024)', self.edgeThreshold)
        self.form_layout.addRow('Patch Size (>2, <1024)', self.patchSize)
        self.form_layout.addRow('WTA Factor (>2, <4)', self.WTA_K)
        self.form_layout.addRow('FAST Threshold (>2, <100)', self.fastThreshold)
        ## -------------------- Control Buttons --------------------
        self.buttons = qt.QWidget(self)
        self.button_layout = qt.QHBoxLayout(self.buttons)
        self.defaults_button = qt.QPushButton('Defaults')
        self.defaults_button.clicked.connect(self.reset_defaults_action)
        self.redo_button = qt.QPushButton('Redo')
        self.redo_button.clicked.connect(self.redo_action)
        self.undo_button = qt.QPushButton('Undo')
        self.undo_button.clicked.connect(self.undo_action)
        self.apply_button = qt.QPushButton('Apply')
        self.apply_button.clicked.connect(self.apply_changes_action)
        self.button_layout.addWidget(self.defaults_button)
        self.button_layout.addWidget(self.redo_button)
        self.button_layout.addWidget(self.undo_button)
        self.button_layout.addWidget(self.apply_button)
        self.after_update()
        ## -------------------- Layout --------------------
        self.whole_layout = qt.QVBoxLayout(self)
        self.whole_layout.addWidget(self.fields)
        self.whole_layout.addWidget(self.buttons)
        self.whole_layout.addStretch()

    def update_field(self, field, fromStr, setter):
        """This function takes a qt.QLineEdit 'field', a function to convert
        it's text to a value to config parameter data, and a 'setter'
        function that sets the value taken from the field. It is
        expected that the 'setter' can raise a ValueError exception if
        the value given cannot be set. This function catches the
        exception and notifies the end user.
        """
        try:
            setter(fromStr(field.text()))
        except ValueError as e:
            self.notify.showMessage(e.args[0])

    def check_nFeatures(self):
        self.update_field(self.nFeatures, int, self.orb_config.set_nFeatures)

    def check_scaleFactor(self):
        self.update_field(self.scaleFactor, float, self.orb_config.set_scaleFactor)

    def check_nLevels(self):
        self.update_field(self.nLevels, int, self.orb_config.set_nLevels)

    def check_edgeThreshold(self):
        self.update_field(self.edgeThreshold, int, self.orb_config.set_edgeThreshold)

    def check_WTA_K(self):
        self.update_field(self.WTA_K, int, self.orb_config.set_WTA_K)

    def check_patchSize(self):
        self.update_field(self.patchSize, int, self.orb_config.set_patchSize)

    def check_fastThreshold(self):
        self.update_field(self.fastThreshold, int, self.orb_config.set_fastThreshold)

    def after_update(self):
        self.redo_button.setEnabled(len(self.orb_config_redo) != 0)
        self.undo_button.setEnabled(len(self.orb_config_undo) != 0)

    def apply_changes_action(self):
        self.check_nFeatures()
        self.check_scaleFactor()
        self.check_nLevels()
        self.check_edgeThreshold()
        self.check_WTA_K()
        self.check_patchSize()
        self.check_fastThreshold()
        self.push_do(self.orb_config_undo)
        self.app_model.set_orb_config(self.orb_config)
        self.after_update()
        if self.app_model.get_reference_image() is not None:
            self.app_view.reset_reference_image()
            self.app_view.change_to_reference_tab()

    def reset_defaults_action(self):
        self.push_do(self.orb_config_undo)
        self.orb_config = ORBConfig()

    def push_do(self, stack):
        """Pass 'self.orb_config_undo' or 'self.orb_config_redo' as the 'stack' argument."""
        if (len(stack) <= 0) or (stack[-1] != self.orb_config):
            stack.append(self.orb_config)
        else:
            pass

    def shift_do(self, forward, reverse):
        print(f'#(len(forward) -> {len(forward)}, len(reverse) -> {len(reverse)})')
        if len(forward) > 0:
            self.push_do(reverse)
            self.orb_config = forward[-1]
            self.orb_config = forward[0:-1]
            self.apply_changes_action()
        else:
            print(f'#(cannot undo/redo, reached end of stack)')

    def undo_action(self):
        self.shift_do(self.orb_config_undo, orb_config_redo)

    def redo_action(self):
        self.shift_do(self.orb_config_redo, orb_config_undo)


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
        self.config_tab = ConfigTab(app_model, self)
        self.addTab(self.files_tab, "Search")
        self.addTab(self.reference_image_tab, "Reference")
        self.addTab(self.config_tab, "Settings")
        self.currentChanged.connect(self.change_tab_handler)

    def set_display_reference(self, orb_image):
        self.reference_image_tab.set_display_reference(orb_image)
        self.files_tab.update_crop_rect_current_item()
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

    def reset_reference_image(self):
        ref = self.app_model.get_reference_image()
        if ref is not None:
            self.reference_image_tab.set_display_reference(ref)
            self.reference_image_tab.reset_reference_image()
        else:
            pass


################################################################################

class ImageWithORB():
    """This class defines an image object, provides an API to run ORB on
    the image, and to associate the ORB keypoints with the image."""

    def __init__(self, filepath):
        if isinstance(filepath, str):
            filepath = PurePath(filepath)
        elif not isinstance(filepath, PurePath):
            raise ValueError( \
                f'ImageWithORB.crop_and_save() method argument output_dir not a PurePath value'
              )
        else:
            pass
        self.filepath = filepath
        self.orb_config = ORBConfig()
        self.ORB = None
        self.keypoints = None
        self.descriptors = None
        self.midpoint = None
        self.init_crop_rect = None
        self.crop_rect = None

    def __hash__(self):
        return hash(self.filepath)

    def __getitem__(self, i):
        return self.keypoints[i]

    def __len__(self):
        return len(self.keypoints)

    def __str__(self):
        return str(self.filepath)

    def __eq__(self, a):
        return \
            (self.filepath == a.filepath) and \
            (self.orb_config == a.orb_config)

    def __ne__(self, a):
        return not self.__eq__(a)

    def get_orb_config(self):
        return self.orb_config

    def set_orb_config(self, orb_config):
        self.run_orb(orb_config)

    def get_filepath(self):
        return self.filepath

    def get_keypoints(self):
        return self.keypoints

    def get_midpoint(self):
        return self.midpoint

    def get_ORB(self):
        return self.ORB

    def get_descriptors(self):
        return self.descriptors

    def get_crop_rect(self):
        return self.crop_rect

    def get_midpoint(self):
        return self.midpoint

    def set_midpoint(self, midpoint):
        """The midpoint must be an (x,y) tuple"""
        self.midpoint = midpoint

    def set_midpoint(self, x, y):
        self.midpoint = (x, y)

    def get_crop_rect(self):
        """The crop rect is a 4-tuple (x, y, width, height)"""
        return self.crop_rect

    def set_crop_rect(self, rect):
        """The crop rect must be a 4-tuple (x, y, width, height). This
        function should be called when the end user draws a new crop
        rectangle on the "Reference" image view. Use
        "set_relative_crop_rect()" to compute the crop_rect relative to
        the keypoints found by the ORB algoirhtm.
        """
        self.crop_rect = rect

    def set_relative_crop_rect(self, ref, orb_config):
        """Compute the crop_rect for this item relative to a given reference item."""
        if ref is not None:
            print(f'ImageWithORB.relative_crop_rect({ref.get_crop_rect()})')
            ref_rect = ref.get_crop_rect()
            ref_midpoint = ref.get_midpoint()
            if (ref_rect is not None) and (ref_midpoint is not None):
                self.run_orb(orb_config)
                (ref_x, ref_y, ref_width, ref_height) = ref_rect
                (mid_x, mid_y) = ref_midpoint
                if self.midpoint is not None:
                    (x, y) = self.midpoint
                    self.crop_rect = \
                      ( ref_x - mid_x + x , \
                        ref_y - mid_y + y, \
                        ref_width, \
                        ref_height, \
                      )
                    print(f'ImageWithORB.relative_crop_rect({ref_rect}) -> {self.crop_rect}')
                else:
                    print(f'#(ImageWithORB.set_relative_crop_rect() #())')
            else:
                print(f'ImageWithORB.set_relative_crop_rect() #(crop_rect={ref_rect}, midpoint={ref_midpoint})')
        else:
            print(f'ImageWithORB.relative_crop_rect(None)')

    def reset_crop_rect(self):
        """If the "self.reference_image" is set, you can reset the crop rect to
        the exact size of the "self.reference_image" by calling this function."""
        self.crop_rect = self.init_crop_rect

    def run_orb(self, orb_config):
        print(f"#(old config: {str(self.orb_config)})")
        print(f"#(new config: {str(orb_config)})")
        print(f"#(up to date? {(self.orb_config == orb_config)})")
        if (self.ORB is None) or (self.orb_config != orb_config):
            self.force_run_orb(orb_config)
        else:
            print(f'ImageWithOrb.run_orb() #(ORB metadata already exists and is up-to-date)')
            pass

    def force_run_orb(self, orb_config):
        path = str(self.filepath)
        pixmap = cv.imread(path, cv.IMREAD_GRAYSCALE)
        if pixmap is not None:
            # Set the init_crop_rect
            height, width = pixmap.shape
            self.init_crop_rect = (0, 0, width, height)
            # Run the ORB algorithm
            print(f'ImageWithOrb.force_run_orb({str(orb_config)})')
            ORB = cv.ORB_create( \
                nfeatures=orb_config.get_nFeatures(), \
                scaleFactor=orb_config.get_scaleFactor(), \
                nlevels=orb_config.get_nLevels(), \
                edgeThreshold=orb_config.get_edgeThreshold(), \
                firstLevel=orb_config.get_firstLevel(), \
                WTA_K=orb_config.get_WTA_K(), \
                scoreType=orb_config.get_scoreType(), \
                patchSize=orb_config.get_patchSize(), \
                fastThreshold=orb_config.get_fastThreshold(), \
              )
            keypoints, descriptor = ORB.detectAndCompute(pixmap, None)
            self.ORB = ORB
            self.orb_config = orb_config
            self.keypoints = keypoints
            self.descriptor = descriptor
            num_points = len(self.keypoints)
            print(f'#(generated {num_points} keypoints)')
            x_sum = 0
            y_sum = 0
            for key in self.keypoints:
                (x, y) = key.pt
                x_sum = x_sum + x
                y_sum = y_sum + y
            if num_points > 0:
                self.set_midpoint(x_sum / num_points, y_sum / num_points)
            else:
                print(f'#(cannot find center of mass for zero points)')
                self.midpoint = None
        else:
            print(f'#(failed to load pixmap for path {path}')

    def crop_and_save(self, output_dir):
        if self.crop_rect is not None:
            pixmap = cv.imread(str(self.filepath))
            if pixmap is not None:
                path = PurePath(output_dir) / self.filepath.name
                (x_min, y_min, width, height) = self.crop_rect
                x_max = round(x_min + width)
                y_max = round(y_min + height)
                x_min = round(x_min)
                y_min = round(y_min)
                print(
                    f'ImageWithORB.crop_and_save("{str(path)}") -> '
                    f'x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max})' \
                  )
                cv.imwrite(str(path), pixmap[ y_min:y_max , x_min:x_max ])
            else:
                raise ValueError( \
                    f'ImageWithORB("{str(self.filepath)}") failed to load file path as image' \
                  )
        else:
            raise ValueError( \
                f'ImageWithORB("{str(self.filepath)}").crop_and_save() failed,'
                f' undefined "crop_rect" value' \
              )

class ORBConfig():
    """This data type contains values used to parameterize the ORB feature
    selection algorithm. It overrides the equality operator so that we
    can detect when the config has changed, and therefore when we need
    to re-run the ORB algorithm.
    """
    def __init__(self):
        self.nFeatures = 1000
        self.scaleFactor = 1.2
        self.nLevels = 8
        self.edgeThreshold = 31
        self.firstLevel = 0
        self.WTA_K = 2
        self.scoreType = 0 # HARRIS_SCORE (use 1 for FAST_SCORE)
        self.patchSize = 31
        self.fastThreshold = 20

    def __eq__(self, a):
        return (
            (self.nFeatures == a.nFeatures) and \
            (self.scaleFactor == a.scaleFactor) and \
            (self.nLevels == a.nLevels) and \
            (self.edgeThreshold == a.edgeThreshold) and \
            (self.firstLevel == a.firstLevel) and \
            (self.WTA_K == a.WTA_K) and \
            (self.scoreType == a.scoreType) and \
            (self.patchSize == a.patchSize) and \
            (self.fastThreshold == a.fastThreshold) \
          )

    def to_dict(self):
        return \
          { 'nFeatures': self.nFeatures,
            'scaleFactor': self.scaleFactor,
            'nLevels': self.nLevels,
            'edgeThreshold': self.edgeThreshold,
            'firstLevel': self.firstLevel,
            'WTA_K': self.WTA_K,
            'scoreType': self.scoreType,
            'patchSize': self.patchSize,
            'fastThreshold': self.fastThreshold,
          }

    def __str__(self):
        return str(self.to_dict())

    def get_nFeatures(self):
        return self.nFeatures

    def set_nFeatures(self, nFeatures):
        check_param('number of features', nFeatures, 20, 20000)
        self.nFeatures = nFeatures

    def get_scaleFactor(self):
        return self.scaleFactor

    def set_scaleFactor(self, scaleFactor):
        check_param('scale factor', scaleFactor, 1.0, 2.0)
        self.scaleFactor = scaleFactor

    def get_nLevels(self):
        return self.nLevels

    def set_nLevels(self, nLevels):
        check_param('number of levels', nLevels, 2, 32)
        self.nLevels = nLevels
        if self.firstLevel > nLevels:
            self.firstLevel = nLevels
        else:
            pass

    def get_edgeThreshold(self):
        return self.edgeThreshold

    def set_edgeThreshold(self, edgeThreshold):
        check_param('edge threshold', edgeThreshold, 2, 1024)
        self.edgeThreshold = edgeThreshold

    def get_firstLevel(self):
        return self.firstLevel

    def set_firstLevel(self, firstLevel):
        check_param('first level', firstLevel, 0, self.edgeThreshold)
        self.firstLevel = firstLevel

    def get_WTA_K(self):
        return self.WTA_K

    def set_WTA_K(self, WTA_K):
        check_param('"WTA" factor', WTA_K, 2, 4)
        self.WTA_K = WTA_K

    def get_scoreType(self):
        return self.scoreType

    def set_scoreType(self, scoreType):
        self.scoreType = scoreType

    def get_patchSize(self):
        return self.patchSize

    def set_patchSize(self, patchSize):
        check_param("patch size", patchSize, 2, 1024)
        self.patchSize = patchSize

    def get_fastThreshold(self):
        return self.fastThreshold

    def set_fastThreshold(self, fastThreshold):
        check_param('"FAST" threshold', fastThreshold, 2, 100)
        self.fastThreshold = fastThreshold


class MainAppModel():

    """This class creates objects that represents the state of the whole
    application.
    """

    def __init__(self):
        self.crop_rect_updated = False
        self.reference_image = None
        self.set_image_list([])
        self.orb_config = ORBConfig()
        
    def get_crop_rect_updated(self):
        return self.crop_rect_updated

    def get_image_list(self):
        return self.image_list

    def set_image_list(self, list):
        self.image_list = list

    def add_image_list(self, items):
        """Takes a list of file paths or strings, converts them to
        ImageWithORB values, and appends them to the image_list."""
        if isinstance(items, list):
            self.image_list = \
                list(
                    dict.fromkeys(
                        self.image_list + \
                        [ImageWithORB(str(item)) for item in items]
                      )
                  )
        elif isinstance(items, ImageWithORB):
            self.image_list.append(items)
        else:
            raise ValueError(
                f'MainAppModel.add_image_list() expects ImageWithORB or list of ImageWithORB'
              )

    def get_reference_image(self):
        return self.reference_image

    def set_reference_image(self, item):
        """Takes a ImageWithORB item and makes it the reference image. This
        will call reset_all_crop_rects()
        """
        if isinstance(item, PurePath):
            self.reference_image = ImageWithORB(item)
        elif isinstance(item, str):
            self.reference_image = ImageWithORB(item)
        elif isinstance(item, ImageWithORB):
            self.reference_image = item
        else:
            raise ValueError( \
                f'MainAppModel.set_reference_image() expects filepath or '
                f'ImageWithORB, was instead passed argument of type {type(item)}' \
              )
        # Now reset the crop_rect of all items in the image_list
        self.reference_image.run_orb(self.orb_config)

    def get_reference_image_filepath(self):
        return self.reference_image_filepath

    def reload_reference_image(self):
        """Given a filepath, load the filepath using cv.imread() and
        store the result in self."""
        if self.reference_image is not None:
            self.reference_image.run_orb(self.orb_config)
        else:
            print(f'MainAppModel.reload_reference_image() failed, reference_image is None')

    def run_orb(self, orb_config):
        if self.reference_image is not None:
            self.reference_image.run_orb(orb_config)
        else:
            pass

    def get_orb_config(self):
        return self.orb_config

    def set_orb_config(self, orb_config):
        """Here we can change the orb_config, then update the orb_config for
        the current reference_image usnig run_orb(). It is important
        to update do reference_image.run_orb() first because it might
        compare it's own internal orb_config to the
        MainAppModel.orb_config to decide whether to run the ORB
        algorithm again.
        """
        self.run_orb(orb_config)
        self.orb_config = orb_config

    def get_keypoints(self):
        if self.reference_image is not None:
            return self.reference_image.get_keypoints()
        else:
            return None

    def get_descriptor(self):
        return self.reference_image.get_descriptor()

    def set_crop_rect(self, crop_rect):
        """this field is of type (x_pix_offset, y_pix_offset, pix_width, pix_height) or None
        """
        if self.reference_image is not None:
            self.reference_image.set_crop_rect(crop_rect)
            self.crop_rect_updated = True
        else:
            pass

    def get_crop_rect(self):
        """this field is of type (x_pix_offset, y_pix_offset, pix_width, pix_height) or None
        """
        if self.reference_image is not None:
            return self.reference_image.get_crop_rect()
        else:
            return None

    def crop_and_save_all(self, output_dir):
        Path(output_dir).mkdir(exist_ok=True)
        for item in self.image_list:
            item.crop_and_save(output_dir)

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
