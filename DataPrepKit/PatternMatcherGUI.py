import DataPrepKit.PatternMatcher as patm

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

####################################################################################################
# The Qt GUI

class FileListItem(qt.QListWidgetItem):
    """A QListWidgetItem for an element in the files list in the Files tab."""

    def __init__(self, path):
        super().__init__(str(path))
        self.path = path

    def get_path(self):
        return self.path

#--------------------------------------------------------------------------------------------------

class ImagePreview(qt.QGraphicsView):

    def __init__(self, app_model, parent):
        super().__init__(parent)
        self.app_model = app_model
        self.preview_scene = qt.QGraphicsScene(self)
        self.pixmap_path = None
        self.pixmap_item = None
        self.pixmap_buffer = None
        self.setViewportUpdateMode(4) # 4: QGraphicsView::BoundingRectViewportUpdate
        self.setResizeAnchor(1) # 1: QGraphicsView::AnchorViewCenter
        self.setScene(self.preview_scene)
        self.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu

    def resizeEvent(self, newSize):
        super().resizeEvent(newSize)
        if self.pixmap_item is not None:
            self.fitInView(self.pixmap_item, 1) # 1: qcore.AspectRatioMode::KeepAspectRatio

    def update_display(self):
        target = self.app_model.get_target()
        path = target.get_path()
        if (self.pixmap_buffer is not None) and (self.pixmap_path == path):
            # Here the pixmap_path has not been changed, so we need to
            # prevent it from being freed by self.preview_scene.clear(),
            # as we do not want to reload it from the filesystem.
            self.preview_scene.removeItem(self.pixmap_item)
        else:
            self.pixmap_buffer = qgui.QPixmap()
            self.pixmap_buffer.load(str(path))
        self.pixmap_item = None
        self.pixmap_path = path
        self.preview_scene.clear()
        if self.pixmap_buffer is not None:
            self.pixmap_item = qt.QGraphicsPixmapItem(self.pixmap_buffer)
            self.preview_scene.addItem(self.pixmap_item)
            self.resetTransform()
            self.fitInView(self.pixmap_item, 1)
        else:
            print(f'ImagePreview.update_display() #(Failed to load "{path!s}")')
            pass


class InspectImagePreview(ImagePreview):

    def __init__(self, app_model, parent):
        super().__init__(app_model, parent)
        self.pen = qgui.QPen(qgui.QColor(255, 0, 0, 255))
        self.pen.setCosmetic(True)
        self.pen.setWidth(3)

    def place_rectangles(self, rectangle_list):
        self.preview_scene.clear()
        if self.pixmap_item is not None:
            self.pixmap_item = qt.QGraphicsPixmapItem(self.pixmap_buffer)
            self.preview_scene.addItem(self.pixmap_item)
        else:
            pass
        for rectangle in rectangle_list:
            bounds = rectangle.get_point_and_size()
            self.preview_scene.addRect(*bounds, self.pen)

#---------------------------------------------------------------------------------------------------

class MessageBox(qt.QWidget):

    def __init__(self, message):
        super().__init__()
        self.layout = qt.QHBoxLayout(self)
        self.message = qt.QLabel(message)
        self.layout.addWidget(self.message)

