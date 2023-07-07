import DataPrepKit.utilities as util
import DataPrepKit.PatternMatcher as patm
from DataPrepKit.PercentSlider import PercentSlider
from DataPrepKit.FileSetGUI import FileSetGUI, qt_modal_image_file_selection
from DataPrepKit.ContextMenuItem import context_menu_item
from DataPrepKit.SimpleImagePreview import SimpleImagePreview
from DataPrepKit.ReferenceImagePreviewGUI import ReferenceImagePreview
from DataPrepKit.CropRectTool import CropRectTool

from pathlib import PurePath

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

####################################################################################################
# The Qt GUI

class InspectImagePreview(SimpleImagePreview):

    def __init__(self, app_model, parent):
        super(InspectImagePreview, self).__init__(parent)
        self.app_model = app_model
        self.rect_items = []
        self.pen = qgui.QPen(qgui.QColor(255, 0, 0, 255))
        self.pen.setCosmetic(True)
        self.pen.setWidth(3)

    def clear(self):
        self.clear_rectangles()
        super(InspectImagePreview, self).clear()

    def redraw(self):
        super(InspectImagePreview, self).redraw()
        self.clear_rectangles()
        self.place_rectangles()

    def clear_rectangles(self):
        scene = self.get_scene()
        print(f'InspectImagePreview.clear_rectangles() #(clear {len(self.rect_items)} items)')
        for rect in self.rect_items:
            scene.removeItem(rect)
        self.rect_items = []

    def place_rectangles(self):
        scene = self.get_scene()
        rectangle_list = self.app_model.get_matched_regions()
        print(f'InspectImagePreview.place_rectangles() #(add {len(rectangle_list)} items)')
        for rectangle in rectangle_list:
            bounds = rectangle.get_point_and_size()
            scene.addRect(*bounds, self.pen)

#---------------------------------------------------------------------------------------------------

class MessageBox(qt.QWidget):

    def __init__(self, message):
        super().__init__()
        self.layout = qt.QHBoxLayout(self)
        self.message = qt.QLabel(message)
        self.layout.addWidget(self.message)

class FilesTab(FileSetGUI):

    def __init__(self, app_model, main_view):
        super(FilesTab, self).__init__(
            main_view,
            fileset=app_model.get_target_fileset(),
            action_label='Search within this image',
          )
        self.app_model = app_model
        ## Action: Use as pattern
        self.use_as_pattern = context_menu_item(
            "Use as pattern",
            self.use_current_item_as_pattern,
            qgui.QKeySequence.Find,
          )
        self.list_widget.addAction(self.use_as_pattern)
        self.image_preview.addAction(self.use_as_pattern)

    def activation_handler(self, path):
        self.app_model.set_target_image_path(path)
        self.app_model.match_on_file()
        distance_map = self.app_model.get_distance_map()
        if distance_map:
            self.main_view.show_distance_map()
            self.main_view.show_inspect_tab()
        else:
            self.main_view.show_pattern_tab()
            self.main_view.error_message(
                "A pattern image must be set for matching on the selected image.",
              )

    def use_current_item_as_pattern(self):
        path = self.current_item_path()
        print(f'FilesTab.use_current_item_as_pattern() #("{path}")')
        self.app_model.set_reference_image_path(path)
        self.main_view.update_pattern_pixmap()

#---------------------------------------------------------------------------------------------------

class PatternPreview(ReferenceImagePreview):

    def __init__(self, app_model, main_view):
        super().__init__(app_model, main_view)
        self.crop_rect_tool = CropRectTool(self.get_scene(), self.change_crop_rect)
        self.set_mouse_mode(self.crop_rect_tool)

    def clear(self):
        self.crop_rect_tool.clear()
        super(PatternPreview, self).clear()

    def redraw(self):
        super(PatternPreview, self).redraw()
        self.crop_rect_tool.redraw()

    def change_crop_rect(self, rect):
        self.app_model.set_pattern_rect(rect)

#---------------------------------------------------------------------------------------------------

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
        self.setAcceptDrops(True)
        ## Action: open image files
        self.open_pattern_file = context_menu_item(
            "Open pattern file",
            self.open_pattern_file_handler,
            qgui.QKeySequence.Open,
          )
        self.preview_view.addAction(self.open_pattern_file)

    def update_pattern_pixmap(self):
        self.preview_view.update_pattern_pixmap()

    def set_reference_image_path(self, path):
        print(f'FilesTab.use_current_item_as_pattern() #("{path}")')
        self.app_model.set_reference_image_path(path)
        self.update_pattern_pixmap()

    def open_pattern_file_handler(self):
        target_dir = self.app_model.get_config().pattern
        urls = qt_modal_image_file_selection(
            self,
            default_dir=target_dir,
            message='Open images in which to search for patterns',
          )
        if len(urls) > 0:
            self.set_reference_image_path(urls[0])
            if len(urls) > 1:
                print(f'WARNING: multiple files selected as pattern path, using only first one "{urls[0]}"')
            else:
                pass
        else:
            print(f'PatternSetupTab.open_pattern_file_handler() #(file selection dialog returned empty list)')

#---------------------------------------------------------------------------------------------------

class InspectTab(qt.QWidget):
    """This tab shows an image on which the pattern matching computation
    has been run, and outlines the matched areas of the image with a
    red rectangle."""

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
        self.slider = PercentSlider(
            "Threshold %",
            config.threshold,
            self.slider_handler,
          )
        self.layout.addWidget(self.slider)
        self.message_box = MessageBox("Please select SEARCH target image and PATTERN image.")
        self.layout.addWidget(self.message_box)
        self.image_preview = InspectImagePreview(self.app_model, self)
        self.image_preview.hide()
        self.layout.addWidget(self.image_preview)
        #---------- Setup context menus ----------
        self.do_save_selected = context_menu_item(
            "Save all selected regions",
            self.save_selected,
            qgui.QKeySequence.Save,
          )
        self.image_preview.addAction(self.do_save_selected)

    def slider_handler(self, new_value):
        threshold = self.slider.get_percent()
        if threshold is not None:
            self.app_model.change_threshold(threshold)
            self.image_preview.redraw()
        else:
            pass

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
        target = self.distance_map.get_target()
        if target is not None:
            path = target.get_path()
        else:
            path = None
        self.image_preview.set_filepath(path)
        self.image_preview.redraw()
        self.show_image_preview()
        self.do_save_selected.setEnabled(True)

    def modal_prompt_get_directory(self, init_dir):
        output_dir = \
            qt.QFileDialog.getExistingDirectory(
                self, "Write images to directory",
                init_dir,
                qt.QFileDialog.ShowDirsOnly,
              )
        return PurePath(output_dir)

    def save_selected(self):
        if self.distance_map is not None:
            output_dir = self.app_model.get_config().output_dir
            output_dir = self.modal_prompt_get_directory(str(output_dir))
            threshold = self.slider.get_percent()
            target_image = self.app_model.target.get_image()
            self.distance_map.write_all_cropped_images(target_image, threshold, output_dir)
        else:
            print('WARNING: InspectTab.save_selected() called before distance_map was set')

#---------------------------------------------------------------------------------------------------

class PatternMatcherView(qt.QTabWidget):
    """The Qt Widget containing the GUI for the whole pattern matching program.
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

