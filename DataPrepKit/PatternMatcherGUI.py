import DataPrepKit.utilities as util
import DataPrepKit.PatternMatcher as patm
from DataPrepKit.PercentSlider import PercentSlider
from DataPrepKit.FileSetGUI import FileSetGUI, qt_modal_image_file_selection
from DataPrepKit.ContextMenuItem import context_menu_item
from DataPrepKit.SimpleImagePreview import SimpleImagePreview
from DataPrepKit.ReferenceImagePreviewGUI import ReferenceImagePreview
from DataPrepKit.CropRectTool import CropRectTool
from DataPrepKit.FileSet import image_file_suffix_set

from pathlib import PurePath

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

####################################################################################################
# The Qt GUI

class InspectImagePreview(SimpleImagePreview):

    def __init__(self, app_model, parent):
        super(InspectImagePreview, self).__init__(parent)
        self.app_model = app_model
        self.rect_items = []
        # TODO: take feature pen and crop pen colors from some global configuration
        self.feature_pen = qgui.QPen(qgui.QColor(0, 255, 0, 255))
        self.feature_pen.setCosmetic(True)
        self.feature_pen.setWidth(3)
        self.crop_pen = qgui.QPen(qgui.QColor(255, 0, 0, 255))
        self.crop_pen.setCosmetic(True)
        self.crop_pen.setWidth(3)

    def clear(self):
        self.clear_rectangles()
        super(InspectImagePreview, self).clear()

    def redraw(self):
        super(InspectImagePreview, self).redraw()
        self.clear_rectangles()
        self.place_rectangles()

    def clear_rectangles(self):
        scene = self.get_scene()
        #print(f'InspectImagePreview.clear_rectangles() #(clear {len(self.rect_items)} items)')
        for rect in self.rect_items:
            scene.removeItem(rect)
        self.rect_items = []

    def place_rectangles(self):
        print(f'{self.__class__.__name__}.place_rectangles()')
        self.clear_rectangles()
        scene = self.get_scene()
        point_list = self.app_model.get_matched_points()
        pen = self.feature_pen
        for (x, y, width, height) in self.app_model.iterate_feature_regions(point_list):
            item = scene.addRect(x, y, width, height, pen)
            self.rect_items.append(item)
        pen = self.crop_pen
        for (_label, (x, y, width, height)) in self.app_model.iterate_crop_regions(point_list):
            item = scene.addRect(x, y, width, height, pen)
            self.rect_items.append(item)

#---------------------------------------------------------------------------------------------------

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
            fileset=app_model.get_target_fileset(),
            action_label='Search within this image',
          )
        self.app_model = app_model
        ## Action: Use as pattern
        self.use_as_pattern = context_menu_item(
            "Use as pattern",
            self.use_current_item_as_reference,
            qgui.QKeySequence.Find,
          )
        self.list_widget.addAction(self.use_as_pattern)
        if self.image_display is not None:
            self.image_display.addAction(self.use_as_pattern)
        else:
            pass
        self.setSizePolicy(
            qt.QSizePolicy(
                qt.QSizePolicy.Expanding, qt.QSizePolicy.Expanding
              ),
          )

    def activation_handler(self, path):
        self.app_model.set_target_image_path(path)
        self.app_model.match_on_file()
        distance_map = self.app_model.get_distance_map()
        if distance_map:
            self.main_view.show_distance_map()
            self.main_view.show_inspect_tab()
        else:
            self.main_view.show_pattern_tab()
            self.main_view.error_message(
                "A pattern image must be set for matching on the selected image.",
              )

    def use_current_item_as_reference(self):
        path = self.current_item_path()
        print(f'FilesTab.use_current_item_as_reference() #("{path}")')
        self.app_model.set_reference_image_path(path)
        self.main_view.update_reference_pixmap()

#---------------------------------------------------------------------------------------------------