class FilesTab(qt.QWidget):
    """Display a list of images, and provide an image preview window to
    view each iamge.
    """

    def __init__(self, app_model, main_view):
        super().__init__(main_view)
        self.setObjectName("FilesTab")
        self.app_model = app_model
        self.main_view = main_view
        #---------- Setup visible widgets ----------
        self.layout        = qt.QHBoxLayout(self)
        self.splitter      = qt.QSplitter(1, self)
        self.setAcceptDrops(True)
        self.splitter.setObjectName("FilesTab splitter")
        self.list_widget   = qt.QListWidget(self)
        self.list_widget.setObjectName("FilesTab list_widget")
        self.list_widget.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu
        self.image_preview  = ImagePreview(self.app_model, self)
        self.image_preview.setObjectName("FilesTab ImagePreview")
        self.splitter.addWidget(self.list_widget)
        self.splitter.addWidget(self.image_preview)
        self.layout.addWidget(self.splitter)
        self.display_pixmap_path = None
        #---------- Populate list view ----------
        self.reset_paths_list()
        #---------- Setup context menus ----------
        ## Action: Use as pattern
        self.use_as_pattern = qt.QAction("Use as pattern", self)
        self.use_as_pattern.setShortcut(qgui.QKeySequence.Find)
        self.use_as_pattern.triggered.connect(self.use_current_item_as_pattern)
        self.list_widget.addAction(self.use_as_pattern)
        self.image_preview.addAction(self.use_as_pattern)
        ## Action: Search within this image
        self.do_find_pattern = qt.QAction("Search within this image", self)
        self.do_find_pattern.setShortcut(qgui.QKeySequence.InsertParagraphSeparator)
        self.do_find_pattern.triggered.connect(self.activate_selected_item)
        self.list_widget.addAction(self.do_find_pattern)
        self.image_preview.addAction(self.do_find_pattern)
        ## Action: open image files
        self.open_image_files = qt.QAction("Open image files", self)
        self.open_image_files.setShortcut(qgui.QKeySequence.Open)
        self.open_image_files.triggered.connect(self.open_image_files_handler)
        self.list_widget.addAction(self.open_image_files)
        self.image_preview.addAction(self.open_image_files)
        #---------- Connect signal handlers ----------
        self.list_widget.currentItemChanged.connect(self.item_change_handler)
        self.list_widget.itemActivated.connect(self.activate_handler)

    def activate_handler(self, item):
        path = item.get_path()
        self.app_model.set_target_image_path(path)
        self.app_model.match_on_file()
        distance_map = self.app_model.get_distance_map()
        if distance_map:
            self.main_view.show_distance_map()
            self.main_view.show_inspect_tab()
        else:
            self.main_view.show_pattern_tab()
            self.main_view.error_message( \
                "A pattern image must be set for matching on the selected image." \
              )

    def activate_selected_item(self):
        item = self.list_widget.currentItem()
        self.activate_handler(item)

    def item_change_handler(self, item, _old):
        if item is not None:
            self.app_model.set_target_image_path(item.get_path())
            self.image_preview.update_display()
        else:
            print("FilesTab.item_change_handler(item=None)")

    def use_current_item_as_pattern(self):
        item = self.list_widget.currentItem()
        path = item.get_path()
        print(f'FilesTab.use_current_item_as_pattern() #("{path}")')
        self.app_model.set_pattern_image_path(path)
        self.main_view.update_pattern_pixmap()

    def reset_paths_list(self):
        """Populate the list view with an item for each file path."""
        paths_list = self.app_model.get_target_fileset()
        self.list_widget.clear()
        if paths_list:
            for item in paths_list:
                self.list_widget.addItem(FileListItem(item))
        else:
            pass

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
            self.app_model.add_target_fileset(patm.gather_QUrl_local_files(mime_data.urls()))
            self.reset_paths_list()
        elif mime_data.hasText():
            event.accept()
            self.app_model.add_target_fileset(util.split_linebreaks(mime_data.text()))
            self.reset_paths_list()
        else:
            event.ignore()

#---------------------------------------------------------------------------------------------------

class PatternPreview(qt.QGraphicsView):
    """A QGraphicsView for displaying the pattern image. It does not
    inherit from InspectImagePreview because it has different behavior
    for displaying the image, and for drag and drop. This class may be
    removed and replaced with a more featureful versino of
    InspectImagePreview in the future.
    """

    def __init__(self, app_model, main_view):
        super().__init__()
        self.app_model = app_model
        self.main_view = main_view
        self.display_pixmap = qgui.QPixmap()
        self.preview_scene  = qt.QGraphicsScene(self)
        self.pixmap_item = None
        self.setScene(self.preview_scene)
        self.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        self.main_view.dragEnterEvent(event)

    def dropEvent(self, event):
        self.main_view.dropEvent(event)

    def update_pattern_pixmap(self):
        self.preview_scene.clear()
        pattern = self.app_model.get_pattern()
        path = pattern.get_path()
        self.display_pixmap = qgui.QPixmap(str(path))
        self.pixmap_item = self.preview_scene.addPixmap(self.display_pixmap)
        self.resetTransform()

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
        ## Action: open image files
        self.open_pattern_file = qt.QAction("Open pattern file", self)
        self.open_pattern_file.setShortcut(qgui.QKeySequence.Open)
        self.open_pattern_file.triggered.connect(self.open_pattern_file_handler)
        self.preview_view.addAction(self.open_pattern_file)

    def update_pattern_pixmap(self):
        self.preview_view.update_pattern_pixmap()

    def open_pattern_file_handler(self):
        target_dir = self.main_view.get_config().pattern
        url = \
            qt.QFileDialog.getOpenFileUrl( \
                self, "Open images in which to search for patterns", \
                qcore.QUrl(str(target_dir)), \
                "Images (*.png *.jpg *.jpeg)", "", \
                qt.QFileDialog.ReadOnly, \
                ["file"] \
              )
        url = url[0]
        if (url is not None) and url.isLocalFile():
            self.main_view.show_pattern_image_path(PurePath(url.toLocalFile()))
        else:
            print(f"URL {url} is not a local file")

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if len(urls) == 1:
                event.accept()
            else:
                event.ignore()
        elif mime_data.hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if len(urls) == 1:
                event.accept()
                url = urls[0]
                self.app_model.set_pattern_image_path(PurePath(url.toLocalFile()))
                self.main_view.update_pattern_pixmap()
            else:
                event.ignore()
        elif mime_data.hasText():
            event.accept()
            self.app_model.set_pattern_image_path(PurePath(mime_data.text()))
            self.main_view.update_pattern_pixmap()
        else:
            event.ignore()

