#! /usr/bin/env python3

import DataPrepKit.utilities as util
import DataPrepKit.FileSet as fs

import argparse
import math
import os
import os.path
import re
import sys
from pathlib import PurePath

import cv2 as cv
import numpy as np
import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

####################################################################################################
# The pattern matcing program

class RegionSize():
    def __init__(self, x, y, width, height):
        self.x_min = x
        self.y_min = y
        self.x_max = x + width
        self.y_max = y + height

    def crop_image(self, image):
        return image[ \
            self.y_min : self.y_max, \
            self.x_min : self.x_max \
          ]

    def as_file_name(self):
        return PurePath(f"{self.x_min:0>5}x{self.y_min:0>5}.png")

    def crop_write_image(self, image, results_dir, file_prefix=None):
        """Takes an image to crop, crops it with 'crop_image()', takes a
        PurePath() 'results_dir', writes the cropped image to the file
        path given by (results_dir/self.as_file_name()) using
        'cv.imwrite()'.
        """
        write_path = self.as_file_name()
        if file_prefix:
            write_path = PurePath(f"{file_prefix!s}_{write_path!s}")
        else:
            pass
        write_path = results_dir / write_path
        print(f"crop_write_image -> {write_path}")
        cv.imwrite(str(write_path), self.crop_image(image))

    def get_point_and_size(self):
        """Return a 4-tuple (x,y, width,height)"""
        return (self.x_min, self.y_min, self.x_max - self.x_min, self.y_max - self.y_min)

#---------------------------------------------------------------------------------------------------