class RegionSelectionTool(CropRectTool, patm.SingleFeatureMultiCrop):
    """This is a version of "CropRectTool" configured to define the
    rectangular regions within "SingleFeatureMultiCrop" model.

    This tool instantiates "SingleFeatureMultiCrop", as does the
    "PatternMatcher" app model, many of the methods of
    "SingleFeatureMultiCrop" are overridden to update the internal
    state of this tool, which contains objects that are drawn in the
    "QGraphicsScene", and simultaneously calls the exact same
    "SingleFeatureMultiCrop" APIs of the "app_model". This ensures the
    view is an accurate representation of the app model.

    To set which rectangle is being updated by this tool, call the
    "set_region_selection()" method. Calling this function with None
    as an argument selects the feature region.

    The pen colors can be customized by calling
    "set_feature_region_pen()" and "set_crop_region_pen()".

    """

    def __init__(self, app_model, scene):
        super().__init__(scene)
        patm.SingleFeatureMultiCrop.__init__(self)
        self.app_model = app_model
        self.set_feature_region_pen(CropRectTool._green_pen)
        self.set_crop_region_pen(CropRectTool._red_pen)
        self.redraw_all_regions()

    ###############  Methods to configure the pen colors  ###############

    # Consider using the default colors defined as static slots of the
    # CropRectTool, such as "CropRectTool._red_pen" "CropRectTool._green_pen".

    def get_feature_region_pen(self):
        return self.feature_region_pen

    def set_feature_region_pen(self, pen):
        if not isinstance(pen, qgui.QPen):
            raise ValueError('received argument that is not a QPen')
        else:
            self.feature_region_pen = pen

    def get_crop_region_pen(self):
        return self.crop_region_pen

    def set_crop_region_pen(self, pen):
        if not isinstance(pen, qgui.QPen):
            raise ValueError('received argument that is not a QPen')
        else:
            self.crop_region_pen = pen

    ###############  Methods for redrawing everything  ###############

    # Use these if for whatever reason the CropRectTool of the
    # 'PatternMatcher' app model and the parent # 'SingleFeatureMultiCrop'
    # of this class somehow become out-of-sync.

    def clear_feature_region(self):
        scene = self.get_scene()
        if self.feature_region:
            scene.removeItem(self.featureRegion)
            self.feature_region = None
        else:
            pass

    def clear_crop_regions(self):
        scene = self.get_scene()
        if self.crop_regions is None or len(self.crop_regions) == 0:
            pass
        else:
            for (label, rect) in self.crop_regions.items():
                scene.removeItem(rect)
                del self.crop_regions[label]
            self.crop_regions = {}

    def redraw_all_regions(self):
        """Copies the crop regions from the global state to this local GUI object."""
        self.clear_feature_region()
        feature_region = self.app_model.get_feature_region()
        scene = self.get_scene()
        if feature_region:
            qrectf = qcore.QRectF(*feature_region)
            self.feature_region = scene.addRect(qrectf, self.feature_region_pen)
            self.redraw_crop_regions(feature_region[0], feature_region[1])
        else:
            self.redraw_crop_regions(0, 0)

    def redraw_crop_regions(self, x_off, y_off):
        self.clear_crop_regions()
        crop_regions = self.app_model.get_crop_regions()
        scene = self.get_scene()
        if (crop_regions is None) or (len(crop_regions) == 0):
            self.crop_regions = {}
        else:
            self.crop_regions = {}
            for (label, (x, y, width, height)) in crop_regions.items():
                rect = qcore.QRectF(x+x_off, y+y_off, width, height)
                self.crop_regions[label] = scene.addRect(rect, self.crop_region_pen)

    ###############  Overrides  ###############

    def draw_rect_updated(self, rect):
        """This method receives events from the CropRectTool parent class
        every time a rectangular region is updated by the end user. It
        calls "set_crop_region_selection()" which uses the
        "self.crop_region_selection" state variable to decide which
        rectangular region receives the update."""
        print(f'{self.__class__.__name__}.draw_rect_updated({rect!r})')
        self.set_crop_region_selection(rect)
        #self.clear_crop_rect()

    def draw_rect_cleared(self):
        """This method receives events from the CropRectTool parent class
        every time an end user begins drawing a rectangular region,
        and the if there is a currently selected rectangular region,
        it should be deleted so it can be re-drawn. """
        scene = self.get_scene()
        if self.crop_region_selection is None:
            if self.feature_region is not None:
                scene.removeItem(self.feature_region)
                self.feature_region = None
            else:
                pass
        elif self.crop_region_selection in self.crop_regions:
            scene.removeItem(self.crop_regions[self.crop_region_selection])
            del self.crop_regions[self.crop_region_selection]
        else:
            pass

    def set_region_selection(self, label):
        print(f'{self.__class__.__name__}.set_region_selection({label!r})')
        patm.SingleFeatureMultiCrop.set_region_selection(self, label)
        self.app_model.set_region_selection(label)
        CropRectTool.set_draw_pen(
            self,
            self.get_feature_region_pen() if label is None else \
              self.get_crop_region_pen(),
          )

    def add_crop_region(self, label, rect):
        """Creates a new crop region, if the crop region already exists it is deleted."""
        print(f'{self.__class__.__name__}.add_crop_region({label!r}, {rect!r})')
        scene = self.get_scene()
        #----------------------------------------
        if label is None:
            raise ValueError('label is None')
        elif label in self.crop_regions:
            return False
            #rect_item = self.crop_regions[label]
            #scene.removeItem(rect_item)
        elif rect is not None:
            qrectf = qcore.QRectF(*rect)
            self.crop_regions[label] = scene.addRect(qrectf, self.crop_region_pen)
            return True
        else:
            self.crop_regions[label] = None
            return True

    def get_feature_region(self, rect):
        return (self.feature_region.rect() if self.feature_region is not None else None)

    def set_feature_region(self, rect):
        print(f'{self.__class__.__name__}.set_feature_region({rect!r})')
        self.app_model.set_feature_region(rect)
        qrectf = qcore.QRectF(*rect)
        if self.feature_region is not None:
            # Update the state of self.feature_region
            self.feature_region.setRect(qrectf)
        else:
            scene = self.get_scene()
            self.feature_region = scene.addRect(qrectf, self.feature_region_pen)
        print(f'{self.__class__.__name__}.set_crop_region_selection({rect}) #(updated feature region)')

    def get_crop_region_selection(self, label, rect):
        qrectf = super(SingleFeatureMultiCrop, self).get_crop_region_selection()
        return (qrectf.x(), qrectf.y(), qrectf.width(), qrectf.height(),)

    def set_crop_region_selection(self, rect):
        """This method takes 4-tuple rectangle (x,y,width,height).
        Uses the 'self.crop_region_selection' (set by 'self.set_region_selection()')
        to create a new entry in the 'self.crop_regions' dictionary.
        If the dictionary contains no such label, a new entry is created.
        If the 'self.crop_region_selection' is None, the given 'rect'
        argument is used to set the 'self. """
        print(f'{self.__class__.__name__}.set_crop_region_selection({rect!r}) #(self.crop_region_selection = {self.crop_region_selection})')
        self.app_model.set_crop_region_selection(rect)
        scene = self.get_scene()
        #----------------------------------------
        if self.crop_region_selection is None:
            # Selection is None, act on feature rect
            self.set_feature_region(rect)
        else:
            # If the selected crop region exists, update it.
            self.app_model.set_crop_region_selection(rect)
            qrectf = qcore.QRectF(*rect)
            if (self.crop_region_selection not in self.crop_regions) or \
              (self.crop_regions is None):
                self.crop_regions[self.crop_region_selection] = \
                    scene.addRect(qrectf, self.crop_region_pen)
            else:
                self.crop_regions[self.crop_region_selection].setRect(qrectf)
            print(
                f'{self.__class__.__name__}.set_crop_region_selection({rect}) '
                f'#(updated crop region "{self.crop_region_selection}"))'
              )

    ###############  Debugging methods  ###############

    def rect_to_str(self, rect):
        return repr(rect.rect() if rect is not None else None)