#---------------------------------------------------------------------------------------------------

class PercentSlider(qt.QWidget):

    def __init__(self, label, init_value, callback):
        super().__init__()
        self.percent = init_value
        self.callback = callback
        self.label = qt.QLabel(label)
        self.slider = qt.QSlider(1, self)
        self.slider.setMinimum(500)
        self.slider.setMaximum(1000)
        self.slider.setPageStep(50)
        self.slider.setSingleStep(10)
        self.slider.setValue(round(self.percent * 1000.0))
        self.slider.setObjectName("InspectTab slider")
        self.slider.valueChanged.connect(self.value_changed_handler)
        self.setSizePolicy(self.slider.sizePolicy())
        self.textbox = qt.QLineEdit(str(round(self.percent * 1000.0) / 10.0), self)
        self.textbox.setMaxLength(5)
        self.textbox.setObjectName("InspectTab textbox")
        font_metrics = qt.QLabel("100.0 %").fontMetrics()
        self.textbox.setFixedWidth(font_metrics.width("100.0 %"))
        self.textbox.editingFinished.connect(self.textbox_handler)
        #---------- The top bar is always visible ----------
        self.layout = qt.QHBoxLayout(self)
        self.layout.setObjectName("InspectTab layout")
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.textbox)
        self.layout.addWidget(self.slider)

    def get_percent(self):
        return self.percent

    def value_changed_handler(self, new_value):
        self.slider.setValue(new_value)
        self.textbox.clear()
        self.textbox.setText(f"{new_value/10.0}")
        self.percent = new_value / 1000.0
        self.callback(new_value)

    def reset_value(self):
        self.textbox.setText(f"{self.percent * 100.0}")
        self.slider.setValue(round(self.percent * 1000.0))

    def textbox_handler(self):
        # editingFinished signal handler
        txt = self.textbox.text()
        try:
            new_value = float(txt)
            if new_value >= 50.0 and new_value <= 100.0:
                self.percent = new_value / 100.0
            else:
                pass
        except ValueError:
            pass
        self.reset_value()

#---------------------------------------------------------------------------------------------------

class InspectTab(qt.QWidget):

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
        self.slider = PercentSlider( \
            "Threshold %", \
            config.threshold, \
            self.slider_handler \
          )
        self.layout.addWidget(self.slider)
        self.message_box = MessageBox("Please select SEARCH target image and PATTERN image.")
        self.layout.addWidget(self.message_box)
        self.image_preview = InspectImagePreview(self.app_model, self)
        self.image_preview.hide()
        self.layout.addWidget(self.image_preview)
        #---------- Setup context menus ----------
        self.do_save_selected = qt.QAction("Save all selected regions", self)
        self.do_save_selected.setShortcut(qgui.QKeySequence.Save)
        self.do_save_selected.setEnabled(False)
        self.do_save_selected.triggered.connect(self.save_selected)
        self.image_preview.addAction(self.do_save_selected)

    def slider_handler(self, new_value):
        self.place_rectangles()

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
        self.image_preview.update_display()
        self.place_rectangles()
        self.show_image_preview()
        self.do_save_selected.setEnabled(True)

    def place_rectangles(self):
        if self.distance_map is not None:
            threshold = self.slider.get_percent()
            self.image_preview.place_rectangles( \
                self.distance_map.find_matching_regions(threshold) \
              )
        else:
            print("WARNING: InspectTab.place_rectangles() called before distance_map was set")

    def modal_prompt_get_directory(self, init_dir):
        output_dir = \
            qt.QFileDialog.getExistingDirectory( \
                self, "Write images to directory", \
                init_dir, \
                qt.QFileDialog.ShowDirsOnly \
          )
        return PurePath(output_dir)

    def save_selected(self):
        if self.distance_map is not None:
            output_dir = self.main_view.get_config().output_dir
            output_dir = self.modal_prompt_get_directory(str(output_dir))
            threshold = self.slider.get_percent()
            target_image = self.main_view.target.get_image()
            self.distance_map.write_all_cropped_images(target_image, threshold, output_dir)
        else:
            print('WARNING: InspectTab.save_selected() called before distance_map was set')

#---------------------------------------------------------------------------------------------------

class PatternMatcherView(qt.QTabWidget):
    """The Qt Widget containing the GUI for the pattern matching program.
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

