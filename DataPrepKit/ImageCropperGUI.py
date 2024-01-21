import DataPrepKit.utilities     as util
import DataPrepKit.ORBMatcher    as orbm
from DataPrepKit.CropRectTool    import CropRectTool
from DataPrepKit.ImageFileLayer  import ImageFileLayer
from DataPrepKit.PointCloudLayer import PointCloudLayer
from DataPrepKit.ImageDisplay    import ImageDisplay

from copy import deepcopy
import os
from pathlib import (PurePath, Path)

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

####################################################################################################
# The GUI for the image croping tool

class ImagePreview(qt.QGraphicsView):

    """This is a QGraphicsView that displays an image. Images are loaded
    by filepath."""

    def __init__(self, parent, app_model):
        super(ImagePreview, self).__init__(parent)
        self.app_model = app_model
        self.preview_scene = qt.QGraphicsScene(self)
        self.display_pixmap = None
        self.display_pixmap_item = None
        self.crop_rect_item = None
        self.current_display = None
        self.setViewportUpdateMode(4) # 4: QGraphicsView::BoundingRectViewportUpdate
        self.setResizeAnchor(1) # 1: QGraphicsView::AnchorViewCenter
        self.setScene(self.preview_scene)
        self.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu
        self.crop_rect_pen = qgui.QPen(qgui.QColor(255, 0, 0))
        self.crop_rect_pen.setCosmetic(True)
        self.crop_rect_pen.setWidth(3)

    def resizeEvent(self, newSize):
        super(ImagePreview, self).resizeEvent(newSize)
        if self.display_pixmap is not None:
            self.fitInView(self.display_pixmap_item, 1) # 1: qcore.AspectRatioMode::KeepAspectRatio

    def update_display_item(self):
        """This function redraws the image displayed in the image preview."""
        #traceback.print_stack()
        image_with_orb = self.app_model.get_selected_image()
        if image_with_orb is not None:
            path = str(image_with_orb.get_filepath())
            if image_with_orb is self.current_display:
                self.preview_scene.removeItem(self.display_pixmap_item)
            else:
                self.display_pixmap = qgui.QPixmap(path)
            #---------------------------------------
            self.preview_scene.clear()
            self.crop_rect_item = None
            self.display_pixmap_item = None
            self.resetTransform()
            if self.display_pixmap:
                self.display_pixmap_item = qt.QGraphicsPixmapItem(self.display_pixmap)
                self.preview_scene.addItem(self.display_pixmap_item)
            else:
                #print(f'ImagePreview.update_display_item() #(failed to load file from path "{path}")')
                pass
            self.current_display = image_with_orb
            rect = image_with_orb.get_crop_rect()
            if rect is not None:
                qrectf = qcore.QRectF(*rect)
                self.crop_rect_item = \
                    self.preview_scene.addRect(qrectf, self.crop_rect_pen)
                self.setSceneRect(qrectf)
            else:
                #print(f'ImagePreview.update_display_item() #(scene crop_rect is None, reset to whole image)')
                size = self.display_pixmap.size()
                self.setSceneRect(0, 0, size.width(), size.height())
        else:
            #print(f'ImagePreview.update_display_item() #(self.app_model.get_selected_item() -> None)')
            pass


