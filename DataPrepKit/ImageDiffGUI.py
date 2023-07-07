import DataPrepKit.ImageDiff as patm
from DataPrepKit.PercentSlider import PercentSlider
from DataPrepKit.FileSetGUI import FileSetGUI, qt_modal_image_file_selection
from DataPrepKit.ContextMenuItem import context_menu_item
from DataPrepKit.SimpleImagePreview import SimpleImagePreview
from DataPrepKit.CropRectTool import CropRectTool

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
        self.app_model.toggle_show_diff()
        
    def use_current_item_as_reference(self):
        path = self.current_item_path()
        print(f'FilesTab.use_current_item_as_reference() #("{path}")')
        self.app_model.set_reference_image_path(path)
        self.main_view.update_reference_pixmap()

#---------------------------------------------------------------------------------------------------

class ReferencePreview(SimpleImagePreview):
    """A QGraphicsView for displaying the reference image. It does not
    inherit from InspectImagePreview because it has different behavior
    for displaying the image, and for drag and drop. This class may be
    removed and replaced with a more featureful versino of
    InspectImagePreview in the future.
    """

    def __init__(self, app_model, main_view):
        super().__init__()
        super(SimpleImagePreview, self).__init__(main_view)
        self.app_model = app_model
        self.main_view = main_view
        self.enable_drop_handlers(True)

    def clear(self):
        self.crop_rect_tool.clear()
        super(ReferencePreview, self).clear()

    def redraw(self):
        super(ReferencePreview, self).redraw()
        self.crop_rect_tool.redraw()

    def dragEnterEvent(self, event):
        self.main_view.dragEnterEvent(event)

    def dropEvent(self, event):
        self.main_view.dropEvent(event)

    def update_reference_pixmap(self):
        """Re-read the file path for the reference image from the app_model
        and update the view to display the image file at that path."""
        reference = self.app_model.get_reference()
        self.set_filepath(reference.get_path())

    def load_reference_image(self, path):
        """Set the reference image in the app_model and also update the view
        to display the image file at that path."""
        print(f'ReferencePreview.load_reference_image({path!s})')
        self.app_model.load_reference_image(path)
        self.set_filepath(path)

    def drop_url_handler(self, urls):
        if len(urls) > 0:
            self.load_reference_image(PurePath(urls[0]))
        else:
            pass

    def drop_text_handler(self, text):
        self.load_reference_image(PurePath(text))

#---------------------------------------------------------------------------------------------------

class ReferenceSetupTab(qt.QWidget):

    def __init__(self, app_model, main_view):
        super().__init__(main_view)
        self.setObjectName("ReferenceSetupTab")
        #self.setAcceptDrops(True)
        self.app_model    = app_model
        self.main_view    = main_view
        self.layout       = qt.QHBoxLayout(self)
        self.preview_view = ReferencePreview(app_model, self)
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

    def load_reference_image(self, path):
        self.preview_view.load_reference_image(path)

    def open_reference_file_handler(self):
        #target_dir = self.app_model.get_config().reference
        path = qt_modal_image_file_selection(self, "Open images in which to search for patterns")
        print(f'ReferenceSetupTab.open_reference_file_handler() #(paths = {path})')
        if len(path) == 1:
            self.load_reference_image(path[0])
        elif len(path) > 1:
            self.load_reference_image(path[0])
            print(f'WARNING: more than one file selected, only using the first file: "{path[0]}"')
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