class DistanceMap():
    """Construct DistanceMap() by providing a target image and a pattern
    matching image. For every point in the target image, the
    square-difference distance between the region of pixels at that
    point that overlap the pattern image and the pattern image iteself
    is computed and stored as a Float32 value in a "distance_map"
    image. All images are retained in memory and can be used to
    extract regions of the target image that most resemble the pattern
    image.
    """

    def __init__(self, target_image_path, target_image, pattern_image):
        """Takes two 2D-images, NumPy arrays loaded from files by
        OpenCV. Constructing this object computes the convolution and
        square-difference distance map.
        """
        self.target_image_path = target_image_path
        pat_shape = pattern_image.shape
        self.pattern_height = pat_shape[0]
        self.pattern_width  = pat_shape[1]
        print(
            f"pattern_width = {self.pattern_width},"
            f" pattern_height = {self.pattern_height},",
          )

        targ_shape = target_image.shape
        self.target_height = targ_shape[0]
        self.target_width  = targ_shape[1]
        print( \
            f"target_width = {self.target_width},"
            f" target_height = {self.target_height},",
          )

        if float(self.pattern_width)  > self.target_width  / 2 * 3 and \
           float(self.pattern_height) > self.target_height / 2 * 3 :
            raise ValueError(\
                "pattern image is too large relative to target image", \
                {"pattern_width": self.pattern_width, \
                 "pattern_height": self.pattern_height, \
                 "target_width": self.target_width, \
                 "target_height": self.target_height,
                },
              )
        else:
            pass

        # When searching the convolution result for local minima, we could
        # use a window size the same as the pattern size, but a slightly
        # finer window size tends to have better results. If possible, halve
        # each dimension of pattern size to define the window size.

        self.window_height = math.ceil(self.pattern_height / 2) \
            if self.pattern_height >= 4 else self.pattern_height
        self.window_width  = math.ceil(self.pattern_width  / 2) \
            if self.pattern_width  >= 4 else self.pattern_width

        print(f"window_height = {self.window_height}, window_width = {self.window_width}")

        ### Available methods for pattern matching in OpenCV
        #
        # cv.TM_CCOEFF  cv.TM_CCOEFF_NORMED
        # cv.TM_CCORR   cv.TM_CCORR_NORMED
        # cv.TM_SQDIFF  cv.TM_SQDIFF_NORMED

        # Apply template Matching
        pre_distance_map = cv.matchTemplate(target_image, pattern_image, cv.TM_SQDIFF_NORMED)
        pre_dist_map_height, pre_dist_map_width = pre_distance_map.shape
        print(f"pre_dist_map_height = {pre_dist_map_height}, pre_dist_map_width = {pre_dist_map_width}")

        # Normalize result
        np.linalg.norm(pre_distance_map)

        # The "search_image" is a white image that is the smallest
        # even multiple of the window size that is larger than the
        # distance_map.
        self.distance_map = np.ones( \
            ( pre_dist_map_height - (pre_dist_map_height % -self.window_height), \
              pre_dist_map_width  - (pre_dist_map_width  % -self.window_width ) \
            ), \
            dtype=np.float32,
          )
        print(f"dist_map_height = {pre_dist_map_height}, dist_map_width = {pre_dist_map_width}")

        # Copy the result into the "search_image".
        self.distance_map[0:pre_dist_map_height, 0:pre_dist_map_width] = pre_distance_map

        # The 'find_matching_regions()' method will memoize it's results.
        self.memoized_regions = {}

    def save_distance_map(self, file_path):
        """Write the distance map that was computed at the time this object
        was constructed to a grayscale PNG image file.
        """
        cv.imwrite(str(file_path), util.float_to_uint32(self.distance_map))

    def find_matching_regions(self, threshold=0.95):
        """Given a 'distance_map' that has been computed by the
        'compute_distance_map()' function above, and a threshold
        value, return a list of all regions where the distance map is
        less or equal to the complement of the threshold value.
        """
        if threshold < 0.5:
            raise ValueError("threshold {str(threshold)} too low, minimum is 0.5", {"threshold": threshold})
        elif threshold in self.memoized_regions:
            return self.memoized_regions[threshold]
        else:
            pass

        # We use reshape to cut the search_image up into pieces exactly
        # equal in size to the pattern image.
        dist_map_height, dist_map_width = self.distance_map.shape
        window_vcount = round(dist_map_height / self.window_height)
        window_hcount = round(dist_map_width  / self.window_width)

        tiles = self.distance_map.reshape( \
            window_vcount, self.window_height, \
            window_hcount, self.window_width \
          )

        results = []
        for y in range(window_vcount):
            for x in range(window_hcount):
                tile = tiles[y, :, x, :]
                (min_y, min_x) = np.unravel_index( \
                    np.argmin(tile), \
                    (self.window_height, self.window_width),
                  )
                global_y = y * self.window_height + min_y
                global_x = x * self.window_width  + min_x
                if tile[min_y, min_x] <= (1.0 - threshold):
                    results.append( \
                        RegionSize( \
                            global_x, global_y, \
                            self.pattern_width, self.pattern_height \
                          ) \
                      )
                else:
                    pass

        self.memoized_regions[threshold] = results
        return results

    def write_all_cropped_images(self, target_image, threshold, results_dir):
        print(f"write_all_cropped_images: threshold = {threshold!s}")
        regions = self.find_matching_regions(threshold=threshold)
        prefix = self.target_image_path.stem
        for reg in regions:
            reg.crop_write_image(target_image, results_dir, prefix)

####################################################################################################
# The Qt GUI

class FileListItem(qt.QListWidgetItem):
    """A QListWidgetItem for an element in the files list in the Files tab."""

    def __init__(self, path):
        super().__init__(str(path))
        self.path = path

    def get_path(self):
        return self.path

#--------------------------------------------------------------------------------------------------