class ReferenceImageView(ImageDisplay):
    """This is the scene controller used to manage mouse events on the
    image view and allows the user to draw a crop rectangle over the
    image. This class is the view and controller for the ImageWithORB
    model.
    """

    def __init__(self, app_model):
        super(ReferenceImageView, self).__init__()
        scene = super(ReferenceImageView, self).get_scene()
        self.app_model = app_model
        self.image_file_layer = ImageFileLayer(scene)
        self.point_cloud_layer = PointCloudLayer(scene)
        self.crop_rect_tool = CropRectTool(scene, self.app_model.set_crop_rect)
        ImageDisplay.set_mouse_mode(self, self.crop_rect_tool)
        self.redraw()

    def set_scene(self, scene):
        super(ReferenceImageView, self).set_scene(scene)
        self.image_file_layer.set_scene(scene)
        self.crop_rect_tool.set_scene(scene)
        self.point_cloud_layer.set_scene(scene)

    def clear(self):
        self.crop_rect_tool.clear()
        self.image_file_layer.clear()
        self.point_cloud_layer.clear()
        #super(ReferenceImageView, self).clear()

    def redraw(self):
        self.draw_pixbuf()
        self.draw_keypoints()
        self.draw_reference_crop_rect()

    def draw_pixbuf(self):
        orb_image = self.app_model.get_reference_image()
        if orb_image is not None:
            #print(f'ReferenceImageView.draw_pixbuf("{str(orb_image.get_filepath())}")')
            self.image_file_layer.set_filepath(orb_image.get_filepath())
        else:
            #print(f'ReferenceImageView.draw_pixbuf() #(no reference image)')

    def draw_keypoints(self):
        orb_image = self.app_model.get_reference_image()
        #print(f'ReferenceImageView.draw_keypoints("str(orb_image.get_filepath())")')
        if orb_image is not None:
            # First remove the existing keypoints.
            self.point_cloud_layer.clear()
            # Then get the new list of orb_image points.
            keypoints = orb_image.get_keypoints()
            if keypoints is not None:
                #print(f'ReferenceImageView.draw_keypoints("str(orb_image.get_filepath())") #(len(keypoints) = {len(keypoints)})')
                for key in keypoints:
                    (x, y) = key.pt
                    self.point_cloud_layer.add_point(x, y)
            else:
                #print(f'ReferenceImageView.draw_keypoints() #(orb_config has not been updated)')
        else:
            #print(f'ReferenceImageView.draw_keypoints() #(no reference image)')

    def draw_reference_crop_rect(self):
        """This function draws the crop_rect in the view based on the crop_rect value
        set in the reference image of the app_model."""
        #print(f'ReferenceImageView.draw_crop_rect({str(rec)})')
        rect = self.app_model.get_crop_rect()
        if rect is not None:
            self.crop_rect_tool.set_crop_rect(rect)
            self.crop_rect_tool.redraw()
        else:
            pass

#---------------------------------------------------------------------------------------------------

class ReferenceImageTab(qt.QWidget):
    """Display the image used as the reference image, and provide an image
    preview window to view each iamge. It responds to mouse clicks to
    allow end users to define the cropping rectangle. The cropping
    rectangle will be centered around the key points found by the ORB
    algorithm. All other images selected for cropping will also run
    the ORB algorithm, and a similar croppiping rectangle will be
    cenetered around those key points.
    """

    def __init__(self, app_model, parent):
        super(ReferenceImageTab, self).__init__(parent)
        self.setObjectName('FilesTab')
        #---------- Setup visible widgets ----------
        self.app_model      = app_model
        self.app_view       = parent
        self.image_preview  = ReferenceImageView(self.app_model)
        self.image_preview.setObjectName('ReferenceImageTab ImagePreview')
        self.layout         = qt.QHBoxLayout(self)
        self.layout.addWidget(self.image_preview)

    def redraw(self):
        self.image_preview.redraw()


################################################################################

def gather_QUrl_local_files(qurl_list):
    """This function converts a list of URL values of type QUrl into a
    list of PurePaths. It is useful for constructing 'FileListItem's
    from the result of a file dialog selection.
    """
    urls = []
    for url in qurl_list:
        if url.isLocalFile():
            urls.append(PurePath(url.toLocalFile()))
    return urls

class FileListItem(qt.QListWidgetItem):
    """A QListWidgetItem for an element in the files list in the Files tab."""

    def __init__(self, image_with_orb):
        super(FileListItem, self).__init__(str(image_with_orb.get_filepath()))
        self.image_with_orb = image_with_orb

    def get_image_with_orb(self):
        return self.image_with_orb

    def get_crop_rect(self):
        return self.image_with_orb.get_crop_rect()

    def get_keypoints(self):
        return self.image_with_orb.get_keypoints()

    def get_filepath(self):
        return self.image_with_orb.get_filepath()

    def crop_and_save(self, output_dir):
        self.image_with_orb.crop_and_save(output_dir)

