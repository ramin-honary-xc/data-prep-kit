import DataPrepKit.PatternMatcher as patm
from DataPrepKit.ContextMenuItem import context_menu_item
from DataPrepKit.FileSet import FileSet
from DataPrepKit.SimpleImagePreview import SimpleImagePreview

import pathlib

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

def qt_modal_file_selection(widget, default_dir=None, message='Select files', qt_file_filter_string=''):
    """Simplifies calling qt.QFileDialog.getOpenFileUrls() function, a
    modal dialog box allowing end users to select files from the
    filesystem, and returns either a list of files, or None. This
    function also requires a smaller number of parameters:

      - 'default_dir': default directory, set to current directory if None
        is passed

      - 'message': displayed to the end user at the top of the dialog window

      - 'qt_file_filter_string': a string expression written using the
        Qt library's own EDSL for specifying what kind of files the
        end user is allowed to choose from the modal dialog.

    This function returns a possibly empty list of values that are
    either, a pathlib.PurePath() if the user selected a file from the
    local filesystem, or otherwise a qt.QUrl().
    """
    if default_dir is None:
        default_dir = pathlib.Path.cwd()
    else:
        pass
    reply = qt.QFileDialog.getOpenFileUrls(
        widget,
        message,
        qcore.QUrl(str(default_dir)),
        qt_file_filter_string,
        "",
        qt.QFileDialog.ReadOnly,
        ["file"],
      )
    if len(reply) > 0:
        urls = reply[0]
        urls = map(
            ( lambda url:
                pathlib.PurePath(url.toLocalFile()) \
                if url.isLocalFile() \
                else url
             ),
            urls,
          )
        return list(urls)
    else:
        print(f'qt_modal_file_selection("{message}") #(returned empty list)')
        return []

def qt_modal_image_file_selection(widget, default_dir=None, message="Open images files"):
    """Convenience function, calls 'qt_modal_file_selection' with the
    'qt_file_filter_string' argument set to the correct value to allow
    end users to select only image files."""
    return qt_modal_file_selection(
        widget,
        default_dir=default_dir,
        message=message,
        qt_file_filter_string='Images (*.png *.jpg *.jpeg)'
      )

class FileListItem(qt.QListWidgetItem):
    """A QListWidgetItem for an element in the files list in the Files tab."""

    def __init__(self, path):
        super().__init__(str(path))
        self.path = path

    def get_path(self):
        return self.path