class ImagePreview(qt.QGraphicsView):

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self.app_model = app_model
        self.preview_scene = qt.QGraphicsScene(self)
        self.pixmap_path = None
        self.pixmap_item = None
        self.pixmap_buffer = None
        self.setViewportUpdateMode(4) # 4: QGraphicsView::BoundingRectViewportUpdate
        self.setResizeAnchor(1) # 1: QGraphicsView::AnchorViewCenter
        self.setScene(self.preview_scene)
        self.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu

    def resizeEvent(self, newSize):
        super().resizeEvent(newSize)
        if self.pixmap_item is not None:
            self.fitInView(self.pixmap_item, 1) # 1: qcore.AspectRatioMode::KeepAspectRatio

    def update_display(self):
        target = self.app_model.get_target()
        path = target.get_path()
        if (self.pixmap_buffer is not None) and (self.pixmap_path == path):
            # Here the pixmap_path has not been changed, so we need to
            # prevent it from being freed by self.preview_scene.clear(),
            # as we do not want to reload it from the filesystem.
            self.preview_scene.removeItem(self.pixmap_item)
        else:
            self.pixmap_buffer = qgui.QPixmap()
            self.pixmap_buffer.load(str(path))
        self.pixmap_item = None
        self.pixmap_path = path
        self.preview_scene.clear()
        if self.pixmap_buffer is not None:
            self.pixmap_item = qt.QGraphicsPixmapItem(self.pixmap_buffer)
            self.preview_scene.addItem(self.pixmap_item)
            self.resetTransform()
            self.fitInView(self.pixmap_item, 1)
        else:
            print(f'ImagePreview.update_display() #(Failed to load "{path!s}")')
            pass


class InspectImagePreview(ImagePreview):

    def __init__(self, app_model, parent):
        super().__init__(app_model, parent)
        self.pen = qgui.QPen(qgui.QColor(255, 0, 0, 255))
        self.pen.setCosmetic(True)
        self.pen.setWidth(3)

    def place_rectangles(self, rectangle_list):
        self.preview_scene.clear()
        if self.pixmap_item is not None:
            self.pixmap_item = qt.QGraphicsPixmapItem(self.pixmap_buffer)
            self.preview_scene.addItem(self.pixmap_item)
        else:
            pass
        for rectangle in rectangle_list:
            bounds = rectangle.get_point_and_size()
            self.preview_scene.addRect(*bounds, self.pen)

#---------------------------------------------------------------------------------------------------

class MessageBox(qt.QWidget):

    def __init__(self, message):
        super().__init__()
        self.layout = qt.QHBoxLayout(self)
        self.message = qt.QLabel(message)
        self.layout.addWidget(self.message)

#---------------------------------------------------------------------------------------------------

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

