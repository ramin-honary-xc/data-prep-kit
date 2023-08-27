import DataPrepKit.utilities as util
import DataPrepKit.PatternMatcher as patm
from DataPrepKit.PercentSlider import PercentSlider
from DataPrepKit.FileSetGUI import FileSetGUI, qt_modal_image_file_selection
from DataPrepKit.ContextMenuItem import context_menu_item
from DataPrepKit.SimpleImagePreview import SimpleImagePreview
from DataPrepKit.ReferenceImagePreviewGUI import ReferenceImagePreview
from DataPrepKit.CropRectTool import CropRectTool
from DataPrepKit.ImageMask

from pathlib import PurePath

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

####################################################################################################
# The Qt GUI

class FilesTab(FileSetGUI):

    def __init__(self, app_model, main_view):
        super(FilesTab, self).__init__(
            main_view,
            fileset=app_model.get_target_fileset(),
            action_label='Search within this image',
          )




class PatternMatcherView(qt.QTabWidget):
    """The Qt Widget containing the GUI for the whole pattern matching program.
    """

    def __init__(self, app_model, main_view=None):
        super().__init__(main_view)
        self.app_model = app_model
        self.notify = qt.QErrorMessage(self)
        self.setTabPosition(qt.QTabWidget.North)
        self.files_tab = FilesTab(app_model, self)
        self.files_tab.default_image_display_widget()
        self.pattern_tab = PatternSetupTab(app_model, self)
        self.inspect_tab = InspectTab(app_model, self)
        self.addTab(self.files_tab, "Search")
        self.addTab(self.pattern_tab, "Pattern")
        self.addTab(self.inspect_tab, "Inspect")
        self.currentChanged.connect(self.change_tab_handler)

