import DataPrepKit.PatternMatcher as patm
from DataPrepKit.ContextMenuItem import context_menu_item
from DataPrepKit.FileSet import FileSet
from DataPrepKit.SimpleImagePreview import SimpleImagePreview

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

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

    - Make modifications to the file display. You can pass your own
      ImageDisplay object as the 3rd argument to the
      constructor. Without this argument, a default ImageDisplay is
      constructed.

    - Construct QAction objects and install them into the context menu
      that pops-up when the end user right-clicks on either the image
      preview or the file list.

    """

    def __init__(self, main_view, fileset=None, image_preview=None, action_label='Use this file'):
        super().__init__(main_view)
        self.setObjectName("FilesTab")
        self.main_view = main_view
        if fileset is None:
            self.fileset = FileSet()
        else:
            self.fileset = fileset
        #---------- Setup visible widgets ----------
        self.layout = qt.QHBoxLayout(self)
        self.splitter = qt.QSplitter(1, self)
        self.setAcceptDrops(True)
        self.splitter.setObjectName("FilesTab splitter")
        self.list_widget = qt.QListWidget(self)
        self.list_widget.setObjectName("FilesTab list_widget")
        self.list_widget.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu
        if image_preview is None:
            self.image_preview = SimpleImagePreview(self)
        else:
            self.image_preview = image_preview
        self.image_preview.setObjectName("FilesTab ImagePreview")
        self.splitter.addWidget(self.list_widget)
        self.splitter.addWidget(self.image_preview)
        self.layout.addWidget(self.splitter)
        self.display_pixmap_path = None
        #---------- Populate list view ----------
        self.reset_paths_list()
        #---------- Setup context menus ----------
        ## Action: open image files
        self.open_image_files = context_menu_item(
            "Open image files",
            self.open_image_files_handler,
            qgui.QKeySequence.Open,
          )
        self.file_list_add_context_menu_item(self.open_image_files)
        self.image_preview_add_context_menu_item(self.open_image_files)
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
        self.image_preview_add_context_menu_item(self.do_find_pattern)
        #---------- Connect signal handlers ----------
        self.list_widget.currentItemChanged.connect(self.__item_change_handler)
        self.list_widget.itemActivated.connect(self.__activation_handler)

    def get_fileset(self):
        return self.fileset

    def set_fileset(self, fileset):
        self.fileset = fileset

    def get_list_widget(self):
        return self.list_widget

    def get_image_preview(self):
        return self.image_preview

    def set_image_preview(self, image_preview):
        self.image_preview = image_preview

    def file_list_add_context_menu_item(self, item):
        if isinstance(item, qt.QAction):
            self.list_widget.addAction(item)
        else:
            raise ValueError(f'not an instance of QAction', item)

    def image_preview_add_context_menu_item(self, item):
        if isinstance(item, qt.QAction):
            self.image_preview.addAction(item)
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
        self.image_preview.set_filepath(item)

    def activate_selected_item(self):
        """This method performs the same action as double-clicking on a file
        item in the file list view, or pressing enter while focused on
        an item of the file list view.
        """
        path = self.current_item_path()
        if path is None:
            path = self.image_preview.get_filepath()
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
        path = item.get_path()
        self.fileset.delete(path)
        self.list_widget.takeItem(item)
        self.image_preview.clear_display()

    def reset_paths_list(self):
        """Populate the list view with an item for each file path."""
        self.list_widget.clear()
        for item in self.fileset:
            self.list_widget.addItem(FileListItem(item))

    def open_image_files_handler(self):
        target_dir = self.main_view.get_config().output_dir
        urls = \
            qt.QFileDialog.getOpenFileUrls( \
                self, "Open images in which to search for patterns", \
                qcore.QUrl(str(target_dir)), \
                "Images (*.png *.jpg *.jpeg)", "", \
                qt.QFileDialog.ReadOnly, \
                ["file"] \
              )
        print(f"selected urls = {urls}")
        urls = urls[0]
        if len(urls) > 0:
            self.main_view.add_target_image_paths(gather_QUrl_local_files(urls))
            self.files_tab.reset_paths_list(self.target_image_paths)
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
        print(f'FilesTab.dropEvent("{mime_data}")')
        if mime_data.hasUrls():
            event.accept()
            self.fileset.merge_recursive(patm.gather_QUrl_local_files(mime_data.urls()))
            self.reset_paths_list()
        elif mime_data.hasText():
            event.accept()
            self.fileset.merge_recursive(util.split_linebreaks(mime_data.text()))
            self.reset_paths_list()
        else:
            event.ignore()