class FilesTab(qt.QWidget):
    """Display a list of images, and provide an image preview window to
    view each iamge.
    """

    def __init__(self, app_model, main_view):
        super().__init__(main_view)
        self.setObjectName("FilesTab")
        self.app_model = app_model
        self.main_view = main_view
        #---------- Setup visible widgets ----------
        self.layout        = qt.QHBoxLayout(self)
        self.splitter      = qt.QSplitter(1, self)
        self.setAcceptDrops(True)
        self.splitter.setObjectName("FilesTab splitter")
        self.list_widget   = qt.QListWidget(self)
        self.list_widget.setObjectName("FilesTab list_widget")
        self.list_widget.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu
        self.image_preview  = ImagePreview(self.app_model, self)
        self.image_preview.setObjectName("FilesTab ImagePreview")
        self.splitter.addWidget(self.list_widget)
        self.splitter.addWidget(self.image_preview)
        self.layout.addWidget(self.splitter)
        self.display_pixmap_path = None
        #---------- Populate list view ----------
        self.reset_paths_list()
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

    def activate_handler(self, item):
        path = item.get_path()
        self.app_model.set_target_image_path(path)
        self.app_model.match_on_file()
        distance_map = self.app_model.get_distance_map()
        if distance_map:
            self.main_view.show_distance_map()
            self.main_view.show_inspect_tab()
        else:
            self.main_view.show_pattern_tab()
            self.main_view.error_message( \
                "A pattern image must be set for matching on the selected image." \
              )

    def activate_selected_item(self):
        item = self.list_widget.currentItem()
        self.activate_handler(item)

    def item_change_handler(self, item, _old):
        if item is not None:
            self.app_model.set_target_image_path(item.get_path())
            self.image_preview.update_display()
        else:
            print("FilesTab.item_change_handler(item=None)")

    def use_current_item_as_pattern(self):
        item = self.list_widget.currentItem()
        path = item.get_path()
        print(f'FilesTab.use_current_item_as_pattern() #("{path}")')
        self.app_model.set_pattern_image_path(path)
        self.main_view.update_pattern_pixmap()

    def reset_paths_list(self):
        """Populate the list view with an item for each file path."""
        paths_list = self.app_model.get_target_fileset()
        self.list_widget.clear()
        if paths_list:
            for item in paths_list:
                self.list_widget.addItem(FileListItem(item))
        else:
            pass

    def open_image_files_handler(self):
        target_dir = self.main_view.get_config().output_dir
        urls = \
            qt.QFileDialog.getOpenFileUrls( \
                self, "Open images in which to search for patterns", \
                qcore.QUrl(str(target_dir)), \
                "Images (*.png *.jpg *.jpeg)", "", \
                qt.QFileDialog.ReadOnly, \
                ["file"] \
              )
        print(f"selected urls = {urls}")
        urls = urls[0]
        if len(urls) > 0:
            self.main_view.add_target_image_paths(gather_QUrl_local_files(urls))
            self.files_tab.reset_paths_list(self.target_image_paths)
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
            self.app_model.add_target_fileset(gather_QUrl_local_files(mime_data.urls()))
            self.reset_paths_list()
        elif mime_data.hasText():
            event.accept()
            self.app_model.add_target_fileset(split_linebreaks(mime_data.text()))
            self.reset_paths_list()
        else:
            event.ignore()

#---------------------------------------------------------------------------------------------------

class PatternPreview(qt.QGraphicsView):
    """A QGraphicsView for displaying the pattern image. It does not
    inherit from InspectImagePreview because it has different behavior
    for displaying the image, and for drag and drop. This class may be
    removed and replaced with a more featureful versino of
    InspectImagePreview in the future.
    """

    def __init__(self, app_model, main_view):
        super().__init__()
        self.app_model = app_model
        self.main_view = main_view
        self.display_pixmap = qgui.QPixmap()
        self.preview_scene  = qt.QGraphicsScene(self)
        self.pixmap_item = None
        self.setScene(self.preview_scene)
        self.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        self.main_view.dragEnterEvent(event)

    def dropEvent(self, event):
        self.main_view.dropEvent(event)

    def update_pattern_pixmap(self):
        self.preview_scene.clear()
        pattern = self.app_model.get_pattern()
        path = pattern.get_path()
        self.display_pixmap = qgui.QPixmap(str(path))
        self.pixmap_item = self.preview_scene.addPixmap(self.display_pixmap)
        self.resetTransform()

class PatternSetupTab(qt.QWidget):

    def __init__(self, app_model, main_view):
        super().__init__(main_view)
        self.setObjectName("PatternSetupTab")
        self.setAcceptDrops(True)
        self.app_model    = app_model
        self.main_view    = main_view
        self.layout       = qt.QHBoxLayout(self)
        self.preview_view = PatternPreview(app_model, self)
        self.layout.addWidget(self.preview_view)
        ## Action: open image files
        self.open_pattern_file = qt.QAction("Open pattern file", self)
        self.open_pattern_file.setShortcut(qgui.QKeySequence.Open)
        self.open_pattern_file.triggered.connect(self.open_pattern_file_handler)
        self.preview_view.addAction(self.open_pattern_file)

    def update_pattern_pixmap(self):
        self.preview_view.update_pattern_pixmap()

    def open_pattern_file_handler(self):
        target_dir = self.main_view.get_config().pattern
        url = \
            qt.QFileDialog.getOpenFileUrl( \
                self, "Open images in which to search for patterns", \
                qcore.QUrl(str(target_dir)), \
                "Images (*.png *.jpg *.jpeg)", "", \
                qt.QFileDialog.ReadOnly, \
                ["file"] \
              )
        url = url[0]
        if (url is not None) and url.isLocalFile():
            self.main_view.show_pattern_image_path(PurePath(url.toLocalFile()))
        else:
            print(f"URL {url} is not a local file")

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if len(urls) == 1:
                event.accept()
            else:
                event.ignore()
        elif mime_data.hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if len(urls) == 1:
                event.accept()
                url = urls[0]
                self.app_model.set_pattern_image_path(PurePath(url.toLocalFile()))
                self.main_view.update_pattern_pixmap()
            else:
                event.ignore()
        elif mime_data.hasText():
            event.accept()
            self.app_model.set_pattern_image_path(PurePath(mime_data.text()))
            self.main_view.update_pattern_pixmap()
        else:
            event.ignore()