#---------------------------------------------------------------------------------------------------

class FilesTab(qt.QWidget):
    """Display a list of images, and provide an image preview window to
    view each iamge.
    """

    def __init__(self, app_model, parent):
        super(FilesTab, self).__init__(parent)
        self.setObjectName('FilesTab')
        #---------- Setup visible widgets ----------
        self.app_model     = app_model
        self.app_view      = parent
        self.layout        = qt.QHBoxLayout(self)
        self.splitter      = qt.QSplitter(1, self)
        self.setAcceptDrops(True)
        self.splitter.setObjectName('FilesTab splitter')
        self.list_widget   = qt.QListWidget(self)
        self.list_widget.setObjectName('FilesTab list_widget')
        self.list_widget.setContextMenuPolicy(2) # 2 = qcore::ContextMenuPolicy::ActionsContextMenu
        self.image_preview  = ImagePreview(self, self.app_model)
        self.image_preview.setObjectName('FilesTab ImagePreview')
        self.splitter.addWidget(self.list_widget)
        self.splitter.addWidget(self.image_preview)
        self.layout.addWidget(self.splitter)
        self.display_pixmap_path = None
        #---------- Populate list view ----------
        self.reset_paths_list()
        #---------- Setup context menus ----------
        ## Action: Search within this image
        self.use_as_refimg_action = qt.QAction("Search within this image", self)
        self.use_as_refimg_action.setShortcut(qgui.QKeySequence.InsertParagraphSeparator)
        self.use_as_refimg_action.triggered.connect(self.activate_selected_item)
        self.list_widget.addAction(self.use_as_refimg_action)
        self.image_preview.addAction(self.use_as_refimg_action)
        ## Action: open image files
        self.open_image_files = qt.QAction("Open image files", self)
        self.open_image_files.setShortcut(qgui.QKeySequence.Open)
        self.open_image_files.triggered.connect(self.open_image_files_handler)
        self.list_widget.addAction(self.open_image_files)
        self.image_preview.addAction(self.open_image_files)
        ## Action: save image files
        self.save_image_action = qt.QAction("Crop and save this image", self)
        self.save_image_action.setShortcut(qgui.QKeySequence.Save)
        self.save_image_action.triggered.connect(self.do_save_image)
        self.list_widget.addAction(self.save_image_action)
        self.image_preview.addAction(self.save_image_action)
        ## Action: save all image files
        self.save_all_images_action = qt.QAction("Crop and save all images", self)
        self.save_all_images_action.setShortcut(qgui.QKeySequence.SaveAs)
        self.save_all_images_action.triggered.connect(self.do_save_all_images)
        self.list_widget.addAction(self.save_all_images_action)
        self.image_preview.addAction(self.save_all_images_action)
        #---------- Connect signal handlers ----------
        self.list_widget.currentItemChanged.connect(self.item_change_handler)
        self.list_widget.itemActivated.connect(self.activate_handler)

    def get_current_item(self):
        return self.list_widget.currentItem()

    def activate_handler(self, item):
        if item is not None:
            image_with_orb = item.get_image_with_orb()
            #print(f'FilesTab.activate_handler("{image_with_orb.get_filepath()}")')
            self.app_model.set_reference_image(image_with_orb)
            self.app_view.redraw()
            self.app_view.update_display_selection()
            self.app_view.change_to_reference_tab()
        else:
            #print(f'FilesTab.activate_handler(None)')

    def activate_selected_item(self):
        self.activate_handler(self.get_current_item())

    def item_change_handler(self, item, _old):
        if item is not None:
            #print(f'FilesTab.item_change_handler("{item.get_filepath()}")')
            image_with_orb = item.get_image_with_orb()
            if image_with_orb is not None:
                self.app_model.set_selected_image(image_with_orb)
                self.image_preview.update_display_item()
            else:
                #print(f'FilesTab.item_change_handler() #(item.get_image_with_orb() -> None)')
        else:
            #print('FilesTab.item_change_handler(item=None)')

    def update_display_item(self):
        self.image_preview.update_display_item()

    def use_current_item_as_reference(self):
        item = self.list_widget.currentItem()
        self.use_item_as_pattern(item)

    def reset_paths_list(self):
        """Populate the list view with an item for each file path."""
        self.list_widget.clear()
        item_list = self.app_model.get_image_list()
        for item in item_list:
            self.list_widget.addItem(FileListItem(item))

    def add_image_list(self, images):
        self.app_model.add_image_list(images)
        self.reset_paths_list()

    def open_image_files_handler(self):
        target_dir = os.getcwd()
        urls = \
            qt.QFileDialog.getOpenFileUrls(
                self, "Open images in which to search for patterns",
                qcore.QUrl(str(target_dir)),
                'Images (*.png *.jpg *.jpeg)', '',
                qt.QFileDialog.ReadOnly,
                ["file"],
              )
        #print(f'FilesTab #(selected urls = {urls})')
        urls = urls[0]
        if len(urls) > 0:
            self.add_image_list(gather_QUrl_local_files(urls))
        else:
            pass

    def modal_prompt_get_directory(self, init_dir):
        output_dir = \
            qt.QFileDialog.getExistingDirectory( \
                self, "Write images to directory", \
                init_dir, \
                qt.QFileDialog.ShowDirsOnly \
          )
        return PurePath(output_dir)

    def do_save_image(self):
        item = self.get_current_item()
        if item is not None:
            output_dir = self.modal_prompt_get_directory(None)
            item.crop_and_save(output_dir)
        else:
            #print(f'#(cannot save, no item selected)')

    def do_save_all_images(self):
        output_dir = self.modal_prompt_get_directory(None)
        self.app_model.crop_and_save_all(output_dir)

    def focusInEvent(self, event):
        """Here the focusInEvent is overridden, but the parent method is also
        called. If the app_model has been changed (in particular, the
        crop_rect) while the ReferenceImageTab was visible, this tab
        also needs to update it's view.
        """
        #print(f'FilesTab.focusInEvent()')
        self.image_preview.update_display_item()
        super(FilesTab, self).focusInEvent(event)

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls() or mime_data.hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            event.accept()
            self.add_image_list(gather_QUrl_local_files(mime_data.urls()))
        elif mime_data.hasText():
            event.accept()
            self.add_image_list(util.split_linebreaks(mime_data.text()))
        else:
            event.ignore()