#---------------------------------------------------------------------------------------------------

class PatternPreview(ReferenceImagePreview):

    def __init__(self, app_model, main_view):
        super().__init__(app_model, main_view)
        self.crop_rect_tool = RegionSelectionTool(app_model, self.get_scene()) #(, self.crop_rect_updated)
        self.set_mouse_mode(self.crop_rect_tool)
        self.setSizePolicy(
            qt.QSizePolicy(
                qt.QSizePolicy.Expanding,
                qt.QSizePolicy.Expanding,
              ),
          )

    def get_crop_rect_tool(self):
        return self.crop_rect_tool

    def set_selected_crop_rect(self, name):
        if name == ActiveSelectorModel.features_title:
            name = None
        else:
            pass
        self.crop_rect_tool.set_region_selection(name)

    def get_selected_crop_rect(self):
        return self.crop_rect_tool.get_region_selection()

    def rename_crop_region(self, old_name, new_name):
        self.crop_rect_tool.rename_crop_region(old_name, new_name)

    def clear(self):
        self.crop_rect_tool.clear()
        super(ReferenceImagePreview, self).clear()

    def redraw(self):
        super(ReferenceImagePreview, self).redraw()
        self.crop_rect_tool.redraw()

#---------------------------------------------------------------------------------------------------