class FileSetGUI(qt.QWidget):
    """This GUI is useful in a variety of tools because the purpose is to
    construct a fileset, or to select individual files, on which image
    processing algorithms can be run in a batch. As a result, it is
    defined as entire QWidget, and objects of this class are typically
    placed into a tab bar.

    There is only one action you must provide which is not built-in,
    and that is the action to be taken when the end users
    double-clicks on a file in the fileset listing, or presses enter
    while that list element is selected, which triggers the same
    action. This is a reference to any method or function that is
    called with a 'PureFilePath' value. Override the
    'activation_handler()' method to define this behavior.

    There are other modifications a subclass of this one might make:

    - Pass a reference to a FileSet as the 2nd argument. All file
      insertion and deletion operations will act directly on this
      fileset. You can also use the set_fileset() method.

    - The 'image_display' argument allows an ImageDisplay object as to
      be placed into the FileSetGUI view. Without this argument, no
      image display is created, but you can setup a default image
      display by calling the 'default_image_display_widget()' or
      'set_image_disaply_widget()' method after creating a new
      FileSetGUI object.

    - Construct QAction objects and install them into the context menu
      that pops-up when the end user right-clicks on either the image
      preview or the file list.

    - The 'file_selector': this function is expected you will pass a
      function that opens a Qt modal file selection dialog box that
      returns files a list of selected by the end user. Use functions
      such as 'qt_modal_file_selection' or
      'qt_modal_image_file_selection'.

    - The 'file_selector_message': the string to display at the top of
      the dialog box opened by the 'file_selector'. This value is
      passed to the function that is set in the 'file_selector' slot.

    """

    def __init__(
        self,
        main_view,
        fileset=None,
        image_display=None,
        action_label='Use this file',
        file_selector=qt_modal_file_selection,
        file_selector_message='Select files',
      ):
        super().__init__(main_view)
        self.setObjectName("FilesTab")
        self.main_view = main_view
        self.file_selector = file_selector
        self.file_selector_message = file_selector_message
        if fileset is None:
            self.fileset = FileSet()
        else:
            self.fileset = fileset
        #---------- Setup visible widgets ----------
        self.layout = qt.QHBoxLayout(self)
        self.splitter = qt.QSplitter(qcore.Qt.Orientation.Horizontal, self)
        self.setAcceptDrops(True)
        self.splitter.setObjectName("FilesTab splitter")
        self.list_widget = qt.QListWidget(self)
        self.list_widget.setObjectName("FilesTab list_widget")
        self.list_widget.setContextMenuPolicy(qcore.Qt.ContextMenuPolicy.ActionsContextMenu)
        self.splitter.insertWidget(0, self.list_widget)
        self.image_display = None
        self.set_image_display_widget(image_display)
        self.layout.addWidget(self.splitter)
        self.display_pixmap_path = None
        #---------- Populate list view ----------
        self.reset_paths_list()
        #---------- Setup context menus ----------
        ## Action: open image files
        self.open_image_files = context_menu_item(
            "Open image files",
            self.open_files_handler,
            qgui.QKeySequence.Open,
          )
        self.file_list_add_context_menu_item(self.open_image_files)
        self.image_display_add_context_menu_item(self.open_image_files)
        ## Action: remove from list
        self.remove_from_list = context_menu_item(
            "Remove from list",
            self.remove_from_list_handler,
            qgui.QKeySequence.Delete,
          )
        self.file_list_add_context_menu_item(self.remove_from_list)
        ## Action: Search within this image
        self.do_find_pattern = context_menu_item(
            action_label,
            self.activate_selected_item,
            qgui.QKeySequence.InsertParagraphSeparator,
          )
        self.file_list_add_context_menu_item(self.do_find_pattern)
        self.image_display_add_context_menu_item(self.do_find_pattern)
        #---------- Connect signal handlers ----------
        self.list_widget.currentItemChanged.connect(self.__item_change_handler)
        self.list_widget.itemActivated.connect(self.__activation_handler)

    def get_fileset(self):
        return self.fileset

    def set_fileset(self, fileset):
        self.fileset = fileset

    def set_file_selector(self, file_selector, message='Select files'):
        """To this function, it is expected you will pass a function that
        opens a Qt modal file selection dialog box that returns files
        a list of selected by the end user. Use functions such as
        'qt_modal_file_selection' or 'qt_modal_image_file_selection'.
        """
        self.file_selector_message = message
        self.file_selector = file_selector

    def get_list_widget(self):
        return self.list_widget

    def get_image_display(self):
        return self.image_display

    def default_image_display_widget(self):
        self.set_image_display_widget(SimpleImagePreview(self))

    def set_image_display_widget(self, image_display):
        if self.image_display is not None:
            print(f'FileListItem.set_image_display_widget() -> deleteLater({self.image_display})')
            self.image_display.clear()
            self.image_display.deleteLater()
        else:
            pass
        self.image_display = image_display
        if self.image_display is not None:
            self.image_display.setObjectName("FilesTab ImagePreview")
            self.splitter.insertWidget(1, self.image_display)
        else:
            pass

    def file_list_add_context_menu_item(self, item):
        if isinstance(item, qt.QAction):
            self.list_widget.addAction(item)
        else:
            raise ValueError(f'not an instance of QAction', item)

    def image_display_add_context_menu_item(self, item):
        if isinstance(item, qt.QAction):
            if self.image_display is not None:
                self.image_display.addAction(item)
            else:
                pass
        else:
            raise ValueError(f'not an instance of QAction', item)

    def __activation_handler(self, item):
        self.activation_handler(item.get_path())

    def activation_handler(self, item):
        pass

    def __item_change_handler(self, item, _old):
        if item is not None:
            self.item_change_handler(item.get_path())
        else:
            pass

    def item_change_handler(self, item):
        if self.image_display is not None:
            self.image_display.set_filepath(item)
        else:
            pass

    def activate_selected_item(self):
        """This method performs the same action as double-clicking on a file
        item in the file list view, or pressing enter while focused on
        an item of the file list view.
        """
        path = self.current_item_path()
        if (path is None) and (self.image_display is not None):
            path = self.image_display.get_filepath()
        else:
            pass
        if path is None:
            # TODO: display an error message dialog box instead of a log message
            print(f'FileSetGUI.activate_selected_item() #(no file item selected)')
        else:
            self.activation_handler(path)

    def current_item_path(self):
        item = self.list_widget.currentItem()
        if item is not None:
            return item.get_path()
        else:
            return None

    def remove_from_list_handler(self):
        item = self.list_widget.currentItem()
        if item is not None:
            path = item.get_path()
            self.fileset.delete(path)
            self.list_widget.takeItem(self.list_widget.currentRow())
            if self.image_display is not None:
                self.image_display.clear()
            else:
                pass
        else:
            pass

    def reset_paths_list(self):
        """Populate the list view with an item for each file path."""
        self.list_widget.clear()
        for item in self.fileset:
            self.list_widget.addItem(FileListItem(item))

    def open_files_handler(self, default_dir):
        """Ask the operating system to display a file selection modal dialog
        box that asks you to select files to open. Pass the a
        pathlib.Path() default directory as an argument to this
        function.
        """
        if default_dir is None:
            default_dir = pathlib.Path.cwd()
        else:
            pass
        urls = self.file_selector(self, self.file_selector_message)
        print(f"selected urls = {urls}")
        urls = urls[0]
        if len(urls) > 0:
            self.main_view.add_target_image_paths(gather_QUrl_local_files(urls))
            self.files_tab.reset_paths_list(self.target_image_paths)
        else:
            pass

    def dragEnterEvent(self, event):
        # TODO: remove these and inherit from DragDropHandler
        mime_data = event.mimeData()
        if mime_data.hasUrls() or mime_data.hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        # TODO: remove these and inherit from DragDropHandler
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            event.accept()
            urls = mime_data.urls()
            print(f'FilesSetGUI.dropEvent() #(urls: {urls})')
            self.fileset.merge_recursive(patm.gather_QUrl_local_files(urls))
            self.reset_paths_list()
        elif mime_data.hasText():
            event.accept()
            text = mime_data.text()
            print(f'FilesSetGUI.dropEvent() #(text: {text})')
            self.fileset.merge_recursive(util.split_linebreaks(text))
            self.reset_paths_list()
        else:
            event.ignore()

