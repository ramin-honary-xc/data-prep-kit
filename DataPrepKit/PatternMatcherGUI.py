import DataPrepKit.utilities as util
import DataPrepKit.PatternMatcher as patm
from DataPrepKit.PercentSlider import PercentSlider
from DataPrepKit.FileSetGUI import FileSetGUI, qt_modal_image_file_selection
from DataPrepKit.ContextMenuItem import context_menu_item
from DataPrepKit.SimpleImagePreview import SimpleImagePreview
from DataPrepKit.ReferenceImagePreviewGUI import ReferenceImagePreview
from DataPrepKit.CropRectTool import CropRectTool
from DataPrepKit.FileSet import image_file_suffix_set

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
        self.feature_pen = qgui.QPen(qgui.QColor(255, 0, 0, 255))
        self.feature_pen.setCosmetic(True)
        self.feature_pen.setWidth(3)
        self.crop_pen = qgui.QPen(qgui.QColor(0, 255, 0, 255))
        self.crop_pen.setCosmetic(True)
        self.crop_pen.setWidth(3)

    def clear(self):
        self.clear_rectangles()
        super(InspectImagePreview, self).clear()

    def redraw(self):
        super(InspectImagePreview, self).redraw()
        self.clear_rectangles()
        self.place_rectangles()

    def clear_rectangles(self):
        scene = self.get_scene()
        #print(f'InspectImagePreview.clear_rectangles() #(clear {len(self.rect_items)} items)')
        for rect in self.rect_items:
            scene.removeItem(rect)
        self.rect_items = []

    def place_rectangles(self):
        scene = self.get_scene()
        point_list = self.app_model.get_matched_points()
        ref_rect = self.app_model.get_reference_rect()
        if ref_rect is None:
            self.main_view.error_message('Must first define a reference image in the "Search" tab.')
        else:
            (x0, y0, width, height) = ref_rect
            crop_regions = self.app_model.get_crop_regions()
            pen = self.feature_pen
            #print(f'InspectImagePreview.place_rectangles() #(add {len(rectangle_list)} items)')
            for (x,y) in point_list:
                scene.addRect(x, y, width, height, pen)
            #------------------
            if crop_regions is not None:
                pen = self.crop_pen
                for (label, (x,y,width,height)) in crop_regions.items():
                    for (x_off,y_off) in point_list:
                        scene.addRect(x+x_off, y+y_off, width, height, pen)
            else:
                pass

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
            self.use_current_item_as_reference,
            qgui.QKeySequence.Find,
          )
        self.list_widget.addAction(self.use_as_pattern)
        if self.image_display is not None:
            self.image_display.addAction(self.use_as_pattern)
        else:
            pass
        self.setSizePolicy(
            qt.QSizePolicy(
                qt.QSizePolicy.Preferred,
                qt.QSizePolicy.Preferred,
              ),
          )

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

    def use_current_item_as_reference(self):
        path = self.current_item_path()
        print(f'FilesTab.use_current_item_as_reference() #("{path}")')
        self.app_model.set_reference_image_path(path)
        self.main_view.update_reference_pixmap()

#---------------------------------------------------------------------------------------------------

class PatternPreview(ReferenceImagePreview):

    def __init__(self, app_model, main_view):
        super().__init__(app_model, main_view)
        self.crop_rect_tool = CropRectTool(self.get_scene(), self.change_crop_rect)
        self.set_mouse_mode(self.crop_rect_tool)
        self.setSizePolicy(
            qt.QSizePolicy(
                qt.QSizePolicy.Expanding,
                qt.QSizePolicy.Preferred,
              ),
          )

    def clear(self):
        self.crop_rect_tool.clear()
        super(ReferenceImagePreview, self).clear()

    def redraw(self):
        super(ReferenceImagePreview, self).redraw()
        self.crop_rect_tool.redraw()

    def change_crop_rect(self, rect):
        if rect is None:
            self.app_model.set_reference_rect(None)
        else:
            (x0, y0, width, height) = rect
            if width == 0 or height == 0:
                self.app_model.set_reference_rect(None)
            else:
                self.app_model.set_reference_rect(rect)

#---------------------------------------------------------------------------------------------------