#---------------------------------------------------------------------------------------------------

class PercentSlider(qt.QWidget):

    def __init__(self, label, init_value, callback):
        super().__init__()
        self.percent = init_value
        self.callback = callback
        self.label = qt.QLabel(label)
        self.slider = qt.QSlider(1, self)
        self.slider.setMinimum(500)
        self.slider.setMaximum(1000)
        self.slider.setPageStep(50)
        self.slider.setSingleStep(10)
        self.slider.setValue(round(self.percent * 1000.0))
        self.slider.setObjectName("InspectTab slider")
        self.slider.valueChanged.connect(self.value_changed_handler)
        self.setSizePolicy(self.slider.sizePolicy())
        self.textbox = qt.QLineEdit(str(round(self.percent * 1000.0) / 10.0), self)
        self.textbox.setMaxLength(5)
        self.textbox.setObjectName("InspectTab textbox")
        font_metrics = qt.QLabel("100.0 %").fontMetrics()
        self.textbox.setFixedWidth(font_metrics.width("100.0 %"))
        self.textbox.editingFinished.connect(self.textbox_handler)
        #---------- The top bar is always visible ----------
        self.layout = qt.QHBoxLayout(self)
        self.layout.setObjectName("InspectTab layout")
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.textbox)
        self.layout.addWidget(self.slider)

    def get_percent(self):
        return self.percent

    def value_changed_handler(self, new_value):
        self.slider.setValue(new_value)
        self.textbox.clear()
        self.textbox.setText(f"{new_value/10.0}")
        self.percent = new_value / 1000.0
        self.callback(new_value)

    def reset_value(self):
        self.textbox.setText(f"{self.percent * 100.0}")
        self.slider.setValue(round(self.percent * 1000.0))

    def textbox_handler(self):
        # editingFinished signal handler
        txt = self.textbox.text()
        try:
            new_value = float(txt)
            if new_value >= 50.0 and new_value <= 100.0:
                self.percent = new_value / 100.0
            else:
                pass
        except ValueError:
            pass
        self.reset_value()

#---------------------------------------------------------------------------------------------------

