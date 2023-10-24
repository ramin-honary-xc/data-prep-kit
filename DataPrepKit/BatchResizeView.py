from DataPrepKit.FileSetGUI import FileSetGUI, qt_modal_image_file_selection
from DataPrepKit.EncodingMenu import EncodingMenu
from DataPrepKit.SimpleImagePreview import SimpleImagePreview
from DataPrepKit.GUIHelpers import numpy_array_to_QPixmap, QPixmap_to_numpy_array
from DataPrepKit.ContextMenuItem import context_menu_item

import PyQt5.QtWidgets as qt
import PyQt5.QtGui as qgui
import PyQt5.QtCore as qcore

import os
from pathlib import PurePath

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

    def set_show_resize_state_widget(self, state):
        self.show_resize.setChecked(
            qcore.Qt.CheckState.Checked if state else qcore.Qt.CheckState.Unchecked
          )


class ImageFileView(FileSetGUI):

    def __init__(
      self,
        main_view,
        fileset=None,
        image_display=None,
      ):
        super(ImageFileView, self).__init__(
            main_view,
            fileset=fileset,
            image_display=image_display,
          )
        self.showing_resized = False
        self.resized_image_cached = None
        self.image_cached = None
        self.cached_path = None
        # -------------------- Menu items --------------------
        self.save_current_menu = context_menu_item(
            "Save current image",
            self.save_current_image_handler,
            qgui.QKeySequence.Save
          )
        self.save_all_menu_item = context_menu_item(
            "Save all resized images",
            self.save_all_images_handler,
            qgui.QKeySequence.SaveAs,
          )
        self.file_list_add_context_menu_item(self.save_current_menu)
        self.image_display_add_context_menu_item(self.save_current_menu)
        self.file_list_add_context_menu_item(self.save_all_menu_item)
        self.image_display_add_context_menu_item(self.save_all_menu_item)

    def save_current_image_handler(self):
        if self.cached_path is None:
            print(f'ImageFileiew.save_current_image_handler() #(failed: no selected image)')
        else:
            out_path = self.modal_prompt_save_file(
                self.app_model.get_diff_image().get_path(),
              )
            cv.imwrite(os.fspath(out_path), QPixmap_to_numpy_array(self.resized_image_cached))

    def save_all_images_handler(self):
        app_model = self.main_view.get_app_model()
        output_dir = \
            qt.QFileDialog.getExistingDirectory(
                self, "Write images to directory",
                str(app_model.get_output_dir()),
                qt.QFileDialog.ShowDirsOnly,
              )
        app_model.set_output_dir(PurePath(output_dir))
        app_model.batch_resize_images()

    def item_change_handler(self, path):
        #super().item_change_handler(path)
        #return
        print(f'ImageFileView.item_change_handler({str(path)!r})')
        if str(self.cached_path) == str(path):
            pass
        else:
            self.cached_path = path
            super().item_change_handler(path)
            image_display = self.get_image_display()
            path_buffer = image_display.get_image_buffer()
            if path_buffer:
                (_, self.image_cached) = path_buffer
            else:
                print(f'ImageFileView.item_change_handler() #(image_display.get_image_buffer() returned value of type {type(path_buffer)})')
                self.image_cached = None
            self.resized_image_cached = None
            if self.showing_resized:
                self._show_resized_view()
            else:
                print(f'ImageFileView.item_change_handler() #(not showing resized view)')
                pass

    def _show_resized_view(self):
        print(f'ImageFileView._show_resized_view() #(evaluate resize on cached image)')
        if not self.cached_path:
            print(f'ImageFileView._show_resized_view() #(self.cached_path = None)')
            return
        else:
            pass
        app_model = self.main_view.get_app_model()
        if not self.resized_image_cached:
            if self.image_cached:
                img = self.image_cached
                if isinstance(img, qgui.QPixmap):
                    img = app_model.resize_image_buffer(QPixmap_to_numpy_array(img))
                    self.image_cached = numpy_array_to_QPixmap(img)
                else:
                    print(f'ImageFileView._show_resized_view() #(will not compute resized image, self.image_cache is of type {type(img)})')
                    pass
                self.resized_image_cached = numpy_array_to_QPixmap(app_model.resize_image_buffer(img))
            else:
                pass
            # # Uncomment this code as a last resort in the event that
            # # QPixmap_to_numpy_array is not working. This code
            # # creates the cached resized image by reloading the
            # # original image from disk every time, rather than using
            # # the image buffer that is already in memory.
            #
            # imgbufs = app_model.resize_image_file(self.cached_path)
            # if imgbufs:
            #     (_original, resized) = imgbufs
            #     print(f'ImageFileView._show_resize_view() #(imgbufs -> (original={type(original)}, resized={type(resized)}))')
            #     #self.image_cached = numpy_array_to_QPixmap(original)
            #     self.resized_image_cached = numpy_array_to_QPixmap(resized)
            # else:
            #     print('ImageFileView._show_resized_view() #(app_model.resize_image_file() returned None)')
        else:
            pass
        print(f'ImageFileView._show_resized_view() #(resized_image_cache is of type {type(self.resized_image_cached)})')
        image_display = self.get_image_display()
        if self.resized_image_cached is not None:
            image_display.set_image_buffer(self.cached_path, self.resized_image_cached)
            self.showing_resized = True
        else:
            print(f'ImageFileView._show_resized_view() #(cannot set resized view, self.resized_image_cache is {self.resized_image_cached!r})')

    def _show_original_size_view(self):
        print(f'ImageFileView._show_original_size_view()')
        image_display = self.get_image_display()
        image_display.set_image_buffer(self.cached_path, self.image_cached)
        self.showing_resized = False

    def get_showing_resized(self):
        return self.showing_resized

    def set_showing_resized(self, yesno):
        if yesno == self.showing_resized:
            print(f'ImageFileView.set_showing_resized({yesno}) #(is already {self.showing_resized})')
            pass
        else:
            self.showing_resized = yesno
            self.update_show_resized()

    def update_show_resized(self):
        if self.showing_resized:
            self._show_resized_view()
        else:
            self._show_original_size_view()


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
        self.fileset_gui = ImageFileView(
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
        self.fileset_gui.set_showing_resized(yesno)