class ActiveSelectorModel(qcore.QStringListModel):
    """An abstract model wrapper around the crop regions and feature
    region so it can be presented to the end user as a QListWidget."""

    features_title = '#Features'

    def reset_data_with(names):
        list_model = [ActiveSelectorModel.features_title]
        list_model += names
        return list_model

    def __init__(self, parent_view, names):
        list_model = ActiveSelectorModel.reset_data_with(names)
        super().__init__(list_model)
        self.list_model = list_model
        self.parent_view = parent_view
        self.crop_rect_tool = self.parent_view.get_preview_view().get_crop_rect_tool()
        self.active_selector_count = 0

    def reset_data(self, names):
        self.list_model = ActiveSelectorModel.reset_data_with(names)

    def rowCount(self, _parent):
        return len(self.list_model)

    def flags(self, index):
        flags = \
            qcore.Qt.ItemFlag.ItemIsSelectable | \
            qcore.Qt.ItemFlag.ItemIsEnabled
        if (index.row() == 0) or \
          (index.data() == ActiveSelectorModel.features_title):
            return flags
        else:
            return flags | qcore.Qt.ItemFlag.ItemIsEditable

    def data(self, qi, role):
        row = qi.row()
        if (role == qcore.Qt.ItemDataRole.DisplayRole) or \
          (role == qcore.Qt.ItemDataRole.EditRole):
            #print(f'ActiveSelectorModel.data({row}, {role})')
            if row == 0:
                return ActiveSelectorModel.features_title
            elif row < len(self.list_model):
                return self.list_model[row]
            else:
                return None
        else:
            return None

    def setData(self, qi, new_name, role):
        print(f'ActiveSelectorModel.setData({qi.row()}, {new_name!r}, {role})')
        if role == qcore.Qt.ItemDataRole.EditRole:
            i = qi.row()
            if (i == 0) or (new_name == ActiveSelectorModel.features_title):
                # Zeroth index is protected, cannot be edited or deleted.
                print(f'ActiveSelectorModel.setData({i}, "{new_name}", {role}) #(refuse to edit index {i} = {old_name!r})')
                return False
            elif (i < 0) or (i >= len(self.list_model)):
                # If we get an out-of-bounds index, this is row that
                # doesn't exist yet and needs to be created.
                if self.crop_rect_tool.add_crop_region(new_name, None):
                    index = self.parent_view.currentIndex()
                    if index is None:
                        self.list_model.append(new_name)
                    else:
                        i = max(1, index.row() + 1)
                        self.list_model.insert(i, new_name)
                    print(f'ActiveSelectorModel.setData({i}, {new_name!r}, {role}) #(list_model = {self.list_model}, crop_regions = {self.crop_rect_tool.get_crop_regions()})')
                    return True
                else:
                    print(f'ActiveSelectorModel.setData({i}, {new_name!r}, {role}) #(name already exists)')
                    self.report_duplicate_name(new_name)
                    return False
            else:
                # If the row is in bounds, it is modifying an existing entry.
                old_name = self.list_model[i]
                if self.crop_rect_tool.rename_crop_region(old_name, new_name):
                    self.list_model[i] = new_name
                    print(f'ActiveSelectorModel.setData({i}, {new_name!r}, {role}) #(list_model = {self.list_model}, crop_regions = {self.crop_rect_tool.get_crop_regions()})')
                    return True
                else:
                    print(f'ActiveSelectorModel.setData({i}, {new_name!r}, {role}) #(failed to rename {old_name!r})')
                    return False
        else:
            print(f'ActiveSelectorModel.setData({i}, "{new_name!r}", {role}) #(meaningless role {role})')
            return False

    def get_index(self, index):
        if isinstance(index, qcore.QModelIndex):
            index = index.row()
        else:
            pass
        if isinstance(index, int):
            if index < len(self.list_model):
                return self.list_model[index]
            else:
                return None            
        else:
            raise ValueError(f'index of wrong type: {type(index)}')

    def new_name_for_crop_region(self):
        self.active_selector_count += 1
        return f'crop_{self.active_selector_count:0>2}'

    def rename_crop_region(self, old_name, new_name):
        if self.crop_rect_tool.rename_crop_region(old_name, new_name):
            return True
        else:
            self.report_duplicate_name(self, new_name)
            return False

    def report_duplicate_name(self, name):
        self.parent_view.error_message(f'Crop region named {name!r} already exists.')

    def new_crop_region(self):
        i = len(self.list_model)
        print(f'ActiveSelectorModel.new_crop_region() #(index = {i})')
        qi = self.index(i, 0)
        name = self.new_name_for_crop_region()
        if self.insertRow(i):
            self.setData(qi, name, qcore.Qt.ItemDataRole.EditRole)
            print(f'ActiveSelectioModel.new_crop_region() #(self.list_model = {self.list_model})')
            self.crop_rect_tool.add_crop_region(name, None)
            return qi
        else:
            print(f'ActiveSelectorModel.new_crop_region() #(failed to insert row)')
            return None

    def delete_crop_region(self, i):
        if 0 <= i and i < len(self.list_model):
            self.removeRow(i)
            del self.list_model[i]
        else:
            pass