class PatternSetupTab(qt.QWidget):

    def __init__(self, app_model, main_view):
        screenWidth = qgui.QGuiApplication.primaryScreen().virtualSize().width()
        super().__init__(main_view)
        self.setObjectName("PatternSetupTab")
        self.setAcceptDrops(True)
        self.app_model    = app_model
        self.main_view    = main_view
        self.layout       = qt.QHBoxLayout(self)
        self.preview_view = PatternPreview(app_model, self)
        self.active_selector_count = 0
        self.active_selector = qt.QListWidget(self)
        self.active_selector.setObjectName("Active Selector")
        self.reset_selector_items()
        self.splitter     = qt.QSplitter(qcore.Qt.Orientation.Horizontal, self)
        self.splitter.setObjectName("PatternTab splitter")
        self.splitter.insertWidget(0, self.active_selector)
        self.splitter.insertWidget(1, self.preview_view)
        self.splitter.setSizes([round(screenWidth/2), round(screenWidth/2)])
        self.layout.addWidget(self.splitter)
        self.setAcceptDrops(True)
        ## Action: open image files
        self.open_pattern_file = context_menu_item(
            "Open pattern file",
            self.open_pattern_file_handler,
            qgui.QKeySequence.Open,
          )
        self.preview_view.addAction(self.open_pattern_file)
        ## Action: add new crop region
        self.do_add_selector_item = context_menu_item(
            'New crop region',
            self.add_selector_item_action,
            qgui.QKeySequence.InsertParagraphSeparator,
          )
        self.active_selector.addAction(self.do_add_selector_item)
        #----------
        self.do_delete_selector_item = context_menu_item(
            'Delete crop region',
            self.delete_selector_item_action,
            qgui.QKeySequence.Delete,
          )
        self.active_selector.addAction(self.do_delete_selector_item)

    def reset_selector_items(self):
        # Make sure "Feautres" is always the first list item.
        self.active_selector.clear()
        self.features_list_item = qt.QListWidgetItem('#Features')
        self.active_selector.addItem(self.features_list_item)
        crop_regions = self.app_model.get_crop_regions()
        for key in crop_regions.keys():
            item = qt.QListWidgetItem(key)
            self.active_selector.addItem(item)

    def add_selector_item(self, name, edit=False):
        crop_regions = self.app_model.get_crop_regions()
        if name in crop_regions:
            print(f'Cannot add selector item named "{name}", already exists')
        else:
            crop_regions[name] = self.app_model.get_reference_rect()
            item = qt.QListWidgetItem(name, parent=self.active_selector)
            if edit:
                self.active_selector.editItem(item)
            else:
                pass

    def add_selector_item_action(self):
        """Calls self.add_selector_item() from the GUI."""
        self.active_selector_count += 1
        self.add_selector_item(f'region-{self.active_selector_count}', True)

    def delete_selector_item_action(self):
        crop_regions = self.app_model.get_crop_regions()
        for item in self.active_selector.selectedItems():
            if item.text() != '#Features':
                self.active_selector.takeItem(self.active_selector.row(item))
            else:
                pass
            text = item.text()
            if text in crop_regions:
                del crop_regions[text]
            else:
                pass

    def update_reference_pixmap(self):
        self.preview_view.update_reference_pixmap()

    def set_reference_image_path(self, path):
        #print(f'FilesTab.use_current_item_as_pattern() #("{path}")')
        self.app_model.set_reference_image_path(path)
        self.update_reference_pixmap()

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

    def add_crop_region(self, rect, label):
        self.active_selector.addItem(qt.QListWidgetItem('Crop'))
        

#---------------------------------------------------------------------------------------------------

class EncodingMenu(qt.QGroupBox):
    """Group box showing the popup-down menu where the image encoding can be selected."""

    def __init__(self, title, app_model, parent):
        super().__init__(title, parent=parent)
        self.app_model = app_model
        self.setSizePolicy(
            qt.QSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Minimum)
          )
        self.layout = qt.QHBoxLayout(self)
        self.menu = qt.QMenu('Choose Encoding', parent=self)
        # Add most popular encodings at the top.
        self.menu.addAction('PNG')
        self.menu.addAction('BMP')
        self.menu.addAction('JPG')
        self.menu.addSeparator()
        # Add all other encodings, it's OK to insert duplicates items,
        # the text of the menu item is used to decide the action.
        for item in image_file_suffix_set:
            self.menu.addAction(item.upper())
        self.menu.triggered.connect(self.menu_item_selected)
        self.popup_menu = qt.QPushButton(self)
        self.popup_menu.setText('PNG')
        self.popup_menu.setMenu(self.menu)
        self.layout.addWidget(self.popup_menu)
        self.layout.setSizeConstraint(qt.QLayout.SizeConstraint.SetFixedSize)
        self.setLayout(self.layout)

    def menu_item_selected(self, action):
        print(f'InspectTabControl.menu_item_selected("{action.text()}")')
        self.app_model.set_file_encoding(action.text())
        self.popup_menu.setText(action.text())