class InspectTab(qt.QWidget):

    def __init__(self, app_model, main_view):
        super().__init__(main_view)
        self.app_model = app_model
        self.main_view = main_view
        self.distance_map = None
        self.setObjectName("InspectTab")
        # The layout of this widget is a top bar with a threshold slider and a graphics view or
        # message view. The graphics view or message view can be changed depending on whether
        # the target and pattern are both selected.
        self.layout = qt.QVBoxLayout(self)
        self.layout.setObjectName("InspectTab layout")
        config = app_model.get_config()
        self.slider = PercentSlider( \
            "Threshold %", \
            config.threshold, \
            self.slider_handler \
          )
        self.layout.addWidget(self.slider)
        self.message_box = MessageBox("Please select SEARCH target image and PATTERN image.")
        self.layout.addWidget(self.message_box)
        self.image_preview = InspectImagePreview(self.app_model, self)
        self.image_preview.hide()
        self.layout.addWidget(self.image_preview)
        #---------- Setup context menus ----------
        self.do_save_selected = qt.QAction("Save all selected regions", self)
        self.do_save_selected.setShortcut(qgui.QKeySequence.Save)
        self.do_save_selected.setEnabled(False)
        self.do_save_selected.triggered.connect(self.save_selected)
        self.image_preview.addAction(self.do_save_selected)

    def slider_handler(self, new_value):
        self.place_rectangles()

    def show_nothing(self):
        self.image_preview.hide()
        self.message_box.show()

    def show_image_preview(self):
        self.message_box.hide()
        self.image_preview.show()

    def show_distance_map(self):
        """Draws the target image and any matching pattern rectangles into the
        image_preview window."""
        self.distance_map = self.app_model.get_distance_map()
        self.image_preview.update_display()
        self.place_rectangles()
        self.show_image_preview()
        self.do_save_selected.setEnabled(True)

    def place_rectangles(self):
        if self.distance_map is not None:
            threshold = self.slider.get_percent()
            self.image_preview.place_rectangles( \
                self.distance_map.find_matching_regions(threshold) \
              )
        else:
            print("WARNING: InspectTab.place_rectangles() called before distance_map was set")

    def modal_prompt_get_directory(self, init_dir):
        output_dir = \
            qt.QFileDialog.getExistingDirectory( \
                self, "Write images to directory", \
                init_dir, \
                qt.QFileDialog.ShowDirsOnly \
          )
        return PurePath(output_dir)

    def save_selected(self):
        if self.distance_map is not None:
            output_dir = self.main_view.get_config().output_dir
            output_dir = self.modal_prompt_get_directory(str(output_dir))
            threshold = self.slider.get_percent()
            target_image = self.main_view.target.get_image()
            self.distance_map.write_all_cropped_images(target_image, threshold, output_dir)
        else:
            print('WARNING: InspectTab.save_selected() called before distance_map was set')

#---------------------------------------------------------------------------------------------------

class CachedCVImageLoader():
    """A tool for loading and caching image from a file into an OpenCV image buffer.
    """

    def __init__(self, path=None):
        self.path   = path
        self.image  = None

    def load_image(self, path=None):
        print('CachedCVImageLoader.load_image(' +
              ('None' if path is None else f'"{path}"') +
              ')')
        if path is None:
            path = self.path
            self.force_load_image(path)
        elif path != self.path:
            self.force_load_image(path)
        else:
            pass

    def force_load_image(self, path):
        self.image = cv.imread(str(path))
        if self.image is None:
            self.path = None
            raise ValueError(
                f"Failed to load image file {path!s}",
                path,
              )
        else:
            self.path = path
            print(f'CachedCVImageLoader.force_load_image() #(success "{self.path}")')

    def get_path(self):
        return self.path

    def get_image(self):
        if self.image is None:
            print(f'WARNING: CachedCVImageLoader("{self.path!s}").get_image() returned None')
        else:
            pass
        return self.image

    def set_image(self, path, pixmap):
        self.path = path
        self.pixmap = pixmap

#---------------------------------------------------------------------------------------------------