class ActiveSelector(qt.QListView):
    """The list of rectangular regions that are selected from the reference image."""

    def __init__(self, app_model, parent_view):
        super().__init__(parent_view)
        self.setObjectName("Active Selector")
        self.setSizePolicy(
            qt.QSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Preferred),
          )
        self.parent_view = parent_view
        self.setDragDropMode(qt.QAbstractItemView.InternalMove)
        self.active_selector = ActiveSelectorModel(
            self,
            list(app_model.get_crop_regions().keys()),
          )
        super().setModel(self.active_selector)
        self.reset_selector_items()
        self.pressed.connect(self.select_region_item)
        ##---------- Setup context menus ----------
        #self.do_new_crop_region = context_menu_item(
        #    "New crop region",
        #    self.new_crop_region,
        #    '+',
        #  )
        #self.addAction(self.do_new_crop_region)
        ##----------
        #self.do_delete_crop_region = context_menu_item(
        #    "Delete crop region",
        #    self.delete_crop_region,
        #    '-',
        #  )
        #self.addAction(self.do_delete_crop_region)
        ##----------
        self.setContextMenuPolicy(qcore.Qt.ContextMenuPolicy.ActionsContextMenu)

    def error_message(self, message):
        self.parent_view.error_message(message)

    def get_preview_view(self):
        return self.parent_view.get_preview_view()

    def new_crop_region(self):
        qi = self.active_selector.new_crop_region()
        if qi is not None:
            self.setCurrentIndex(qi)
            self.edit(qi)
        else:
            pass

    def delete_crop_region(self):
        qi = self.currentIndex()
        if qi is not None:
            self.active_selector.delete_crop_region(qi.row())
        else:
            pass

    def rename_crop_region(self, old_name, new_name):
        self.parent_view.rename_crop_region(old_name, new_name)

    def reset_selector_items(self, crop_regions=None):
        self.active_selector.reset_data(
            list(crop_regions.keys()) if crop_regions is not None else [],
          )

    def select_region_item(self, index):
        print(f'ActiveSelector.select_region_item({index.row()})')
        name = self.active_selector.get_index(index.row())
        if name == ActiveSelectorModel.features_title:
            name = None
        else:
            pass
        self.parent_view.set_selected_crop_rect(name)


