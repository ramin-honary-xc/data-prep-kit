from DataPrepKit.FileSetGUI import FileSetGUI, qt_modal_image_file_selection
from DataPrepKit.EncodingMenu import EncodingMenu
from DataPrepKit.SimpleImagePreview import SimpleImagePreview

import PyQt5.QtWidgets as qt
import PyQt5.QtCore as qcore

####################################################################################################

class ResizeConfig(qt.QWidget):
    """A widget where a "width" and "height" parameter can be entered as
    text fields, layed out horizontally so it can fill in space at the
    top of the window.

    When the text fields change, the "app_model" methods
    "set_resize_width()" and "set_resize_height()" are called, so be
    sure these methods exist in whatever object you pass as the
    "app_model" argument.

    On initialization, the "app_model" methods "get_resize_width()"
    and "get_resize_height()" are called, so be sure these methods
    exist in whatever object you pass as the "app_model" argument."""

    def __init__(self, app_model, editable=True, parent=None):
        super().__init__()
        self.app_model = app_model
        #----------- Construct widgets ------------
        self.setObjectName("config-resize-width-height-text-fields")
        self.width_label      = qt.QLabel("Width:", parent=self)
        self.height_label     = qt.QLabel("Height:", parent=self)
        resize_width          = self.app_model.get_resize_width()
        resize_height         = self.app_model.get_resize_height()
        init_width_text       = "" if resize_width  is None else str(resize_width)
        init_height_text      = "" if resize_height is None else str(resize_height)
        self.width_line_edit  = qt.QLineEdit(init_width_text, parent=self)
        self.height_line_edit = qt.QLineEdit(init_height_text, parent=self)
        #----------- Layout all widgets ------------
        self.layout           = qt.QHBoxLayout(self)
        self.layout.addWidget(self.width_label)
        self.layout.addWidget(self.width_line_edit)
        self.layout.addWidget(self.height_label)
        self.layout.addWidget(self.height_line_edit)
        #----------- Connect event handlers ------------
        self.width_line_edit.editingFinished.connect(self.width_textbox_handler)
        self.height_line_edit.editingFinished.connect(self.height_textbox_handler)

    def get_layout(self):
        return self.layout

    def textbox_handler(self, textbox, handler):
        txt = textbox.text()
        try:
            handler(float(txt))
        except ValueError:
            pass

    def width_textbox_handler(self):
        self.textbox_handler(self.width_line_edit, self.app_model.set_resize_width)

    def height_textbox_handler(self):
        self.textbox_handler(self.height_line_edit, self.app_model.set_resize_height)


class ControlPanel(qt.QWidget):
    """A widget where all of the configuration controls for this app are
    displayed. There are not many, so they all run along the top in a
    horizontal line, while the file list and image preview take up the
    majority of the space in the window below the controls in this widget."""

    def __init__(self, app_view, parent=None):
        super().__init__()
        self.app_view = app_view
        self.app_model = app_view.get_app_model()
        #----------- Construct widgets ------------
        self.resize_widget = ResizeConfig(self.app_model, editable=True, parent=self)
        self.encoding_menu = EncodingMenu("Encoding:", self.app_model, self)
        self.show_resize = qt.QCheckBox("Show resized")
        #----------- Layout all widgets ------------
        self.layout = qt.QHBoxLayout(self)
        self.layout.addWidget(self.resize_widget)
        self.layout.addWidget(self.encoding_menu)
        self.layout.addWidget(self.show_resize)
        #------------ Connect signal handlers------------
        self.show_resize.stateChanged.connect(self.change_show_resize_state)

    def change_show_resize_state(self, state):
        self.app_view.do_show_resize(state != qcore.Qt.CheckState.Unchecked)


class BatchResizeView(qt.QWidget):

    def __init__(self, app_model):
        super().__init__()
        self.app_model = app_model
        self.notify = qt.QErrorMessage(self)
        self.setWindowTitle("Image Resizing Kit")
        self.resize(1280, 720)
        #----------- Construct widgets ------------
        self.control_panel = ControlPanel(self)
        self.image_display = SimpleImagePreview(self)
        self.fileset_gui = FileSetGUI(
            self,
            fileset=app_model.get_fileset(),
            image_display=self.image_display,
          )
        #----------- Layout all widgets ------------
        self.layout = qt.QVBoxLayout(self)
        self.layout.addWidget(self.control_panel)
        self.layout.addWidget(self.fileset_gui)

    def get_app_model(self):
        return self.app_model

    def do_show_resize(self, yesno):
        print(f'BatchResizeView.do_show_resize({yesno})')
