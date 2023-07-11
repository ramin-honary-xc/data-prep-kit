import DataPrepKit.ImageDiff as patm
from DataPrepKit.PercentSlider import PercentSlider
from DataPrepKit.FileSetGUI import FileSetGUI, qt_modal_image_file_selection
from DataPrepKit.ContextMenuItem import context_menu_item
from DataPrepKit.ReferenceImagePreviewGUI import ReferenceImagePreview
from DataPrepKit.CropRectTool import CropRectTool
from DataPrepKit.GUIHelpers import numpy_array_to_QPixmap

import pathlib
from pathlib import PurePath

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

####################################################################################################
# The Qt GUI

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
            fileset=app_model.get_fileset(),
            action_label='Show this images differences',
          )
        self.app_model = app_model
        ## Action: Use as reference
        self.use_as_reference = context_menu_item(
            "Use as reference",
            self.use_current_item_as_reference,
            qgui.QKeySequence.Find,
          )
        self.list_widget.addAction(self.use_as_reference)
        self.image_preview.addAction(self.use_as_reference)

    def activation_handler(self, path):
        print(f'FilesTab.activation_handler("{path!s}")')
        self.app_model.toggle_show_diff()
        self.item_change_handler(path)

    def item_change_handler(self, path):
        self.app_model.set_compare_image_path(path)
        image_buffer = self.app_model.get_display_image()
        if image_buffer is None:
            print(f'FilesTab.item_change_handler("{path!s}") #(self.app_model.get_display_image() returned None)')
            pass
        else:
            image_preview = self.get_image_preview()
            image_preview.set_image_buffer(path, numpy_array_to_QPixmap(image_buffer))
        
    def use_current_item_as_reference(self):
        path = self.current_item_path()
        print(f'FilesTab.use_current_item_as_reference() #("{path}")')
        self.app_model.set_reference_image_path(path)
        self.main_view.update_reference_pixmap()

#---------------------------------------------------------------------------------------------------

class ReferenceSetupTab(qt.QWidget):

    def __init__(self, app_model, main_view):
        super().__init__(main_view)
        self.setObjectName("ReferenceSetupTab")
        #self.setAcceptDrops(True)
        self.app_model    = app_model
        self.main_view    = main_view
        self.layout       = qt.QHBoxLayout(self)
        self.preview_view = ReferenceImagePreview(app_model, self)
        self.layout.addWidget(self.preview_view)
        ## Action: open image files
        self.open_reference_file = context_menu_item(
            "Open reference file",
            self.open_reference_file_handler,
            qgui.QKeySequence.Open,
          )
        self.preview_view.addAction(self.open_reference_file)

    def update_reference_pixmap(self):
        self.preview_view.update_reference_pixmap()

    def set_reference_image_path(self, path):
        print(f'ReferenceSetupTab.set_reference_image_path("{path!s}")')
        self.preview_view.set_reference_image_path(path)
        self.app_model.set_reference_image_path(path)

    def open_reference_file_handler(self):
        #target_dir = self.app_model.get_config().reference
        paths = qt_modal_image_file_selection(self, "Open images in which to search for patterns")
        print(f'ReferenceSetupTab.open_reference_file_handler() #(paths = {paths})')
        if len(paths) > 0:
            self.set_reference_image_path(paths[0])
            if len(paths) > 1:
                print(f'WARNING: more than one file selected, only using the first file: "{path[0]}"')
            else:
                pass
        else:
            print(f'ReferenceSetupTab.open_reference_file_handler() #(file selector dialog box returned empty list)')
            pass

#---------------------------------------------------------------------------------------------------

class ImageDiffGUI(qt.QTabWidget):
    """The Qt Widget containing the GUI for the whole reference matching program.
    """

    def __init__(self, app_model, main_view=None):
        super().__init__(main_view)
        self.app_model = app_model
        #----------------------------------------
        # Setup the GUI
        self.notify = qt.QErrorMessage(self)
        self.setWindowTitle("Image Reference Matching Kit")
        self.resize(800, 600)
        self.setTabPosition(qt.QTabWidget.North)
        self.files_tab = FilesTab(app_model, self)
        self.reference_tab = ReferenceSetupTab(app_model, self)
        self.addTab(self.files_tab, "Search")
        self.addTab(self.reference_tab, "Reference")
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

    def show_reference_tab(self):
        self.setCurrentWidget(self.reference_tab)

    def update_reference_pixmap(self):
        self.reference_tab.update_reference_pixmap()
        self.show_reference_tab()