class PatternSetupTab(qt.QWidget):

    def __init__(self, app_model, main_view):
        screenWidth = qgui.QGuiApplication.primaryScreen().virtualSize().width()
        super().__init__(main_view)
        self.setObjectName("PatternSetupTab")
        self.setAcceptDrops(True)
        self.app_model    = app_model
        self.main_view    = main_view
        self.layout       = qt.QHBoxLayout(self)
        self.preview_view = PatternPreview(app_model, self)
        self.active_selector = ActiveSelector(app_model, self)
        self.splitter     = qt.QSplitter(qcore.Qt.Orientation.Horizontal, self)
        self.splitter.setObjectName("PatternTab splitter")
        self.splitter.insertWidget(0, self.active_selector)
        self.splitter.insertWidget(1, self.preview_view)
        self.layout.addWidget(self.splitter)
        self.setAcceptDrops(True)
        ## Action: open image files
        self.open_pattern_file = context_menu_item(
            "Open pattern file",
            self.open_pattern_file_handler,
            qgui.QKeySequence.Open,
          )
        self.preview_view.addAction(self.open_pattern_file)
        ## Action: add new crop region
        self.do_add_selector_item = context_menu_item(
            'New crop region',
            self.add_selector_item_action,
            '+'
          )
        self.active_selector.addAction(self.do_add_selector_item)
        #----------
        self.do_delete_selector_item = context_menu_item(
            'Delete crop region',
            self.delete_selector_item_action,
            '-'
          )
        self.active_selector.addAction(self.do_delete_selector_item)

    def error_message(self, message):
        self.main_view.error_message(message)

    def get_preview_view(self):
        return self.preview_view

    def add_selector_item_action(self):
        self.active_selector.new_crop_region()

    def delete_selector_item_action(self):
        self.active_selector.delete_crop_region()

    def update_reference_pixmap(self):
        self.preview_view.update_reference_pixmap()

    def set_reference_image_path(self, path):
        #print(f'FilesTab.use_current_item_as_pattern() #("{path}")')
        self.app_model.set_reference_image_path(path)
        self.update_reference_pixmap()

    def open_pattern_file_handler(self):
        target_dir = self.app_model.get_config().pattern
        urls = qt_modal_image_file_selection(
            self,
            default_dir=target_dir,
            message='Open images in which to search for patterns',
          )
        if len(urls) > 0:
            self.set_reference_image_path(urls[0])
            if len(urls) > 1:
                print(f'WARNING: multiple files selected as pattern path, using only first one "{urls[0]}"')
            else:
                pass
        else:
            print(f'PatternSetupTab.open_pattern_file_handler() #(file selection dialog returned empty list)')

    def add_crop_region(self, rect, label):
        self.active_selector.addItem(qt.QListWidgetItem('Crop'))
        
    def set_selected_crop_rect(self, label):
        self.preview_view.set_selected_crop_rect(label)

    def rename_crop_region(self, old_name, new_name):
        """Updates the "self.preview_view", which mirrors, but is a different
        object from, the "self.app_model.crop_regions" dictionary. """
        self.preview_view.rename_crop_region(old_name, new_name)

