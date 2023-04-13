#! /usr/bin/env python3

import argparse
import sys
import argparse
import os
import os.path
import re
from pathlib import PurePath
import math
import cv2 as cv
import numpy as np
from scipy.signal import argrelextrema

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

####################################################################################################
# Parsing command line arguments

arper = argparse.ArgumentParser( \
    description="""
      Does "pattern matching" -- finding instances of a smaller image in a larger image.
      """, \
    exit_on_error=False, \
    epilog="""
      This program will search for a pattern image in each input image, regions found
      to be close to 100% similar within a certain specified threshold value will
      be cropped and saved as a separate image file in a specified output directory.

      The --gui option enables GUI mode (disabled by default), where you can view
      each image and the bounding boxes for each region that matches a pattern. If
      you do not enable GUI mode, this program operates in "batch mode", creating the
      output directory and images without user intervention.
      """ \
  )

arper.add_argument (\
    '-v', '--verbose', \
    dest='verbose', \
    action='store_true', \
    default=False, \
    help="""
      Reports number of matching regions per input image,
      reports each file that is created.
      """ \
  )

arper.add_argument( \
    '--gui', \
    dest='gui', \
    action='store_true', \
    default=False, \
    help="""
      Inlcude this arugment to launch the GUI utility.
      """ \
  )

arper.add_argument( \
    '--no-gui', \
    dest='gui', \
    action='store_false', \
    help="""
      Program runs in "batch mode," without presenting a GUI or requesting user feedback.
      """ \
  )

def threshold(val):
    val = float(val)
    if val >= 0.0 and val <= 100.0:
        return (float(val) / 100.0)
    else:
        raise ValueError("threshold must be percentage value between 0 and 100")

arper.add_argument( \
    '-t', '--threshold', \
    dest='threshold', \
    action='store', \
    default='95', \
    type=threshold, \
    help="""
      The minimum percentage of similarity reqiured between a pattern and a
      region of the image in order for the region to be selected and cropped.
      """
  )

arper.add_argument( \
    '-p', '--pattern', \
    dest='pattern', \
    action='store', \
    default=PurePath('./pattern.png'), \
    type=PurePath, \
    help="""
      Specify the file path of the image to be used as the pattern.
      """ \
  )

arper.add_argument( \
    '-o', '--output-dir', \
    dest='output_dir', \
    action='store', \
    default=PurePath('./matched-images'), \
    type=PurePath, \
    help="""
      Specify the output directory into which multiple image files can be created.
      """
  )

arper.add_argument( \
    '--save-map', \
    dest='save_map', \
    action='store', \
    default=None, \
    help="""
      If a filename suffix string is supplied as this argument, the resulting image of
      the pattern matching convolution is saved to a file of the same name as the input
      file with the prefix apended to the filename (but before the file extension).
      """ \
  )

arper.add_argument( \
    'inputs', \
    nargs='*', \
    action='store', \
    type=PurePath, \
    help="""    
      A set of images, or directories containing images, in which the pattern image is searched.
      Directories are searched for images, but not recursively. See the --recursive option.
      """ \
  )

####################################################################################################
# Miscelaneous utilities (that ought to already exist somewhere else, but do not).