class PatternMatcherView(qt.QTabWidget):
    """The Qt Widget containing the GUI for the pattern matching program.
    """

    def __init__(self, app_model, main_view=None):
        super().__init__(main_view)
        self.app_model = app_model
        #----------------------------------------
        # Setup the GUI
        self.notify = qt.QErrorMessage(self)
        self.setWindowTitle("Image Pattern Matching Kit")
        self.resize(800, 600)
        self.setTabPosition(qt.QTabWidget.North)
        self.files_tab = FilesTab(app_model, self)
        self.pattern_tab = PatternSetupTab(app_model, self)
        self.inspect_tab = InspectTab(app_model, self)
        self.addTab(self.files_tab, "Search")
        self.addTab(self.pattern_tab, "Pattern")
        self.addTab(self.inspect_tab, "Inspect")
        self.currentChanged.connect(self.change_tab_handler)

    def error_message(self, message):
        self.notify.showMessage(message)

    def change_tab_handler(self, index):
        """Does the work of actually changing the GUI display to the "InspectTab".
        """
        super().setCurrentIndex(index)
        self.widget(index).update()

    def show_inspect_tab(self):
        self.setCurrentWidget(self.inspect_tab)

    def show_pattern_tab(self):
        self.setCurrentWidget(self.pattern_tab)

    def show_distance_map(self):
        self.inspect_tab.show_distance_map()

    def update_pattern_pixmap(self):
        self.pattern_tab.update_pattern_pixmap()
        self.show_pattern_tab()

####################################################################################################

class PatternMatcher():
    """The main app model contains the buffer for the reference image, and the memoized search
    results for every image that has been compared against the reference image for a particular
    threshold value."""

    def __init__(self, config=None):
        self.distance_map = None
        self.config = None
        self.results_dir = None
        self.set_target_fileset(None)
        self.results_dir = None
        self.save_distance_map = None
        self.threshold = 0.78
        self.target = CachedCVImageLoader()
        self.pattern = CachedCVImageLoader()
        if config:
            self.set_config(config)
        else:
            pass

    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config
        self.set_target_fileset(config.inputs)
        self.set_pattern_image_path(config.pattern)
        self.results_dir = config.output_dir
        self.threshold = config.threshold
        self.save_distance_map = config.save_map
        # Load the pattern right away, if it is not None
        self.pattern_image_path = config.pattern
        if self.pattern_image_path:
            self.pattern.load_image(self.pattern_image_path)
        else:
            pass

    def get_pattern(self):
        return self.pattern

    def get_pattern_image_path(self):
        return self.pattern.get_path()

    def set_pattern_image_path(self, path):
        print(f'PatternMatcher.set_pattern_image_path("{path}")')
        self.pattern_image_path = path
        if path:
            self.pattern.load_image(path)
        else:
            pass

    def set_pattern_pixmap(self, pattern_path, pixmap):
        self.pattern.set_image(pattern_path, pixmap)

    def get_target(self):
        return self.target

    def get_target_image_path(self):
        return self.target.get_path()

    def set_target_image_path(self, path):
        print(f'PatternMatcher.set_target_image_path("{path}")')
        self.target.load_image(path)

    def get_target_fileset(self):
        return self.target_fileset

    def set_target_fileset(self, path_list):
        self.target_fileset = \
            fs.FileSet(filter=fs.filter_image_files_by_ext)
        if path_list:
            self.fileset.merge_recursive(path_list)
        else:
            pass

    def add_target_fileset(self, path_list):
        self.target_fileset.merge_recursive(path_list)

    def get_distance_map(self):
        return self.distance_map

    def match_on_file(self):
        """This function is triggered when you double-click on an item in the image
        list in the "FilesTab". It starts running the pattern matching algorithm and
        changes the display of the GUI over to the "InspectTab".
        """
        patimg = self.pattern.get_image()
        targimg = self.target.get_image()
        if patimg is None:
            print(f'PatternMatcher.match_on_file() #(self.pattern.get_image() returned None)')
        elif targimg is None:
            print(f'PatternMatcher.match_on_file() #(self.target.get_image() returned None)')
        else:
            target_image_path = self.target.get_path()
            self.distance_map = DistanceMap(target_image_path, targimg, patimg)

    def crop_matched_patterns(target_image_path):
        #TODO: the "save_distance_map" argument should be used as a
        #      file name suffix, not a file name.

        # Create results directory if it does not exist
        if not os.path.isdir(results_dir):
            os.mkdir(results_dir)

        target_image  = self.target.get_image(target_image_path)
        if target_image is None:
            raise FileNotFoundError(self.target_image_path)
        else:
            pass

        pattern_image = self.pattern.get_iamge(self.pattern_image_path)
        if pattern_image is None:
            raise FileNotFoundError(pattern_image_path)
        else:
            pass

        self.distance_map = DistanceMap(target_image_path, target_image, pattern_image)

        if self.save_distance_map is not None:
            # Save the convolution image:
            distance_map.save_distance_map(self.save_distance_map)
        else:
            pass
        distance_map.write_all_cropped_images(target_image, threshold, results_dir)

    def batch_crop_matched_patterns():
        self.pattern.load_image()
        for image in self.target_fileset:
            print(
                f'image = {image}\npattern_image_path = {pattern_image_path}\n'
                f'results_dir = {results_dir}\n'
                f'threshold = {threshold}\n'
                f'save_distance_map = {save_distance_map}',
              )
            self.crop_matched_patterns(image)

    def load_image(self, path):
        self.pattern.set_pattern_image_path(path)
        self.pattern.load_image()