#---------------------------------------------------------------------------------------------------

class EncodingMenu(qt.QGroupBox):
    """Group box showing the popup-down menu where the image encoding can be selected."""

    def __init__(self, title, app_model, parent):
        super().__init__(title, parent=parent)
        self.app_model = app_model
        self.setSizePolicy(
            qt.QSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Minimum)
          )
        self.layout = qt.QHBoxLayout(self)
        self.menu = qt.QMenu('Choose Encoding', parent=self)
        # Add most popular encodings at the top.
        self.menu.addAction('PNG')
        self.menu.addAction('BMP')
        self.menu.addAction('JPG')
        self.menu.addSeparator()
        # Add all other encodings, it's OK to insert duplicates items,
        # the text of the menu item is used to decide the action.
        for item in image_file_suffix_set:
            self.menu.addAction(item.upper())
        self.menu.triggered.connect(self.menu_item_selected)
        self.popup_menu = qt.QPushButton(self)
        self.popup_menu.setText('PNG')
        self.popup_menu.setMenu(self.menu)
        self.layout.addWidget(self.popup_menu)
        self.layout.setSizeConstraint(qt.QLayout.SizeConstraint.SetFixedSize)
        self.setLayout(self.layout)

    def menu_item_selected(self, action):
        print(f'InspectTabControl.menu_item_selected("{action.text()}")')
        self.app_model.set_file_encoding(action.text())
        self.popup_menu.setText(action.text())


class InspectTabControl(qt.QWidget):
    """The upper control bar for the Inspect tab"""

    def __init__(self, app_model, inspect_tab):
        super().__init__(inspect_tab)
        self.setObjectName('InspectTab controls')
        self.app_model = app_model
        self.inspect_tab = inspect_tab
        self.setSizePolicy(
            qt.QSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Minimum)
          )
        self.layout = qt.QHBoxLayout(self)
        config = app_model.get_config()
        # ---------- setup slider ----------
        self.slider = PercentSlider(
            "Threshold %",
            config.threshold,
            inspect_tab.slider_handler,
          )
        # ---------- setup popup-menu ----------
        self.encoding_menu = EncodingMenu('Encoding', self.app_model, parent=self)
        # ---------- lay out the widgets ----------
        self.layout.addWidget(self.encoding_menu)
        self.layout.addWidget(self.slider)