def float_to_uint32(input_image):
    height, width = input_image.shape
    output_image = np.empty((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            output_image[y,x] = round(input_image[y,x] * 255)
    return output_image

def flatten_list(input):
    result = []
    for x in input:
        if type(x) == type([]):
            result.extend(x)
        else:
            result.append(x)
    input.clear()
    input.extend(result)
    return input

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
        return PurePath(f'{self.x_min:0>5}x{self.y_min:0>5}.png')

    def crop_write_image(self, image, results_dir):
        """Takes an image to crop, crops it with 'crop_image()', takes a
        PurePath() 'results_dir', writes the cropped image to the file
        path given by (results_dir/self.as_file_name()) using
        'cv.imwrite()'.
        """
        write_path = str(results_dir / self.as_file_name())
        print(f'crop_write_image -> {write_path}')
        cv.imwrite(write_path, self.crop_image(image))

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

    def __init__(self, target_image, pattern_image):
        """Takes two 2D-images, NumPy arrays loaded from files by
        OpenCV. Constructing this object computes the convolution and
        square-difference distance map.
        """
        pat_shape = pattern_image.shape
        self.pattern_height = pat_shape[0]
        self.pattern_width  = pat_shape[1]
        print( \
            f'pattern_width = {self.pattern_width},' + \
            f' pattern_height = {self.pattern_height},'
          )

        targ_shape = target_image.shape
        self.target_height = targ_shape[0]
        self.target_width  = targ_shape[1]
        print( \
            f'target_width = {self.target_width},' + \
            f' target_height = {self.target_height},'
          )

        if float(self.pattern_width)  > self.target_width  / 2 * 3 and \
           float(self.pattern_height) > self.target_height / 2 * 3 :
            raise ValueError(\
                "pattern image is too large relative to target image", \
                {'pattern_width': self.pattern_width, \
                 'pattern_height': self.pattern_height, \
                 'target_width': self.target_width, \
                 'target_height': self.target_height
                }
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

        print(f'window_height = {self.window_height}, window_width = {self.window_width}')

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
              pre_dist_map_width  - (pre_dist_map_width  % -self.window_width ), \
            ), \
            dtype=np.float32
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
        cv.imwrite(str(file_path), float_to_uint32(self.distance_map))

    def find_matching_regions(self, threshold=0.95):
        """Given a 'distance_map' that has been computed by the
        'compute_distance_map()' function above, and a threshold
        value, return a list of all regions where the distance map is
        less or equal to the complement of the threshold value.
        """
        if threshold < 0.5:
            raise ValueError("threshold {str(threshold)} too low, minimum is 0.5", {'threshold': threshold})
        elif threshold in self.memoized_regions:
            return self.memoized_regions[threshold]
        else:
            pass

        # We use reshape to cut the search_image up into pieces exactly
        # equal in size to the pattern image.
        dist_map_height, dist_map_width = self.distance_map.shape
        window_vcount = round(dist_map_height / self.window_height)
        window_hcount = round(dist_map_width  / self.window_width)
        #print(f"window_hcount = {window_vcount}, window_vcount = {window_hcount}")

        tiles = self.distance_map.reshape( \
            window_vcount, self.window_height, \
            window_hcount, self.window_width \
          )

        results = []
        for y in range(window_vcount):
            for x in range(window_hcount):
                tile = tiles[y, :, x, :]
                #visible_tile = float_to_uint32(tile)
                #cv.imwrite(f"./{x}x{y}.png", visible_tile)
                (min_y, min_x) = np.unravel_index( \
                    np.argmin(tile), \
                    (self.window_height, self.window_width)
                  )
                global_y = y * self.window_height + min_y
                global_x = x * self.window_width  + min_x
                if tile[min_y, min_x] <= (1.0 - threshold):
                    #print(f"argmin(tiles[{y},{x}]) -> ({global_x}, {global_y})")
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
        print(f'write_all_cropped_images: threshold = {str(threshold)}')
        regions = self.find_matching_regions(threshold=threshold)
        for reg in regions:
            reg.crop_write_image(target_image, results_dir)

#---------------------------------------------------------------------------------------------------
# Front-end API to the pattern matching program, called in batch mode.

def crop_matched_patterns(
        target_image_path=PurePath('./test-target.png'), \
        pattern_image_path=PurePath('./test-pattern.png'), \
        results_dir=PurePath('./test-results'), \
        threshold=0.78, \
        save_distance_map="_map" \
      ):
    #TODO: the "save_distance_map" argument should be used as a
    #      file name suffix, not a file name.

    # Create results directory if it does not exist
    if not os.path.isdir(results_dir):
        os.mkdir(results_dir)

    target_image  = cv.imread(str(target_image_path))
    if target_image is None:
        raise FileNotFoundError(target_image_path)
    else:
        pass

    pattern_image = cv.imread(str(pattern_image_path))
    if pattern_image is None:
        raise FileNotFoundError(pattern_image_path)
    else:
        pass

    distance_map  = DistanceMap(target_image, pattern_image)

    if save_distance_map is not None:
        # Save the convolution image:
        distance_map.save_distance_map(save_distance_map)
    else:
        pass

    distance_map.write_all_cropped_images(target_image, threshold, results_dir)

def batch_crop_matched_patterns(
        target_images=[PurePath('./test-target.png')], \
        pattern_image_path=PurePath('./test-pattern.png'), \
        results_dir=PurePath('./test-results'), \
        threshold=0.78, \
        save_distance_map="_map" \
      ):
    for image in target_images:
        print(f'image = {image}\npattern_image_path = {pattern_image_path}\nresults_dir = {results_dir}\nthreshold = {threshold}\nsave_distance_map = {save_distance_map}')
        crop_matched_patterns( \
            image, \
            pattern_image_path, \
            results_dir, \
            threshold, \
            save_distance_map \
          )

####################################################################################################
# The Qt GUI

class FileListItem(qt.QListWidgetItem):
    """A QListWidgetItem for an element in the files list in the Files tab."""

    def __init__(self, path):
        super(FileListItem, self).__init__(str(path))
        self.path = path

    def get_path(self):
        return self.path

#--------------------------------------------------------------------------------------------------

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

class InspectImagePreview(ImagePreview):

    def __init__(self, parent):
        super(InspectImagePreview, self).__init__(parent)
        self.pen = qgui.QPen(qgui.QColor(255, 0, 0, 255))
        self.pen.setCosmetic(True)
        self.pen.setWidth(3)

    def place_rectangles(self, rectangle_list):
        self.preview_scene.clear()
        if self.pixmap_item is not None:
            self.pixmap_item = qt.QGraphicsPixmapItem(self.display_pixmap)
            self.preview_scene.addItem(self.pixmap_item)
        else:
            pass
        for rectangle in rectangle_list:
            bounds = rectangle.get_point_and_size()
            self.preview_scene.addRect(*bounds, self.pen)

#---------------------------------------------------------------------------------------------------

class MessageBox(qt.QWidget):

    def __init__(self, message):
        super(MessageBox, self).__init__()
        self.layout = qt.QHBoxLayout(self)
        self.message = qt.QLabel(message)
        self.layout.addWidget(self.message)

#---------------------------------------------------------------------------------------------------

def gather_QUrl_local_files(qurl_list):
    urls = []
    for url in qurl_list:
        if url.isLocalFile():
            urls.append(PurePath(url.toLocalFile()))
    return urls

class FilesTab(qt.QWidget):

    def __init__(self, parent):
        super(FilesTab, self).__init__(parent)
        self.setObjectName('FilesTab')
        #---------- Setup visible widgets ----------
        self.main_view     = parent
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
        self.reset_paths_list(self.main_view.target_image_paths)
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
        self.main_view.match_on_file(item.get_path())

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
        self.main_view.set_pattern_pixmap(path, self.image_preview.get_pixmap())

    def reset_paths_list(self, paths_list):
        """Populate the list view with an item for each file path."""
        self.list_widget.clear()
        for item in paths_list:
            self.list_widget.addItem(FileListItem(item))

    def open_image_files_handler(self):
        target_dir = self.main_view.get_config().output_dir
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
            self.main_view.add_target_image_paths(gather_QUrl_local_files(urls))
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
            self.main_view.add_target_image_paths(gather_QUrl_local_files(mime_data.urls()))
        elif mime_data.hasText():
            event.accept()
            self.main_view.add_target_image_paths(split_linebreaks(mime_data.text()))
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

    def __init__(self, parent):
        super(PatternPreview, self).__init__()
        self.parent = parent
        self.display_pixmap = qgui.QPixmap()
        self.preview_scene  = qt.QGraphicsScene(self)
        self.pixmap_item = None
        self.setScene(self.preview_scene)
        self.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        self.parent.dragEnterEvent(event)

    def dropEvent(self, event):
        self.parent.dropEvent(event)

    def set_pattern_pixmap(self):
        self.preview_scene.clear()
        self.resetTransform()
        self.pixmap_item = qt.QGraphicsPixmapItem(self.display_pixmap)
        self.preview_scene.addItem(self.pixmap_item)

    def show_pattern_image_path(self, pixmap_path, pixmap=None):
        if pixmap is not None:
            self.display_pixmap = pixmap
        else:
            loaded = self.display_pixmap.load(str(pixmap_path))
        self.set_pattern_pixmap()

class PatternSetupTab(qt.QWidget):

    def __init__(self, config, parent=None):
        super(PatternSetupTab, self).__init__(parent)
        self.setObjectName('PatternSetupTab')
        self.setAcceptDrops(True)
        self.main_view      = parent
        self.file_path      = self.main_view.get_config().pattern
        self.layout         = qt.QHBoxLayout(self)
        self.preview_view   = PatternPreview(self)
        self.layout.addWidget(self.preview_view)
        if config.pattern is not None:
            print(f'config.pattern = "{config.pattern}"')
            self.show_pattern_image_path(config.pattern)
        else:
            print(f'config.pattern = None')
            pass
        ## Action: open image files
        self.open_pattern_file = qt.QAction("Open pattern file", self)
        self.open_pattern_file.setShortcut(qgui.QKeySequence.Open)
        self.open_pattern_file.triggered.connect(self.open_pattern_file_handler)
        self.preview_view.addAction(self.open_pattern_file)

    def show_pattern_image_path(self, pattern_path):
        self.display_pixmap_path = pattern_path
        self.preview_view.show_pattern_image_path(self.display_pixmap_path)

    def set_pattern_pixmap(self, pattern_path, pixmap):
        self.file_path = pattern_path
        self.preview_view.show_pattern_image_path(pattern_path, pixmap)

    def open_pattern_file_handler(self):
        target_dir = self.main_view.get_config().pattern
        url = \
            qt.QFileDialog.getOpenFileUrl( \
                self, "Open images in which to search for patterns", \
                qcore.QUrl(str(target_dir)), \
                'Images (*.png *.jpg *.jpeg)', '', \
                qt.QFileDialog.ReadOnly, \
                ["file"] \
              )
        url = url[0]
        if (url is not None) and url.isLocalFile():
            self.main_view.show_pattern_image_path(PurePath(url.toLocalFile()))
        else:
            print(f'URL {url} is not a local file')

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
            url = mime_data.urls()
            url = url[0]
            if len(urls) == 1:
                event.accept()
                url = mime_data.urls()[0]
                self.preview_view.show_pattern_image_path(PurePath(url.toLocalFile()))
                self.main_view.show_pattern_image_path(PurePath(url.toLocalFile()))
            else:
                event.ignore()
        elif mime_data.hasText():
            event.accept()
            self.preview_view.show_pattern_image_path(PurePath(mime_data.text()))
            self.main_view.show_pattern_image_path(PurePath(mime_data.text()))
        else:
            event.ignore()

#---------------------------------------------------------------------------------------------------

class PercentSlider(qt.QWidget):

    def __init__(self, label, init_value, callback):
        super(PercentSlider, self).__init__()
        self.percent = init_value
        self.callback = callback
        self.label = qt.QLabel(label)
        self.slider = qt.QSlider(1, self)
        self.slider.setMinimum(500)
        self.slider.setMaximum(1000)
        self.slider.setPageStep(50)
        self.slider.setSingleStep(10)
        self.slider.setValue(round(self.percent * 1000.0))
        self.slider.setObjectName('InspectTab slider')
        self.slider.valueChanged.connect(self.value_changed_handler)
        self.setSizePolicy(self.slider.sizePolicy())
        self.textbox = qt.QLineEdit(str(round(self.percent * 1000.0) / 10.0), self)
        self.textbox.setMaxLength(5)
        self.textbox.setObjectName('InspectTab textbox')
        font_metrics = qt.QLabel('100.0 %').fontMetrics()
        self.textbox.setFixedWidth(font_metrics.width('100.0 %'))
        self.textbox.editingFinished.connect(self.textbox_handler)
        #---------- The top bar is always visible ----------
        self.layout = qt.QHBoxLayout(self)
        self.layout.setObjectName('InspectTab layout')
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.textbox)
        self.layout.addWidget(self.slider)

    def get_percent(self):
        return self.percent

    def value_changed_handler(self, new_value):
        self.slider.setValue(new_value)
        self.textbox.clear()
        self.textbox.setText(f'{new_value/10.0}')
        self.percent = new_value / 1000.0
        self.callback(new_value)

    def reset_value(self):
        self.threshold_textbox.setText(f'{self.threshold}')
        self.threshold_slider.setValue(round(self.percent * 1000.0))

    def textbox_handler(self):
        # editingFinished signal handler
        txt = self.threshold_textbox.text()
        try:
            new_value = float(txt)
            if new_value >= 50.0 and new_value <= 100.0:
                self.percent = new_value / 100.0
            else:
                pass
        except ValueError as e:
            pass
        self.reset_value()

#---------------------------------------------------------------------------------------------------

class InspectTab(qt.QWidget):

    def __init__(self, parent):
        super(InspectTab, self).__init__(parent)
        self.main_view = parent
        self.distance_map = None
        self.setObjectName('InspectTab')
        # The layout of this widget is a top bar with a threshold slider and a graphics view or
        # message view. The graphics view or message view can be changed depending on whether
        # the target and pattern are both selected.
        self.layout = qt.QVBoxLayout(self)
        self.layout.setObjectName('InspectTab layout')
        self.slider = PercentSlider( \
            "Threshold %", \
            parent.get_config().threshold, \
            self.slider_handler \
          )
        self.layout.addWidget(self.slider)
        self.message_box = MessageBox('Please select SEARCH target image and PATTERN image.')
        self.layout.addWidget(self.message_box)
        self.image_preview = InspectImagePreview(self)
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

    def switch_image_display(self, pixmap):
        self.image_preview.set_pixmap(pixmap)

    def show_nothing(self):
        self.image_preview.hide()
        self.message_box.show()

    def show_image_preview(self):
        self.message_box.hide()
        self.image_preview.show()

    def show_distance_map(self, target_image, distance_map):
        self.switch_image_display(target_image)
        self.distance_map = distance_map
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
            print('WARNING: InspectTab.place_rectangles() called before distance_map was set')

    def save_selected(self):
        if self.distance_map is not None:
            output_dir = self.main_view.get_config().output_dir
            output_dir = \
                qt.QFileDialog.getExistingDirectory( \
                    self, "Write images to directory", \
                    str(output_dir), \
                    qt.QFileDialog.ShowDirsOnly \
              )
            output_dir = PurePath(output_dir)
            threshold = self.slider.get_percent()
            target_image = self.main_view.target.get_image()
            self.distance_map.write_all_cropped_images(target_image, threshold, output_dir)
        else:
            print('WARNING: InspectTab.save_selected() called before distance_map was set')

#---------------------------------------------------------------------------------------------------

class CachedCVImageLoader():
    """A tool for loading and caching image from a file into an OpenCV image buffer.
    """

    def __init__(self, notify, path=None):
        self.path   = path
        self.notify = notify
        self.image  = None

    def load_image(self, path=None):
        if path is None:
            path = self.path
            self.force_load_image(path)
        elif path != self.path:
            self.force_load_image(path)
        else:
            pass

    def force_load_image(self, path):
        self.image  = cv.imread(str(path))
        if path is not None:
            if self.image is None:
                self.path = None
                self.notify.showMessage( \
                    f'Failed to load image file {str(path)}' \
                  )
            else:
                #print(f'CachedCVImageLoader({str(self.path)}).force_load_image(str({path})) -> OK')
                self.path = path
        else:
            pass

    def get_path(self):
        return self.path

    def get_image(self):
        if self.image is None:
            print(f'warning: CachedCVImageLoader({str(self.path)}).get_image() returned None')
        return self.image

#---------------------------------------------------------------------------------------------------

class PatternMatcher(qt.QTabWidget):
    """The Qt Widget containing the GUI for the pattern matching program.
    """

    def __init__(self, config, parent=None):
        super(PatternMatcher, self).__init__(parent)
        #----------------------------------------
        # Setup the model
        self.config = config
        self.distance_map = None
        self.target_image_paths = search_target_images(self.config.inputs)
        self.cache   = {}
        self.notify  = qt.QErrorMessage(self)
        self.pattern = CachedCVImageLoader(self.notify, self.config.pattern)
        self.pattern.load_image()
        self.target  = CachedCVImageLoader(self.notify)
        #----------------------------------------
        # Setup the GUI
        self.setWindowTitle('Image Pattern Matching Kit')
        self.resize(800, 600)
        #self.tab_bar = qt.QTabWidget()
        self.setTabPosition(qt.QTabWidget.North)
        self.files_tab = FilesTab(self)
        self.pattern_tab = PatternSetupTab(config, self)
        self.inspect_tab = InspectTab(self)
        self.addTab(self.files_tab, "Search")
        self.addTab(self.pattern_tab, "Pattern")
        self.addTab(self.inspect_tab, "Inspect")
        self.currentChanged.connect(self.change_tab_handler)

    def get_config(self):
        return self.config

    def get_target_image_paths(self):
        return self.target_image_paths

    def add_target_image_paths(self, path_list):
        found_paths = search_target_images(path_list)
        self.target_image_paths = self.target_image_paths + found_paths
        self.files_tab.reset_paths_list(self.target_image_paths)

    def change_tab_handler(self, index):
        """Does the work of actually changing the GUI display to the "InspectTab".
        """
        super(PatternMatcher, self).setCurrentIndex(index)
        self.widget(index).update()

    def match_on_file(self, target_image_path):
        """This function is triggered when you double-click on an item in the image 
        list in the "FilesTab". It starts running the pattern matching algorithm and
        changes the display of the GUI over to the "InspectTab".
        """
        self.target.load_image(target_image_path)
        if (self.pattern.get_image() is not None) and (self.target.get_image() is not None):
            if target_image_path in self.cache:
                distance_map = self.cache[target_path]
            else:
                self.target.load_image(target_image_path)
                distance_map = DistanceMap(self.target.get_image(), self.pattern.get_image())
            self.inspect_tab.show_distance_map(self.files_tab.get_display_pixmap(), distance_map)
            self.setCurrentWidget(self.inspect_tab)
            return self.distance_map
        else:
            self.setCurrentWidget(self.pattern_tab)
            self.notify.showMessage( \
                'A pattern image must be set for matching on the selected image.' \
              )
            return None

    def show_pattern_image_path(self, path):
        self.pattern_tab.show_pattern_image_path(path)
        self.pattern.load_image(path)
        self.setCurrentWidget(self.pattern_tab)

    def set_pattern_pixmap(self, path, pixmap):
        self.pattern_tab.set_pattern_pixmap(path, pixmap)
        self.setCurrentWidget(self.pattern_tab)
        self.pattern.load_image(path)

####################################################################################################
# The main function, and functions for searching the filesystem for program input

def filename_filter(filepath):
    ext = filepath.suffix.lower()
    return (ext == '.png') or (ext == '.jpg') or (ext == '.jpeg')

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

def main():
    (config, remaining_argv) = arper.parse_known_args()
    print(config)
    #flatten_list(config.inputs)
    if config.gui:
        app = qt.QApplication(remaining_argv)
        appWindow = PatternMatcher(config)
        appWindow.show()
        sys.exit(app.exec_())
    else:
        target_image_paths = search_target_images(config.inputs)
        batch_crop_matched_patterns( \
            target_images=target_image_paths, \
            pattern_image_path=config.pattern, \
            results_dir=config.output_dir, \
            threshold=config.threshold, \
            save_distance_map=config.save_map \
          )

####################################################################################################

if __name__ == '__main__':
    main()