####################################################################################################
# The main function, and functions for searching the filesystem for program input

def main():
    arper = argparse.ArgumentParser(
        description="""
          Does "pattern matching" -- finding instances of a smaller image in a larger image.
          """,
        exit_on_error=False,
        epilog="""
          This program will search for a pattern image in each input image, regions found
          to be close to 100% similar within a certain specified threshold value will
          be cropped and saved as a separate image file in a specified output directory.

          The --gui option enables GUI mode (disabled by default), where you can view
          each image and the bounding boxes for each region that matches a pattern. If
          you do not enable GUI mode, this program operates in "batch mode", creating the
          output directory and images without user intervention.
          """,
      )

    arper.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="""
          Reports number of matching regions per input image,
          reports each file that is created.
          """,
      )

    arper.add_argument(
        "--gui",
        dest="gui",
        action="store_true",
        default=False,
        help="""
          Inlcude this arugment to launch the GUI utility.
          """,
      )

    arper.add_argument( \
        "--no-gui", \
        dest="gui", \
        action="store_false", \
        help="""
          Program runs in "batch mode," without presenting a GUI or requesting user feedback.
          """ \
      )

    arper.add_argument( \
        "-t", "--threshold", \
        dest="threshold", \
        action="store", \
        default="95", \
        type=util.threshold, \
        help="""
          The minimum percentage of similarity reqiured between a pattern and a
          region of the image in order for the region to be selected and cropped.
          """,
      )

    arper.add_argument( \
        "-p", "--pattern", \
        dest="pattern", \
        action="store", \
        default=None, \
        type=PurePath, \
        help="""
          Specify the file path of the image to be used as the pattern.
          """ \
      )

    arper.add_argument( \
        "-o", "--output-dir", \
        dest="output_dir", \
        action="store", \
        default=PurePath("./matched-images"), \
        type=PurePath, \
        help="""
          Specify the output directory into which multiple image files can be created.
          """,
      )

    arper.add_argument( \
        "--save-map", \
        dest="save_map", \
        action="store", \
        default=None, \
        help="""
          If a filename suffix string is supplied as this argument, the resulting image of
          the pattern matching convolution is saved to a file of the same name as the input
          file with the prefix apended to the filename (but before the file extension).
          """ \
      )

    arper.add_argument( \
        "inputs", \
        nargs="*", \
        action="store", \
        type=PurePath, \
        help="""
          A set of images, or directories containing images, in which the pattern image is searched.
          Directories are searched for images, but not recursively. See the --recursive option.
          """ \
      )

    (config, remaining_argv) = arper.parse_known_args()
    matcher = PatternMatcher(config)
    print(config)
    if config.gui:
        app = qt.QApplication(remaining_argv)
        appWindow = PatternMatcherView(matcher)
        appWindow.show()
        sys.exit(app.exec_())
    else:
        matcher.batch_crop_matched_patterns()

####################################################################################################

if __name__ == "__main__":
    main()