class InspectTab(qt.QWidget):
    """This tab shows an image on which the pattern matching computation
    has been run, and outlines the matched areas of the image with a
    red rectangle."""

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
        self.layout.setObjectName('InspectTab layout')
        self.control_widget = InspectTabControl(app_model, self)
        self.slider = self.control_widget.slider
        self.layout.addWidget(self.control_widget)
        self.message_box = MessageBox("Please select SEARCH target image and PATTERN image.")
        self.layout.addWidget(self.message_box)
        self.image_display = InspectImagePreview(self.app_model, self)
        image_display_size_policy = self.image_display.sizePolicy()
        image_display_size_policy.setRetainSizeWhenHidden(True)
        self.image_display.setSizePolicy(image_display_size_policy)
        self.image_display.hide()
        self.layout.addWidget(self.image_display)
        #---------- Setup context menus ----------
        self.do_save_selected = context_menu_item(
            "Save selected regions",
            self.save_selected,
            qgui.QKeySequence.Save,
          )
        self.image_display.addAction(self.do_save_selected)
        #----------
        self.do_save_selected_all = context_menu_item(
            "Save selected regions, all files",
            self.save_selected_all,
            qgui.QKeySequence.SaveAs,
          )
        self.image_display.addAction(self.do_save_selected_all)
        #----------
        self.do_move_next_image = context_menu_item(
            "Search Next Image",
            self.search_next_image,
            qgui.QKeySequence.MoveToNextPage,
          )
        self.image_display.addAction(self.do_move_next_image)
        #----------
        self.do_move_previous_image = context_menu_item(
            "Search Previous Image",
            self.search_previous_image,
            qgui.QKeySequence.MoveToPreviousPage,
          )
        self.image_display.addAction(self.do_move_previous_image)

    def slider_handler(self, new_value):
        threshold = self.slider.get_percent()
        if threshold is not None:
            self.app_model.change_threshold(threshold)
            if self.app_model.get_feature_region() is not None:
                self.image_display.redraw()
            else:
                pass
        else:
            pass

    def show_nothing(self):
        self.image_display.hide()
        self.message_box.show()

    def show_image_display(self):
        self.message_box.hide()
        self.image_display.show()

    def show_distance_map(self):
        """Draws the target image and any matching pattern rectangles into the
        image_display window."""
        self.distance_map = self.app_model.get_distance_map()
        target = self.distance_map.get_target()
        path = self.app_model.get_target_image_path()
        self.image_display.set_filepath(path)
        self.image_display.redraw()
        self.show_image_display()
        self.do_save_selected.setEnabled(True)

    def modal_prompt_get_directory(self, init_dir):
        output_dir = \
            qt.QFileDialog.getExistingDirectory(
                self, "Write images to directory",
                init_dir,
                qt.QFileDialog.ShowDirsOnly,
              )
        return PurePath(output_dir)

    def get_files_list(self):
        return self.main_view.files_tab.get_list_widget()

    def current_file_index(self):
        """Looks into the files tab and returns the index of the currently
        selected item, along with the number of items."""
        listwidget = self.get_files_list()
        return (listwidget.currentRow(), listwidget.count())

    def save_selected(self):
        if self.distance_map is not None:
            output_dir = self.app_model.get_config().output_dir
            output_dir = self.modal_prompt_get_directory(str(output_dir))
            self.app_model.set_results_dir(PurePath(output_dir))
            threshold = self.slider.get_percent()
            self.app_model.write_all_cropped_images(
                self.distance_map,
                threshold,
                output_dir,
              )
        else:
            print('WARNING: InspectTab.save_selected() called before distance_map was set')

    def save_selected_all(self):
        output_dir = self.app_model.get_config().output_dir
        output_dir = self.modal_prompt_get_directory(str(output_dir))
        self.app_model.set_results_dir(PurePath(output_dir))
        self.app_model.batch_crop_matched_patterns()

    def search_next_image(self):
        (row, count) = self.current_file_index()
        if row is None:
            self.main_view.error_messge('Please select an image in the "Files" tab')
        elif row+1 >= count:
            self.main_view.error_message('No further images in "Files" tab, currently viewing last image')
        else:
            listwidget = self.get_files_list()
            listwidget.setCurrentRow(row+1)
            item = listwidget.item(row+1)
            listwidget.setCurrentItem(item)
            self.main_view.files_tab.activation_handler(item.get_path())

    def search_previous_image(self):
        (row, count) = self.current_file_index()
        if row is None:
            self.main_view.error_messge('Please select an image in the "Files" tab')
        elif row-1 <= 0:
            self.main_view.error_message('No further images in "Files" tab, currently viewing last image')
        else:
            listwidget = self.get_files_list()
            listwidget.setCurrentRow(row-1)
            item = listwidget.item(row-1)
            listwidget.setCurrentItem(item)
            self.main_view.files_tab.activation_handler(item.get_path())

#---------------------------------------------------------------------------------------------------

class PatternMatcherView(qt.QTabWidget):
    """The Qt Widget containing the GUI for the whole pattern matching program.
    """

    def __init__(self, app_model, main_view=None):
        super().__init__(main_view)
        self.app_model = app_model
        #----------------------------------------
        # Setup the GUI
        self.notify = qt.QErrorMessage(self)
        self.setWindowTitle("Image Pattern Matching Kit")
        self.resize(1280, 720)
        self.setTabPosition(qt.QTabWidget.North)
        self.files_tab = FilesTab(app_model, self)
        self.files_tab.default_image_display_widget()
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

    def update_reference_pixmap(self):
        self.pattern_tab.update_reference_pixmap()
        self.show_pattern_tab()