#---------------------------------------------------------------------------------------------------

class ConfigTab(qt.QWidget):
    """This appears as a tab in the GUI where you can set the
    configuration options that tweak the settings for the ORB algorithm."""

    def __init__(self, app_model, parent):
        super(ConfigTab, self).__init__(parent)
        self.app_view = parent
        self.app_model = app_model
        self.orb_config = orbm.ORBConfig()
        self.orb_config_undo = []
        self.orb_config_redo = []
        self.notify = qt.QErrorMessage(self)
        ##-------------------- The text fields --------------------
        self.fields = qt.QWidget(self)
        self.nFeatures = qt.QLineEdit(str(self.orb_config.get_nFeatures()))
        self.nFeatures.editingFinished.connect(self.check_nFeatures)
        self.scaleFactor = qt.QLineEdit(str(self.orb_config.get_scaleFactor()))
        self.scaleFactor.editingFinished.connect(self.check_scaleFactor)
        self.nLevels = qt.QLineEdit(str(self.orb_config.get_nLevels()))
        self.nLevels.editingFinished.connect(self.check_nLevels)
        self.edgeThreshold = qt.QLineEdit(str(self.orb_config.get_edgeThreshold()))
        self.edgeThreshold.editingFinished.connect(self.check_edgeThreshold)
        #self.firstLevel = qt.QLineEdit(str(self.orb_config.get_firstLevel()))
        self.WTA_K = qt.QLineEdit(str(self.orb_config.get_WTA_K()))
        self.WTA_K.editingFinished.connect(self.check_WTA_K)
        self.patchSize = qt.QLineEdit(str(self.orb_config.get_patchSize()))
        self.patchSize.editingFinished.connect(self.check_patchSize)
        self.fastThreshold = qt.QLineEdit(str(self.orb_config.get_fastThreshold()))
        self.fastThreshold.editingFinished.connect(self.check_fastThreshold)
        ## -------------------- the form layout --------------------
        self.form_layout = qt.QFormLayout(self.fields)
        self.form_layout.setFieldGrowthPolicy(qt.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form_layout.setLabelAlignment(qcore.Qt.AlignmentFlag.AlignRight)
        self.form_layout.setFormAlignment(qcore.Qt.AlignmentFlag.AlignLeft)
        self.form_layout.addRow('Number of Features (>20, <20000)', self.nFeatures)
        self.form_layout.addRow('Number of Levels (>1, <64)', self.nLevels)
        self.form_layout.addRow('Scale Factor (>1.0, <2.0)', self.scaleFactor)
        self.form_layout.addRow('Edge Threshold (>2, <1024)', self.edgeThreshold)
        self.form_layout.addRow('Patch Size (>2, <1024)', self.patchSize)
        self.form_layout.addRow('WTA Factor (>2, <4)', self.WTA_K)
        self.form_layout.addRow('FAST Threshold (>2, <100)', self.fastThreshold)
        ## -------------------- Control Buttons --------------------
        self.buttons = qt.QWidget(self)
        self.button_layout = qt.QHBoxLayout(self.buttons)
        self.defaults_button = qt.QPushButton('Defaults')
        self.defaults_button.clicked.connect(self.reset_defaults_action)
        self.redo_button = qt.QPushButton('Redo')
        self.redo_button.clicked.connect(self.redo_action)
        self.undo_button = qt.QPushButton('Undo')
        self.undo_button.clicked.connect(self.undo_action)
        self.apply_button = qt.QPushButton('Apply')
        self.apply_button.clicked.connect(self.apply_changes_action)
        self.button_layout.addWidget(self.defaults_button)
        self.button_layout.addWidget(self.redo_button)
        self.button_layout.addWidget(self.undo_button)
        self.button_layout.addWidget(self.apply_button)
        self.after_update()
        ## -------------------- Layout --------------------
        self.whole_layout = qt.QVBoxLayout(self)
        self.whole_layout.addWidget(self.fields)
        self.whole_layout.addWidget(self.buttons)
        self.whole_layout.addStretch()

    def update_field(self, field, fromStr, setter):
        """This function takes a qt.QLineEdit 'field', a function to convert
        it's text to a value to config parameter data, and a 'setter'
        function that sets the value taken from the field. It is
        expected that the 'setter' can raise a ValueError exception if
        the value given cannot be set. This function catches the
        exception and notifies the end user.
        """
        try:
            setter(fromStr(field.text()))
        except ValueError as e:
            self.notify.showMessage(e.args[0])

    def check_nFeatures(self):
        self.update_field(self.nFeatures, int, self.orb_config.set_nFeatures)

    def check_scaleFactor(self):
        self.update_field(self.scaleFactor, float, self.orb_config.set_scaleFactor)

    def check_nLevels(self):
        self.update_field(self.nLevels, int, self.orb_config.set_nLevels)

    def check_edgeThreshold(self):
        self.update_field(self.edgeThreshold, int, self.orb_config.set_edgeThreshold)

    def check_WTA_K(self):
        self.update_field(self.WTA_K, int, self.orb_config.set_WTA_K)

    def check_patchSize(self):
        self.update_field(self.patchSize, int, self.orb_config.set_patchSize)

    def check_fastThreshold(self):
        self.update_field(self.fastThreshold, int, self.orb_config.set_fastThreshold)

    def after_update(self):
        self.redo_button.setEnabled(len(self.orb_config_redo) != 0)
        self.undo_button.setEnabled(len(self.orb_config_undo) != 0)

    def apply_changes_action(self):
        self.check_nFeatures()
        self.check_scaleFactor()
        self.check_nLevels()
        self.check_edgeThreshold()
        self.check_WTA_K()
        self.check_patchSize()
        self.check_fastThreshold()
        self.push_do(self.orb_config_undo)
        #print(f'ConfigTab.apply_changes_action({str(self.orb_config)})')
        self.app_model.set_orb_config(self.orb_config)
        self.after_update()
        ref_orb_image = self.app_model.get_reference_image()
        if ref_orb_image is not None:
            self.app_view.redraw()
            self.app_view.change_to_reference_tab()
        else:
            self.app_view.change_to_files_tab()

    def reset_defaults_action(self):
        #print(f'ConfigTab.reset_defaults_action()')
        self.push_do(self.orb_config_undo)
        self.orb_config = ORBConfig()

    def push_do(self, stack):
        """Pass 'self.orb_config_undo' or 'self.orb_config_redo' as the 'stack' argument."""
        if (len(stack) <= 0) or (stack[-1] != self.orb_config):
            stack.append(self.orb_config)
        else:
            pass

    def shift_do(self, forward, reverse):
        if len(forward) > 0:
            #print(f'ConfigTab.shift_do() #(len(forward) -> {len(forward)}, len(reverse) -> {len(reverse)})')
            self.push_do(reverse)
            self.orb_config = deepcopy(forward[-1])
            del forward[-1]
            self.apply_changes_action()
        else:
            #print(f'ConfigTab.shift_do() #(cannot undo/redo, reached end of stack)')

    def undo_action(self):
        self.shift_do(self.orb_config_undo, self.orb_config_redo)

    def redo_action(self):
        self.shift_do(self.orb_config_redo, self.orb_config_undo)


#---------------------------------------------------------------------------------------------------

class ImageCropKit(qt.QTabWidget):

    """The Qt Widget containing the GUI for the pattern matching program.
    """

    def __init__(self, parent=None):
        super(ImageCropKit, self).__init__(parent)
        self.app_model = orbm.ImageCropper()
        #----------------------------------------
        # Setup the GUI
        self.setWindowTitle('Image Cropp Kit')
        self.resize(800, 600)
        #self.tab_bar = qt.QTabWidget()
        self.setTabPosition(qt.QTabWidget.North)
        self.files_tab = FilesTab(self.app_model, self)
        self.reference_image_tab = ReferenceImageTab(self.app_model, self)
        self.config_tab = ConfigTab(self.app_model, self)
        self.addTab(self.files_tab, "Search")
        self.addTab(self.reference_image_tab, "Reference")
        self.addTab(self.config_tab, "Settings")
        self.currentChanged.connect(self.change_tab_handler)

    def change_tab_handler(self, index):
        """Does the work of actually changing the GUI display to the "InspectTab".
        """
        super(ImageCropKit, self).setCurrentIndex(index)
        selected = self.widget(index)
        selected.setFocus()

    def change_to_files_tab(self):
        self.change_tab_handler(0)

    def change_to_reference_tab(self):
        self.change_tab_handler(1)

    def change_to_config_tab(self):
        self.change_tab_handler(2)

    def update_display_selection(self):
        self.files_tab.update_display_item()

    def redraw(self):
        ref_orb_image = self.app_model.get_reference_image()
        if ref_orb_image is not None:
            #print(f'ImageCropKit.redraw()')
            self.reference_image_tab.redraw()
        else:
            #print(f'ImageCropKit.redraw() #(no reference image)')