class InspectTabControl(qt.QWidget):
    """The upper control bar for the Inspect tab"""

    def __init__(self, app_model, inspect_tab):
        super().__init__(inspect_tab)
        self.setObjectName('InspectTab controls')
        self.app_model = app_model
        self.inspect_tab = inspect_tab
        self.setSizePolicy(
            qt.QSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Minimum)
          )
        self.layout = qt.QHBoxLayout(self)
        config = app_model.get_config()
        # ---------- setup slider ----------
        self.slider = PercentSlider(
            "Threshold %",
            config.threshold,
            inspect_tab.slider_handler,
          )
        # ---------- setup popup-menu ----------
        self.encoding_menu = EncodingMenu('Encoding', self.app_model, parent=self)
        # ---------- lay out the widgets ----------
        self.layout.addWidget(self.encoding_menu)
        self.layout.addWidget(self.slider)


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
        self.layout.setObjectName('InspectTab layout')
        self.control_widget = InspectTabControl(app_model, self)
        self.slider = self.control_widget.slider
        self.layout.addWidget(self.control_widget)
        self.message_box = MessageBox("Please select SEARCH target image and PATTERN image.")
        self.layout.addWidget(self.message_box)
        self.image_display = InspectImagePreview(self.app_model, self)
        image_display_size_policy = self.image_display.sizePolicy()
        image_display_size_policy.setRetainSizeWhenHidden(True)
        self.image_display.setSizePolicy(image_display_size_policy)
        self.image_display.hide()
        self.layout.addWidget(self.image_display)
        #---------- Setup context menus ----------
        self.do_save_selected = context_menu_item(
            "Save selected regions",
            self.save_selected,
            qgui.QKeySequence.Save,
          )
        self.image_display.addAction(self.do_save_selected)
        #----------
        self.do_save_selected_all = context_menu_item(
            "Save selected regions, all files",
            self.save_selected_all,
            qgui.QKeySequence.SaveAs,
          )
        self.image_display.addAction(self.do_save_selected_all)
        #----------
        self.do_move_next_image = context_menu_item(
            "Search Next Image",
            self.search_next_image,
            qgui.QKeySequence.MoveToNextPage,
          )
        self.image_display.addAction(self.do_move_next_image)
        #----------
        self.do_move_previous_image = context_menu_item(
            "Search Previous Image",
            self.search_previous_image,
            qgui.QKeySequence.MoveToPreviousPage,
          )
        self.image_display.addAction(self.do_move_previous_image)

    def slider_handler(self, new_value):
        threshold = self.slider.get_percent()
        if threshold is not None:
            self.app_model.change_threshold(threshold)
            if self.app_model.get_reference_rect() is not None:
                self.image_display.redraw()
            else:
                pass
        else:
            pass

    def show_nothing(self):
        self.image_display.hide()
        self.message_box.show()

    def show_image_display(self):
        self.message_box.hide()
        self.image_display.show()

    def show_distance_map(self):
        """Draws the target image and any matching pattern rectangles into the
        image_display window."""
        self.distance_map = self.app_model.get_distance_map()
        target = self.distance_map.get_target()
        if target is not None:
            path = target.get_path()
        else:
            path = None
        self.image_display.set_filepath(path)
        self.image_display.redraw()
        self.show_image_display()
        self.do_save_selected.setEnabled(True)

    def modal_prompt_get_directory(self, init_dir):
        output_dir = \
            qt.QFileDialog.getExistingDirectory(
                self, "Write images to directory",
                init_dir,
                qt.QFileDialog.ShowDirsOnly,
              )
        return PurePath(output_dir)

    def get_files_list(self):
        return self.main_view.files_tab.get_list_widget()

    def current_file_index(self):
        """Looks into the files tab and returns the index of the currently
        selected item, along with the number of items."""
        listwidget = self.get_files_list()
        return (listwidget.currentRow(), listwidget.count())

    def save_selected(self):
        if self.distance_map is not None:
            output_dir = self.app_model.get_config().output_dir
            output_dir = self.modal_prompt_get_directory(str(output_dir))
            self.app_model.set_results_dir(PurePath(output_dir))
            threshold = self.slider.get_percent()
            target_image = self.app_model.target.get_image()
            crop_regions = self.app_model.get_crop_regions()
            self.distance_map.write_all_cropped_images(
                target_image,
                threshold,
                crop_regions,
                output_dir,
              )
        else:
            print('WARNING: InspectTab.save_selected() called before distance_map was set')

    def save_selected_all(self):
        output_dir = self.app_model.get_config().output_dir
        output_dir = self.modal_prompt_get_directory(str(output_dir))
        self.app_model.set_results_dir(PurePath(output_dir))
        self.app_model.batch_crop_matched_references()

    def search_next_image(self):
        (row, count) = self.current_file_index()
        if row is None:
            self.main_view.error_messge('Please select an image in the "Files" tab')
        elif row+1 >= count:
            self.main_view.error_message('No further images in "Files" tab, currently viewing last image')
        else:
            listwidget = self.get_files_list()
            listwidget.setCurrentRow(row+1)
            item = listwidget.item(row+1)
            listwidget.setCurrentItem(item)
            self.main_view.files_tab.activation_handler(item.get_path())

    def search_previous_image(self):
        (row, count) = self.current_file_index()
        if row is None:
            self.main_view.error_messge('Please select an image in the "Files" tab')
        elif row-1 <= 0:
            self.main_view.error_message('No further images in "Files" tab, currently viewing last image')
        else:
            listwidget = self.get_files_list()
            listwidget.setCurrentRow(row-1)
            item = listwidget.item(row-1)
            listwidget.setCurrentItem(item)
            self.main_view.files_tab.activation_handler(item.get_path())

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
        self.files_tab.default_image_display_widget()
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

    def update_reference_pixmap(self):
        self.pattern_tab.update_reference_pixmap()
        self.show_pattern_tab()

