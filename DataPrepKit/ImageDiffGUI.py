import DataPrepKit.ImageDiff as patm
from DataPrepKit.PercentSlider import PercentSlider
import DataPrepKit.FileSetGUI as fs
from DataPrepKit.SimpleImagePreview import ImagePreview
from DataPrepKit.ContextMenuItem import context_menu_item
from DataPrepKit.ReferenceImagePreviewGUI import ReferenceImagePreview
from DataPrepKit.CropRectTool import CropRectTool
from DataPrepKit.GUIHelpers import numpy_array_to_QPixmap

import pathlib
from pathlib import Path, PurePath

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

class FilesTab(fs.FileSetGUI):

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
        self._infobox = qt.QLineEdit()
        self._infobox.setReadOnly(True)
        self._display = ImagePreview()
        self.set_image_display_widget(self._display)
        self._display.set_info_widget(self._infobox)
        self._display.setContextMenuPolicy(qcore.Qt.ContextMenuPolicy.ActionsContextMenu)
        #---------- Setup context menus ----------
        self.save_selected_action = context_menu_item(
            "Save diff image for selected file",
            self.do_save_selected,
            qgui.QKeySequence.Save,
          )
        self._display.addAction(self.save_selected_action)
        #---------------
        self.save_all_action = context_menu_item(
            "Save diff image for every file",
            self.do_save_all,
            qgui.QKeySequence.SaveAs,
          )
        self._display.addAction(self.save_all_action)
        self.get_list_widget().addAction(self.save_all_action)

    def default_image_display_widget(self):
        return super(FilesTab, self).default_image_display_widget()

    def set_image_display_widget(self, image_display):
        super(FilesTab, self).set_image_display_widget(image_display)
        if self.image_display is not None:
            self.image_display.addAction(self.use_as_reference)
        else:
            pass

    def activation_handler(self, path):
        #print(f'{self.__class__.__name__}.activation_handler("{path!s}")')
        self.app_model.toggle_show_diff()
        self.item_change_handler(path)

    def item_change_handler(self, path):
        self.app_model.set_compare_image_path(path)
        self.app_model.update_diff_image()
        (image_buffer, similarity) = self.app_model.get_display_image()
        image_display = self.get_image_display()
        if image_display is not None:
            if image_buffer is None:
                image_display.clear()
                self._infobox.clear()
            else:
                image_display.set_image_buffer(path, numpy_array_to_QPixmap(image_buffer))
        else:
            pass
        if similarity is not None:
            self._infobox.clear()
            similarity = round(similarity * 100000) / 1000
            self._infobox.setText(f'similarity = {similarity!s}%')
        else:
            pass
        
    def use_current_item_as_reference(self):
        path = self.current_item_path()
        #print(f'{self.__class__.__name__}.use_current_item_as_reference() #("{path}")')
        self.app_model.set_reference_image_path(path)
        self.main_view.update_reference_pixmap()

    def modal_prompt_get_directory(self, init_dir):
        output_dir = \
            qt.QFileDialog.getExistingDirectory(
                self, "Write images to directory",
                str(init_dir),
                qt.QFileDialog.ShowDirsOnly,
              )
        return PurePath(output_dir)

    def modal_prompt_save_file(self, init_file):
        out_path = \
            qt.QFileDialog.getSaveFileName(
                self, "Save diff image for selected file",
                str(init_file),
                fs.qt_image_file_filter_string,
              )
        #print(f'FilesTab.model_prompt_save_file() $({out_path})')
        if out_path is None:
            return None
        else:
            return PurePath(out_path[0])

    def do_save_selected(self):
        out_path = self.modal_prompt_save_file(
            self.app_model.get_diff_image().get_path(),
          )
        if out_path is not None:
            self.app_model.save_diff_image(filepath=out_path)
        else:
            pass

    def do_save_all(self):
        if self.app_model.get_reference().get_raw_image() is not None:
            output_dir = self.modal_prompt_get_directory(Path.cwd())
            self.app_model.save_all(output_dir=output_dir)
        else:
            # TODO: display error dialog box
            print(f'WARNING: no reference image selected')

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
        #print(f'{self.__class__.__name__}.set_reference_image_path("{path!s}")')
        self.preview_view.set_reference_image_path(path)
        self.app_model.set_reference_image_path(path)

    def open_reference_file_handler(self):
        #target_dir = self.app_model.get_config().reference
        paths = fs.qt_modal_image_file_selection(self, "Open images in which to search for patterns")
        #print(f'{self.__class__.__name__}.open_reference_file_handler() #(paths = {paths})')
        if len(paths) > 0:
            self.set_reference_image_path(paths[0])
            if len(paths) > 1:
                print(f'WARNING: more than one file selected, only using the first file: "{path[0]}"')
            else:
                pass
        else:
            #print(f'{self.__class__.__name__}.open_reference_file_handler() #(file selector dialog box returned empty list)')
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

