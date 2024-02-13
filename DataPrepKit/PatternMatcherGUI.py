import DataPrepKit.utilities as util
import DataPrepKit.RMEMatcher as rme
import DataPrepKit.ORBMatcher as orb
from DataPrepKit.PercentSlider import PercentSlider
from DataPrepKit.FileSetGUI import FileSetGUI, qt_modal_image_file_selection
from DataPrepKit.ContextMenuItem import context_menu_item
from DataPrepKit.SimpleImagePreview import SimpleImagePreview
from DataPrepKit.ReferenceImagePreviewGUI import ReferenceImagePreview
from DataPrepKit.CropRectTool import CropRectTool
from DataPrepKit.FileSet import image_file_suffix_set
from DataPrepKit.EncodingMenu import EncodingMenu
from DataPrepKit.SingleFeatureMultiCrop import SingleFeatureMultiCrop

import DataPrepKit.GUIHelpers as dpk

from pathlib import Path, PurePath
import os
#import traceback

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

####################################################################################################
# The Qt GUI

class ProgressDialog(qt.QProgressDialog):

    def __init__(self, window_title, cancel_title, min_value, max_value, main_view):
        super(ProgressDialog, self).__init__(
            window_title,
            cancel_title,
            min_value,
            max_value,
            parent=main_view
          )
        self.main_view = main_view
        self.setValue(min_value)
        self.setMinimumDuration(1000)
        self.setWindowModality(qcore.Qt.WindowModal)

    def fail_if_canceled(self):
        """Raises a RuntimeError if the Cancel button has been pressed
        recently, otherwise does nothing. This function is
        automatically called by both the "add_work()" and
        "update_progress()" methods. """
        if self.wasCanceled():
            label = self.label()
            #print(f'{self.__class__.__name__}.fail_if_canceled()')
            raise RuntimeError(f'{str(label)!r} process canceled')
        else:
            pass

    def update_label(self, label=None):
        if label is not None:
            self.setLabelText(label)
        else:
            pass

    def add_work(self, count, label=None):
        """Add (or subtract) to the total number of things remaining to be done."""
        self.fail_if_canceled()
        self.update_label(label)
        self.setMaximum(self.maximum() + count)
        #print(f'{self.__class__.__name__}.add_work({count}) #(maximum = {self.maximum()})')

    def update_progress(self, steps, label=None):
        """Add (or subtract) to the total amount of work that has already been done."""
        self.fail_if_canceled()
        self.update_label(label)
        self.setValue(self.value() + steps)
        #print(f'{self.__class__.__name__}.update_progress({steps}, {label!r}) #(value = {self.value()})')

    # def accept(self):
    #     print(f'{self.__class__.__name__}.accept()')
    #     qt.QProgressDialog.accept(self)
        
    # def reject(self):
    #     print(f'{self.__class__.__name__}.reject()')
    #     qt.QProgressDialog.reject(self)
        

class InspectImagePreview(SimpleImagePreview):

    def __init__(self, main_view, parent):
        super(InspectImagePreview, self).__init__(parent)
        self.main_view = main_view

    def post_init(self):
        pass

    def clear(self):
        self.clear_rectangles()
        SimpleImagePreview.clear(self)

    def redraw(self):
        #print(f'{self.__class__.__name__}.redraw()')
        app_model = self.main_view.get_app_model()
        match_list = app_model.get_matched_points()
        self.redraw_regions(match_list)

    def redraw_regions(self, match_list):
        #print(f'{self.__class__.__name__}.redraw_regions(match_list) #(len(match_list) = {len(match_list)})')
        SimpleImagePreview.redraw(self)
        self.clear_rectangles()
        self.place_rectangles(match_list)

    def clear_rectangles(self):
        #print(f'InspectImagePreview.clear_rectangles() #(clear {len(self.visualized_match_list)} items)')
        visualizer = self.main_view.get_visualizer()
        visualizer.clear_matches()

    def place_rectangles(self, match_list):
        #print(f'{self.__class__.__name__}.place_rectangles()')
        app_model = self.main_view.get_app_model()
        crop_regions = app_model.get_crop_regions()
        visualizer = self.main_view.get_visualizer()
        #print(f'{self.__class__.__name__}.place_rectangles() #(len(match_list) = {len(match_list)})')
        visualizer.clear_matches()
        for match in match_list:
            visualizer.draw_matches(match, crop_rect_dict=crop_regions)

#---------------------------------------------------------------------------------------------------

class AbstractMatchVisualizer():

    def __init__(self, main_view):
        self.main_view = main_view

    def draw_matches(self, match_item, crop_rect_dict=None):
        pass

    def draw_features(self):
        pass

    def clear(self):
        #print(f'{self.__class__.__name__}.clear()')
        self.clear_matches()
        self.clear_reference()

    def get_match_scene(self):
        widget = self.main_view.get_inspect_widget()
        return widget.get_image_display().get_scene()

    def get_reference_scene(self):
        widget = self.main_view.get_reference_widget()
        return widget.get_image_display().get_scene()


class RMEMatchVisualizer(AbstractMatchVisualizer):

    def __init__(self, main_view):
        super().__init__(main_view)
        self.feature_qrect = None
        self.crop_region_qrect_list = []

    def get_match_scene(self):
        return AbstractMatchVisualizer.get_match_scene(self)

    def clear_matches(self):
        #print(f'{self.__class__.__name__}.clear()')
        if self.feature_qrect is not None:
            match_scene = self.get_match_scene()
            if match_scene is not None:
                match_scene.removeItem(self.feature_qrect)
                self.feature_qrect = None
            else:
                pass
        else:
            pass
        for item in self.crop_region_qrect_list:
            match_scene = self.get_match_scene()
            if match_scene is not None:
                match_scene.removeItem(item)
            else:
                pass
        self.crop_region_qrect_list = []

    def clear_reference(self):
        pass

    def draw_matches(self, match_item, crop_rect_dict=None):
        #print(f'{self.__class__.__name__}.draw_matches()')
        scene = self.get_match_scene()
        pen = self.main_view.get_feature_region_pen()
        (x0, y0, width, height) = match_item.get_rect()
        self.feature_qrect = scene.addRect(x0, y0, width, height, pen)
        pen = self.main_view.get_crop_region_pen()
        if crop_rect_dict is not None:
            for (_label, (x, y, width, height)) in crop_rect_dict.items():
                item = scene.addRect(x+x0, y+y0, width, height, pen)
                self.crop_region_qrect_list.append(item)
        else:
            pass

    def draw_features(self):
        #print(f'{self.__class__.__name__}.draw_features()')
        return []


class ORBMatchVisualizer(AbstractMatchVisualizer):

    def __init__(self, main_view):
        super().__init__(main_view)
        if not isinstance(main_view, PatternMatcherView):
            raise ValueError(f'type(main_view) is {type(main_view)}, not an instance of PatternMatcherView', main_view)
        else:
            pass
        self.feature_point_list = []
        self.feature_line_list = []
        self.feature_point_list = []
        self.crop_region_line_list_list = []
        self.reference_point_list = []

    def clear_matches(self):
        #print(f'{self.__class__.__name__}.clear_matches()')
        scene = self.get_match_scene()
        if scene is None:
            for item in self.feature_point_list:
                scene.removeItem(item)
            self.feature_point_list = []
        else:
            pass
        for item in self.feature_line_list:
            scene.removeItem(item)
        #print(f'{self.__class__.__name__}.clear_references() #(removed {len(self.feature_line_list)} match feature items)')
        self.feature_line_list = []
        for crop_region_line_list in self.crop_region_line_list_list:
            for crop_region_line in crop_region_line_list:
                scene.removeItem(crop_region_line)
        #print(f'{self.__class__.__name__}.clear_references() #(removed {len(self.crop_region_line_list_list)} matching region items)')
        self.crop_region_line_list_list = []

    def clear_reference(self):
        #print(f'{self.__class__.__name__}.clear_references()')
        scene = self.get_reference_scene()
        if scene is None:
            #print(f'{self.__class__.__name__}.clear_references() #(scene is not defined)')
            return None
        else:
            pass
        for item in self.reference_point_list:
            scene.removeItem(item)
        self.reference_point_list = []
        #print(f'{self.__class__.__name__}.clear_references() #(removed {len(self.feature_point_list)} feature point items)')

    def draw_point(scene, x, y, pen):
        return scene.addEllipse(round(x-9), round(y-9), 18, 18, pen)

    def draw_matches(self, match_item, crop_rect_dict=None):
        #print(f'{self.__class__.__name__}.draw_matches()')
        scene = self.get_match_scene()
        if scene is None:
            return None
        else:
            pass
        bottom_pen    = self.main_view.get_horizontal_feature_region_pen()
        left_pen      = self.main_view.get_vertical_feature_region_pen()
        top_right_pen = self.main_view.get_opposite_feature_region_pen()
        crop_pen      = self.main_view.get_crop_region_pen()
        region_lines  = match_item.get_bound_lines()
        feature_point_pen = self.main_view.get_feature_point_pen()
        (bottom0, bottom1) = region_lines[0]
        (left0  , left1  ) = region_lines[1]
        (top0   , top1   ) = region_lines[2]
        (right0 , right1 ) = region_lines[3]
        self.feature_line_list = \
          [ scene.addLine(bottom0[0], bottom0[1], bottom1[0], bottom1[1], bottom_pen),
            scene.addLine(  left0[0],   left0[1],   left1[0],   left1[1], left_pen),
            scene.addLine(   top0[0],    top0[1],    top1[0],    top1[1], top_right_pen),
            scene.addLine( right0[0],  right0[1],  right1[0],  right1[1], top_right_pen),
          ]
        for (x,y) in match_item.get_match_points():
            self.feature_point_list.append(
                # the ORB algorithm built-in to OpenCV uses FAST-9 for
                # feature points, which are points of a radius of 9
                # pixels, so we draw a circle with a radius of 9
                # centered around the point.
                ORBMatchVisualizer.draw_point(scene, x, y, feature_point_pen),
              )
        if crop_rect_dict is not None:
            for (_label, rect) in crop_rect_dict.items():
                line_list = []
                for (crop0, crop1) in match_item.get_bound_lines(rect):
                    line_list.append(
                        scene.addLine(crop0[0], crop0[1], crop1[0], crop1[1], crop_pen),
                      )
                self.crop_region_line_list_list.append(line_list)
        else:
            pass

    def draw_features(self):
        #print(f'{self.__class__.__name__}.draw_features()')
        app_model = self.main_view.get_app_model()
        matcher = app_model.get_algorithm()
        scene = self.get_reference_scene()
        points = matcher.get_feature_points()
        if points is not None:
            #print(f'ORBMatchVisualizer.draw_features() #(draw {len(points)} points)')
            feature_point_pen = self.main_view.get_feature_point_pen()
            for (x,y) in points:
                self.reference_point_list.append(
                    ORBMatchVisualizer.draw_point(
                        self.get_reference_scene(),
                        x, y, feature_point_pen,
                      ),
                  )
            return self.feature_point_list
        else:
            #print(f'ORBMatchVisualizer.draw_features() #(points = None)')
            return None

#---------------------------------------------------------------------------------------------------

class MessageBox(qt.QWidget):

    def __init__(self, message):
        super().__init__()
        self.layout = qt.QHBoxLayout(self)
        self.message = qt.QLabel(message)
        self.layout.addWidget(self.message)

class FilesTab(FileSetGUI):

    def __init__(self, main_view):
        super(FilesTab, self).__init__(
            main_view,
            fileset=main_view.get_app_model().get_target_fileset(),
            action_label='Search within this image',
          )
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

    def post_init(self):
        pass

    def activation_handler(self, path=None):
        """This is what happens when the return/enter key is pressed on a
        selected file, or when a file is double-clicked."""
        #print(f'{self.__class__.__name__}.activation_handler({path!r})')
        path = path if path is not None else self.current_item_path()
        if path is None:
            self.main_view.error_message('No input files have been selected')
        else:
            app_model = self.main_view.get_app_model()
            results = None
            progress_dialog = None
            try:
                guess_steps = app_model.guess_compute_steps()
                compute_steps = 0 if guess_steps is None else guess_steps
                target = app_model.get_target_image()
                if compute_steps > 1:
                    progress_dialog = self.main_view.show_progress(
                        f'Load image {str(target.get_path())!r}',
                        'Cancel', 0, compute_steps,
                      )
                    progress_dialog.open()
                else:
                    progress_dialog = None
                target.load_image(path)
                if progress_dialog:
                    progress_dialog.update_progress(0, label='Searching image...')
                else:
                    pass
                results = app_model.match_on_file(progress=progress_dialog)
                #print(f'{self.__class__.__name__}.activation_handler({path!r}) #(len(results) = {len(results)})')
                if progress_dialog:
                    progress_dialog.accept()
                else:
                    pass
                if results is not None:
                    if len(results) > 0:
                        self.main_view.update_inspect_tab()
                        self.main_view.show_inspect_tab()
                    else:
                        self.main_view.update_inspect_tab()
                        self.main_view.error_message(
                            "Pattern image could not be not found in this image",
                          )
                else:
                    if progress_dialog is not None:
                        progress_dialog.reject()
                    else:
                        pass
                    self.main_view.show_pattern_tab()
                    self.main_view.error_message(
                        "Please select a pattern image",
                      )
            except ValueError as err:
                if progress_dialog is not None:
                    progress_dialog.reject()
                else:
                    pass
                self.main_view.show_pattern_tab()
                self.main_view.error_message(str(err))
                #traceback.print_exception(err)
            except RuntimeError as err:
                pass

    def use_current_item_as_reference(self):
        path = self.current_item_path()
        #print(f'FilesTab.use_current_item_as_reference() #("{path}")')
        app_model = self.main_view.get_app_model()
        reference = app_model.get_reference_image()
        reference.load_image(path=path)
        self.main_view.update_reference_pixmap()

#---------------------------------------------------------------------------------------------------

class RegionSelectionTool(CropRectTool):
    """This is a version of "CropRectTool" configured to define the
    rectangular regions within "SingleFeatureMultiCrop" model.

    This tool instantiates "SingleFeatureMultiCrop", as does the
    "RMEMatcher" app model, many of the methods of
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

    def __init__(self, main_view, preview_view):
        super().__init__(preview_view.get_scene())
        #rme.SingleFeatureMultiCrop.__init__(self)
        self.main_view = main_view

    def post_init(self):
        self.redraw_all_regions()

    ###############  Methods for redrawing everything  ###############

    def clear_feature_region(self):
        pattern_setup = self.main_view.get_reference_widget()
        pattern_setup.clear_feature_regions()

    def clear_crop_regions(self):
        pattern_setup = self.main_view.get_reference_widget()
        pattern_setup.clear_crop_regions(self)

    def redraw_all_regions(self):
        pattern_setup = self.main_view.get_reference_widget()
        pattern_setup.redraw_all_regions()

    def redraw_crop_regions(self, x_off, y_off):
        pattern_setup = self.main_view.get_reference_widget()
        pattern_setup.redraw_crop_regions(x_off, y_off)

    ###############  Overrides  ###############

    def draw_rect_updated(self, rect):
        """This method receives events from the CropRectTool parent class
        every time a rectangular region is updated by the end user. It
        calls "set_crop_region_selection()" which uses the
        "self.crop_region_selection" state variable to decide which
        rectangular region receives the update."""
        pattern_setup = self.main_view.get_reference_widget()
        region = pattern_setup.get_selected_region_rect()
        #print(f'{self.__class__.__name__}.draw_rect_updated({region.get_label()!r})')
        region.redraw_rect(rect)

    def draw_rect_cleared(self):
        """This method receives events from the CropRectTool parent class
        every time an end user begins drawing a rectangular region,
        and the if there is a currently selected rectangular region,
        it should be deleted so it can be re-drawn. """
        pattern_setup = self.main_view.get_reference_widget()
        region = pattern_setup.get_selected_region_rect()
        #print(f'{self.__class__.__name__}.draw_rect_cleared() #(clear region {region.get_label()!r})')
        if region:
            region.clear_rect()
        else:
            pass

#---------------------------------------------------------------------------------------------------

class PatternPreview(ReferenceImagePreview):

    def __init__(self, main_view):
        super().__init__(main_view)
        self.crop_rect_tool = RegionSelectionTool(main_view, self)
        self.set_mouse_mode(self.crop_rect_tool)
        self.setSizePolicy(
            qt.QSizePolicy(
                qt.QSizePolicy.Expanding,
                qt.QSizePolicy.Expanding,
              ),
          )

    def post_init(self):
        self._draw_feature_layer()
        self.crop_rect_tool.post_init()

    def get_crop_rect_tool(self):
        return self.crop_rect_tool

    def draw_rect(self, qrectf, pen):
        #print(f'{self.__class__.__name__}.draw_rect()')
        scene = self.get_scene()
        scene.addRect(qrectf, pen)

    def _clear_feature_layer(self):
        #print(f'{self.__class__.__name__}._clear_feature_layer()')
        scene = self.get_scene()
        visualizer = self.main_view.get_visualizer()
        if visualizer is not None:
            visualizer.clear_features()
        else:
            pass

    def _draw_feature_layer(self):
        #print(f'{self.__class__.__name__}._draw_feature_layer()')
        app_model = self.main_view.get_app_model()
        visualizer = self.main_view.get_visualizer()
        if visualizer is not None:
            visualizer.draw_features()
        else:
            #print(f'{self.__class__.__name__}._draw_feature_layer() #(ignoring feature layer, no visualizer)')
            pass

    def clear(self):
        #print(f'{self.__class__.__name__}.clear()')
        self.crop_rect_tool.clear()
        self._clear_feature_layer()
        ReferenceImagePreview.clear(self)

    def redraw(self):
        #print(f'{self.__class__.__name__}.redraw()')
        #traceback.print_stack()
        app_model = self.main_view.get_app_model()
        ReferenceImagePreview.redraw(self)
        self._draw_feature_layer()
        self.crop_rect_tool.redraw()

#---------------------------------------------------------------------------------------------------

class ActiveSelectorModel(qcore.QStringListModel):
    """This class exists only to provide a QListView widget with the
    special behavior that the first element in the list cannot be
    removed as it is the feature region. All updates to this model are
    performed by other methods which handle the task of actually
    updating the model, so this model actually is JUST for use by the
    view and does nothing to interact with the real model. """

    ######################  Static members  ########################

    features_title = '#Features'

    def reset_data_with(names):
        list_model = [ActiveSelectorModel.features_title]
        list_model += names
        return list_model

    #########################  Methods  ############################

    def __init__(self, parent_view, names):
        list_model = ActiveSelectorModel.reset_data_with(names)
        super().__init__(list_model)
        self.list_model = list_model
        self.parent_view = parent_view
        self.active_selector_count = 0

    def post_init(self):
        pass

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
            #print(f'{self.__class__.__name__}.data({row}, {role})')
            if row == 0:
                return ActiveSelectorModel.features_title
            elif row < len(self.list_model):
                return self.list_model[row]
            else:
                return None
        else:
            return None

    def setData(self, qi, new_name, role):
        #print(f'{self.__class__.__name__}.setData({qi.row()}, {new_name!r}, {role})')
        if role == qcore.Qt.ItemDataRole.EditRole:
            i = qi.row()
            if (i == 0) or (new_name == ActiveSelectorModel.features_title):
                # Zeroth index is protected, cannot be edited or deleted.
                #print(f'{self.__class__.__name__}.setData({i}, "{new_name}", {role}) #(refuse to edit index {i} = {old_name!r})')
                return False
            elif (i < 0) or (i >= len(self.list_model)):
                # Out-of-bounds index occurs when elements are added
                # to the list.  No need to call parent classes, the
                # action which triggers this will update itself, this
                # function is only called to update the view.
                #print(f'{self.__class__.__name__}.setData({i}, {new_name!r}, {role}) #(append to list model {new_name!r})')
                self.list_model.append(new_name)
                return True
            else:
                # If any other index is given, an edit
                # occurred. Rename the index.
                #print(f'{self.__class__.__name__}.setData({i}, {new_name!r}, {role}) #(change list model index {i} to {new_name!r}')
                old_name = self.list_model[i]
                if old_name == new_name:
                    return True
                elif self.rename_crop_region(old_name, new_name):
                    #print(f'{self.__class__.__name__}.setData({i}, {new_name!r}, {role}) #(successfully renamed {old_name!r} to {new_name!r}')
                    self.list_model[i] = new_name
                    return qcore.QStringListModel.setData(self, qi, new_name, role)
                else:
                    return False
        else:
            #print(f'{self.__class__.__name__}.setData({i}, "{new_name!r}", {role}) #(meaningless role {role})')
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
        """Create a new name with a number when adding a crop region to this
        list."""
        while True:
            self.active_selector_count += 1
            new_name = f'crop_{self.active_selector_count:0>2}'
            if new_name in self.list_model:
                continue
            else:
                return new_name

    def rename_crop_region(self, old_name, new_name):
        #print(f'{self.__class__.__name__}.rename_crop_region({old_name!r}, {new_name!r})')
        if self.parent_view.rename_crop_region(old_name, new_name):
            return True
        else:
            return False

    def new_crop_region(self): #TODO: check if this is even used, remove it if it is
        #print(f'{self.__class__.__name__}.new_crop_region()')
        name = self.new_name_for_crop_region()
        index = len(self.list_model)
        self.list_model.append(name)
        qcore.QStringListModel.insertRows(self, index, 1)
        return (index, name)

    def delete_crop_region(self, qi):
        if qi is not None:
            index = qi.row()
            if index == 0:
                #print(f'{self.__class__.__name__}.delete_crop_region({index}) #(return (0, None))')
                return (0, None)
            else:
                qcore.QStringListModel.removeRow(self, index)
                name = self.list_model[index]
                #print(f'{self.__class__.__name__}.delete_crop_region({index}) #(return ({index}, {name}))')
                del self.list_model[index]
                return (index, name)
        else:
            #print(f'{self.__class__.__name__}.delete_crop_region(None) #(return (-1, None))')
            return (-1, None)


class ActiveSelector(qt.QListView):
    """The list of rectangular regions that are selected from the
    reference image."""

    def __init__(self, main_view, parent_view):
        super().__init__(parent_view)
        self.main_view = main_view
        app_model = self.main_view.get_app_model()
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
        #self.pressed.connect(self.select_region_item)
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

    def currentChanged(self, current, previous):
        #print(f'{self.__class__.__name__}.selectionChanged()')
        qt.QListView.currentChanged(self, current, previous)
        self.select_region_item(current)

    def post_init(self):
        self.active_selector.post_init()

    def error_message(self, message):
        self.parent_view.error_message(message)

    def get_preview_view(self):
        return self.parent_view.get_preview_view()

    def new_crop_region(self):
        #print(f'{self.__class__.__name__}.new_crop_region()')
        (index, name) = self.active_selector.new_crop_region()
        model = self.model()
        qi = model.index(index)
        qt.QAbstractItemView.setCurrentIndex(self, qi)
        qt.QAbstractItemView.edit(self, qi)
        return (index, name)

    def delete_crop_region(self):
        qi = self.currentIndex()
        return self.active_selector.delete_crop_region(qi)

    def rename_crop_region(self, old_name, new_name):
        #print(f'{self.__class__.__name__}.rename_crop_region({old_name!r}, {new_name!r})')
        return self.parent_view.rename_crop_region(old_name, new_name)

    def reset_selector_items(self, crop_regions=None):
        self.active_selector.reset_data(
            list(crop_regions.keys()) if crop_regions is not None else [],
          )

    def select_region_item(self, index):
        #print(f'{self.__class__.__name__}.select_region_item({index.row()})')
        name = self.active_selector.get_index(index.row())
        #print(f'{self.__class__.__name__}.select_region_item({index.row()}) #(selected item {name!r})')
        if name == ActiveSelectorModel.features_title:
            name = None
        else:
            pass
        self.parent_view.set_region_selector(name)


class RegionContainer():
    """This class is a container for a QGraphicsRectItem drawn into the
    pattern setup scene. It is setup so changes made in the scene are
    reflected in the app_model. On instance of this class is created
    for every rectangle (feature rectangle, or crop rectangle) defined
    in the app_model pattern matching configuration. When initialzed,
    nothing is drawn, to the scene. Use 'redraw_rect' to draw to the
    scene. """

    def __init__(self, label, app_model, scene, pen):
        self.label = label
        self.app_model = app_model
        self.scene = scene
        self.pen = pen
        self.graphics_rect = None

    def get_rect(self):
        if self.graphics_rect:
            return  dpk.QGraphicsRectItem_to_tuple(self.graphics_rect)
        else:
            return None

    def get_pen(self):
        return self.pen

    def set_draw_pen(self, pen):
        self.pen = pen
        self.redraw_rect(self.get_rect())

    def get_label(self):
        return self.label

    def set_label(self, label):
        self.label = label

    def clear_rect(self):
        """Remove the graphics item contained within this container, and from
        the scene as well, but not from the app_model. This function
        should be called when redrawing. """
        self.scene.removeItem(self.graphics_rect)
        self.graphics_rect = None

    def redraw_rect(self, rect):
        """Call clear_rect() and also create a new rect using the old pen value."""
        self.clear_rect()
        if rect:
            self.graphics_rect = self.scene.addRect(
                qcore.QRectF(*rect),
                self.pen,
              )
            self.app_model.set_crop_region(self.label, rect)
        else:
            pass

#---------------------------------------------------------------------------------------------------

class PatternSetupTab(qt.QWidget):

    """This tab sets up the reference/pattern argument used by the pattern
    matching algorithm. It contains views for creating, updating, and
    deleting rectangular regions within the pattern image. The state
    of the view in this class are mapped to the feature and crop
    regions in the SingleFeatureMultiCrop configuration used by the
    pattern matching algorithm. The state of the view can also be
    constructed from the feature and crop regions configuration in the
    SingleFeatureMultiCrop class. """

    def __init__(self, main_view):
        screenWidth = qgui.QGuiApplication.primaryScreen().virtualSize().width()
        super().__init__(main_view)
        self.setObjectName("PatternSetupTab")
        self.setAcceptDrops(True)
        self.main_view    = main_view
        self.layout       = qt.QHBoxLayout(self)
        self.preview_view = PatternPreview(main_view)
        self.active_selector = ActiveSelector(main_view, self)
        self.active_selector.clicked.connect(self.selector_clicked_handler)
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
            self.new_selector_item_action,
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
        #----------
        # Stuff related to displaying the crop regions
        self.selected_region_label = ActiveSelectorModel.features_title
        self.feature_region = RegionContainer(
            None,
            self.main_view.get_app_model(),
            self.preview_view.get_scene(),
            self.main_view.get_feature_region_pen(),
          )
        self.crop_regions = {}

    def selector_clicked_handler(self, qi):
        self.active_selector.select_region_item(qi)

    def get_feature_region(self):
        return self.feature_region

    def post_init(self):
        self.preview_view.post_init()
        self.active_selector.post_init()

    def error_message(self, message):
        self.main_view.error_message(message)

    #def set_selected_region_label(self, name):
    #    #print(f'{self.__class__.__name__}.set_selected_region_label({name!r})')
    #    self.selected_region_label = name

    def get_image_display(self):
        return self.preview_view

    def get_preview_view(self):
        return self.preview_view

    def new_selector_item_action(self):
        """The event handler to create a new selector item."""
        #print(f'{self.__class__.__name__}.new_selector_item_action()')
        (index, name) = self.active_selector.new_crop_region()
        app_model = self.main_view.get_app_model()
        if app_model.new_crop_region(name, None):
            scene = self.preview_view.get_scene()
            self.crop_regions[name] = RegionContainer(
                name,
                app_model,
                scene,
                self.main_view.get_crop_region_pen(),
              )
            self.set_region_selection(name)
            return name
        else:
            self.active_selector.reset_selector_items()
            return None

    def rename_crop_region(self, old_name, new_name):
        #print(f'{self.__class__.__name__}.rename_crop_region({old_name!r}, {new_name!r})')
        app_model = self.main_view.get_app_model()
        result = app_model.rename_crop_region(old_name, new_name)
        if not result:
            self.report_duplicate_name(new_name)
            return False
        else:
            container = self.crop_regions[old_name]
            del self.crop_regions[old_name]
            self.crop_regions[new_name] = container
            container.set_label(new_name)
            return True

    def report_duplicate_name(self, name):
        self.main_view.error_message(f'Crop region named {name!r} already exists.')

    def delete_selector_item_action(self):
        """The event handler to delete a selector item."""
        (index, name) = self.active_selector.delete_crop_region()
        app_model = self.main_view.get_app_model()
        if (index == 0) or (not name):
            self.feature_region.clear_rect()
            app_model.delete_crop_region(None)
        else:
            app_model.delete_crop_region(name)
            if name in self.crop_regions:
                container = self.crop_regions[name]
                container.clear_rect()
                del self.crop_regions[name]
            else:
                pass

    def update_reference_pixmap(self):
        self.preview_view.update_reference_pixmap()

    def set_reference_image_path(self, path):
        #print(f'FilesTab.use_current_item_as_pattern() #("{path}")')
        app_model = self.main_view.get_app_model()
        app_model.set_reference_image_path(path)
        self.update_reference_pixmap()

    def open_pattern_file_handler(self):
        app_model = self.main_view.get_app_model()
        target_dir = app_model.get_config().pattern
        urls = qt_modal_image_file_selection(
            self,
            default_dir=target_dir,
            message='Open images in which to search for patterns',
          )
        if len(urls) > 0:
            self.set_reference_image_path(urls[0])
            if len(urls) > 1:
                #print(f'WARNING: multiple files selected as pattern path, using only first one "{urls[0]}"')
                pass
            else:
                pass
        else:
            #print(f'PatternSetupTab.open_pattern_file_handler() #(file selection dialog returned empty list)')
            pass

    #####################  Working with regions  #####################

    def redraw_all_regions(self):
        #print(f'{self.__class__.__name__}.redraw_all_regions()')
        scene = self.preview_view.get_scene()
        app_model = self.main_view.get_app_model()
        feature_region = app_model.get_feature_region()
        pen = self.main_view.get_feature_region_pen()
        if feature_region:
            self.feature_region = RegionContainer(None, app_model, scene, pen)
            self.feature_region.redraw_rect(feature_region)
        else:
            pass
        pen = self.main_view.get_crop_region_pen()
        for name,crop_region in app_model.get_crop_regions().items():
            self.crop_regions[name] = RegionContainer(name, app_model, scene, pen)

    def set_region_selection(self, label):
        #print(f'{self.__class__.__name__}.set_region_selection({label!r})')
        if (not label) or \
          (label == ActiveSelectorModel.features_title) or \
          (label in self.crop_regions):
            self.selected_region_label = label
        else:
            raise ValueError('no such region label exists', label)

    def new_crop_region(self, label, rect):
        """Creates a new crop region."""
        #print(f'{self.__class__.__name__}.new_crop_region({label!r}, {rect!r})')
        #----------------------------------------
        if not label:
            raise ValueError('label is None')
        elif label == ActiveSelectorModel.features_title:
            raise ValueError(f'cannot create label with title "{ActiveSelectorModel.features_title}", reserved name')
        elif label in self.crop_regions:
            # Already exists
            return False
        else:
            app_model = self.main_view.get_app_model()
            scene = self.get_scene()
            pen = self.main_view.get_crop_region_pen()
            region = RegionContainer(label, app_model, scene, pen)
            self.crop_regions[label] = region
            if rect:
                region.redraw_rect(rect)
            else:
                pass
            return True

    def delete_crop_region(self, label):
        """Deletes a crop region, if the crop region already exists."""
        #print(f'{self.__class__.__name__}.new_crop_region({label!r})')
        #----------------------------------------
        if not label:
            raise ValueError('label is None')
        elif label == ActiveSelectorModel.features_title:
            raise ValueError(f'cannot delete label with title "{ActiveSelectorModel.features_title}", reserved name')
        elif label in self.crop_regions:
            app_model = self.main_view.get_app_model()
            del self.crop_regions[label]
            app_model.delete_crop_region(label)
        else:
            raise ValueError(f'cannot delete label, does not exist', label)

    def get_region_selector(self):
        return self.selected_region_label

    def set_region_selector(self, selected_region_label):
        #print(f'{self.__class__.__name__}.set_region_selector({selected_region_label!r})')
        crop_rect_tool = self.preview_view.get_crop_rect_tool()
        if (not selected_region_label) or \
          (selected_region_label == ActiveSelectorModel.features_title):
            crop_rect_tool.set_draw_pen(self.main_view.get_feature_region_pen())
        else:
            crop_rect_tool.set_draw_pen(self.main_view.get_crop_region_pen())
        self.selected_region_label = selected_region_label

    def get_selected_region_rect(self):
        """Returns the rectangle of the region that is currently selected. If
        no crop regions are selected then the feature region is
        returned by default, which itself defaults to the full size of
        the reference image. The only time this function returns None
        is if the reference image is not defined, or if the selection
        was deleted without updating the region_selector. """
        if (not self.selected_region_label) or \
          (self.selected_region_label == ActiveSelectorModel.features_title):
            return self.feature_region
        else:
            if (self.selected_region_label in self.crop_regions):
                return self.crop_regions[self.selected_region_label]
            else:
                self.selected_region_label = None
                return None

#---------------------------------------------------------------------------------------------------

class InspectTabControl(qt.QWidget):
    """The upper control bar for the Inspect tab"""

    def __init__(self, main_view, inspect_tab):
        super().__init__(inspect_tab)
        self.setObjectName('InspectTab controls')
        self.main_view = main_view
        app_model = self.main_view.get_app_model()
        self.inspect_tab = inspect_tab
        self.setSizePolicy(
            qt.QSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Minimum)
          )
        self.layout = qt.QHBoxLayout(self)
        # ---------- setup slider ----------
        self.slider = PercentSlider(
            "Threshold %",
            app_model.get_threshold(),
            inspect_tab.slider_handler,
          )
        # ---------- setup popup-menu ----------
        self.encoding_menu = EncodingMenu('Encoding:', app_model, parent=self)
        # ---------- lay out the widgets ----------
        self.layout.addWidget(self.encoding_menu)
        self.layout.addWidget(self.slider)

    def post_init(self):
        pass


class InspectTab(qt.QWidget):
    """This tab shows an image on which the pattern matching computation
    has been run, and outlines the matched areas of the image with a
    red rectangle."""

    def __init__(self, main_view):
        super().__init__(main_view)
        self.main_view = main_view
        app_model = self.main_view.get_app_model()
        self.distance_map = None
        self.setObjectName("InspectTab")
        # The layout of this widget is a top bar with a threshold slider and a graphics view or
        # message view. The graphics view or message view can be changed depending on whether
        # the target and pattern are both selected.
        self.layout = qt.QVBoxLayout(self)
        self.layout.setObjectName('InspectTab layout')
        self.control_widget = InspectTabControl(main_view, self)
        self.slider = self.control_widget.slider
        self.layout.addWidget(self.control_widget)
        self.message_box = MessageBox("Please select SEARCH target image and PATTERN image.")
        self.layout.addWidget(self.message_box)
        self.image_display = InspectImagePreview(main_view, self)
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

    def post_init(self):
        self.control_widget.post_init()
        self.image_display.post_init()

    def get_image_display(self):
        return self.image_display

    def slider_handler(self, new_value):
        threshold = self.slider.get_percent()
        if threshold is not None:
            app_model = self.main_view.get_app_model()
            regions = app_model.set_threshold(threshold)
            if regions is not None:
                self.image_display.redraw_regions(regions)
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

    def redraw_all_regions(self):
        #print(f'{self.__class__.__name__}.redraw_all_regions()')
        #traceback.print_stack()
        app_model = self.main_view.get_app_model()
        target = app_model.get_target_image()
        path = target.get_path()
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
        #print('------------------------------------------------------------')
        #print(f'{self.__class__.__name__}.save_selected()')
        app_model = self.main_view.get_app_model()
        output_dir = app_model.get_output_dir()
        output_dir = self.modal_prompt_get_directory(str(output_dir))
        try:
            app_model.set_output_dir(PurePath(output_dir))
            app_model.save_selected()
        except IOError as err:
            self.main_view.error_message(str(err))

    def save_selected_all(self):
        #print('------------------------------------------------------------')
        #print(f'{self.__class__.__name__}.save_selected_all()')
        app_model = self.main_view.get_app_model()
        output_dir = app_model.get_cli_config().output_dir
        output_dir = self.modal_prompt_get_directory(str(output_dir))
        app_model.set_output_dir(PurePath(output_dir))
        compute_steps = len(app_model.get_target_fileset())
        progress_dialog = self.main_view.show_progress(
            f'Processing all files...',
            'Cancel', 0, compute_steps,
          )
        app_model.batch_crop_matched_patterns(progress=progress_dialog)
        progress_dialog.accept()

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

class ConfigFileSelector(qt.QWidget):
    """This is a simple widget to choose a JSON file path and use it
    to change all of the configuration settings."""

    def __init__(self, parent):
        super().__init__(parent)
        self.main_view = parent.main_view
        self.app_model = self.main_view.get_app_model()
        self.layout = qt.QHBoxLayout(self)
        self.open_button = qt.QPushButton('Open')
        self.open_button.clicked.connect(self.open_config_action)
        self.save_button = qt.QPushButton('Save')
        self.save_button.clicked.connect(self.save_config_action)
        self.path_input_field = qt.QLineEdit()
        self.layout.addWidget(self.open_button)
        self.layout.addWidget(self.save_button)
        self.layout.addWidget(self.path_input_field)

    qt_file_dialog_filter_string = 'Files (*.cfg *.config *.ini *.json)'

    def get_load_save_directory(self):
        target_dir = self.app_model.get_default_config_file()
        if target_dir is None:
            target_dir = Path(os.getcwd())
        else:
            pass
        if not target_dir.is_dir():
            target_dir = target_dir.parent
        else:
            pass
        return target_dir

    def show_select_file_dialog(self, message, readwrite):
        if len(urls) > 0:
            return Path(urls[0])
        else:
            return None

    def open_config_action(self):
        open_file = self.path_input_field.text()
        if (open_file is None) or (open_file == ''):
            target_dir = self.get_load_save_directory()
            open_file = qt.QFileDialog.getOpenFileName(
                self, 'Choose a configuration file',
                str(target_dir),
                ConfigFileSelector.qt_file_dialog_filter_string,
              )
            open_file = open_file[0]
        else:
            pass
        if (open_file is not None) and (open_file != ''):
            self.app_model.set_default_config_file(open_file)
            self.app_model.configure_from_file()
            self.path_input_field.setText(str(self.app_model.get_default_config_file()))
        else:
            pass

    def save_config_action(self):
        save_file = self.path_input_field.text()
        if (save_file is None) or (save_file == ''):
            target_dir = self.get_load_save_directory()
            save_file = qt.QFileDialog.getSaveFileName(
                self, 'Save a configuration file',
                str(target_dir),
                ConfigFileSelector.qt_file_dialog_filter_string,
              )
            save_file = save_file[0]
        else:
            pass
        if (save_file is not None) and (save_file != ''):
            self.app_model.set_default_config_file(save_file)
            self.app_model.configure_to_file()
            self.path_input_field.setText(str(self.app_model.get_default_config_file()))
        else:
            pass

#---------------------------------------------------------------------------------------------------

class AlgorithmSelector(qt.QTabWidget):
    """This is the final tab, here you can select the pattern matching
    algorithm to be used. Only RME an ORB are supported as of right
    now. The ORB algorithm has many tuning parameters that can be set
    in this tab as well.
    """

    def __init__(self, main_view):
        super().__init__(main_view)
        self.main_view = main_view
        app_model = self.main_view.get_app_model()
        self.orb_config = orb.ORBConfig()
        self.orb_config_undo = []
        self.orb_config_redo = []
        self.notify = qt.QErrorMessage(self)
        ##--------------- The Config File selector ----------------
        self.config_file_selector = ConfigFileSelector(self)
        ##-------------------- The text fields --------------------
        self.rme_checkbox = qt.QCheckBox('Root-Mean Error (RME) ')
        self.orb_config_view = qt.QGroupBox('Oriented Rotated BRIEF (ORB) ')
        self.orb_config_view.setCheckable(True)
        algorithm = app_model.get_algorithm()
        if isinstance(algorithm, rme.RMEMatcher):
            self.set_algorithm_RME()
        elif isinstance(algorithm, orb.ORBMatcher):
            self.set_algorithm_ORB()
        else:
            raise ValueError('unknown matcher algorithm', algorithm)
        #self.orb_config_view = qt.QWidget(self)
        self.nFeatures = qt.QLineEdit(str(self.orb_config.get_nFeatures()))
        self.nFeatures.editingFinished.connect(self.check_nFeatures)
        self.minimum_descriptor_count = qt.QLineEdit(str(self.orb_config.get_minimum_descriptor_count()))
        self.minimum_descriptor_count.editingFinished.connect(self.check_minimum_descriptor_count)
        self.descriptor_threshold = qt.QLineEdit(str(self.orb_config.get_descriptor_threshold()))
        self.descriptor_threshold.editingFinished.connect(self.check_descriptor_threshold)
        self.scaleFactor = qt.QLineEdit(str(self.orb_config.get_scaleFactor()))
        self.scaleFactor.editingFinished.connect(self.check_scaleFactor)
        self.nLevels = qt.QLineEdit(str(self.orb_config.get_nLevels()))
        self.nLevels.editingFinished.connect(self.check_nLevels)
        self.edgeThreshold = qt.QLineEdit(str(self.orb_config.get_edgeThreshold()))
        self.edgeThreshold.editingFinished.connect(self.check_edgeThreshold)
        self.WTA_K = qt.QLineEdit(str(self.orb_config.get_WTA_K()))
        self.WTA_K.editingFinished.connect(self.check_WTA_K)
        self.patchSize = qt.QLineEdit(str(self.orb_config.get_patchSize()))
        self.patchSize.editingFinished.connect(self.check_patchSize)
        self.fastThreshold = qt.QLineEdit(str(self.orb_config.get_fastThreshold()))
        self.fastThreshold.editingFinished.connect(self.check_fastThreshold)
        #self.descriptor_neighbor_count = qt.QLineEdit(str(self.orb_config.get_descriptor_nearest_neigbor_count()))
        #self.descriptor_neighbor_count.editingFinished.connect(self.check_descriptor_neighbor_count)
        ## -------------------- the form layout --------------------
        self.form_layout = qt.QFormLayout(self.orb_config_view)
        self.form_layout.setFieldGrowthPolicy(qt.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form_layout.setLabelAlignment(qcore.Qt.AlignmentFlag.AlignRight)
        self.form_layout.setFormAlignment(qcore.Qt.AlignmentFlag.AlignLeft)
        self.form_layout.addRow('Number of Features (>20, <20000)', self.nFeatures)
        self.form_layout.addRow('Minimum Matching (>4, <N_features/2)', self.minimum_descriptor_count)
        self.form_layout.addRow('Feature Threshold (>0.01, <2.0)', self.descriptor_threshold)
        self.form_layout.addRow('Number of Levels (>1, <64)', self.nLevels)
        self.form_layout.addRow('Scale Factor (>1.0, <2.0)', self.scaleFactor)
        self.form_layout.addRow('Edge Threshold (>2, <1024)', self.edgeThreshold)
        self.form_layout.addRow('Patch Size (>2, <1024)', self.patchSize)
        self.form_layout.addRow('WTA Factor (>2, <4)', self.WTA_K)
        self.form_layout.addRow('FAST Threshold (>2, <100)', self.fastThreshold)
        #self.form_layout.addRow('Number of Neighbor (>2, <5)', self.descriptor_neighbor_count)
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
        self.rme_checkbox.stateChanged.connect(self.rme_checkbox_state_changed)
        self.orb_config_view.toggled.connect(self.orb_config_view_check_state_changed)
        self.whole_layout = qt.QVBoxLayout(self)
        self.whole_layout.addWidget(self.config_file_selector)
        self.whole_layout.addWidget(self.rme_checkbox)
        self.whole_layout.addWidget(self.orb_config_view)
        self.whole_layout.addWidget(self.buttons)
        self.whole_layout.addStretch()

    def post_init(self):
        pass

    def set_algorithm_ORB(self):
        #print(f'{self.__class__.__name__}.set_algorithm_ORB()')
        self.rme_checkbox.setCheckState(qcore.Qt.Unchecked)
        self.orb_config_view.setChecked(True)
        self.main_view.set_algorithm_ORB()

    def set_algorithm_RME(self):
        #print(f'{self.__class__.__name__}.set_algorithm_RME()')
        self.rme_checkbox.setCheckState(qcore.Qt.Checked)
        self.orb_config_view.setChecked(False)
        self.main_view.set_algorithm_RME()

    def orb_config_view_check_state_changed(self, state):
        # This function exists because Qt5 does not allow you to add a
        # QGroupBox to a QButtonGroup.
        if state:
            self.set_algorithm_ORB()
        else:
            self.set_algorithm_RME()

    def rme_checkbox_state_changed(self, state):
        # This function exists because Qt5 does not allow you to add a
        # QGroupBox to a QButtonGroup.
        if state == qcore.Qt.Checked:
            self.set_algorithm_RME()
        else:
            self.set_algorithm_ORB()

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
        except ValueError as err:
            self.notify.showMessage(err.args[0])

    def reset_field(self, field, getter):
        try:
            field.setText(str(getter()))
        except ValueError as err:
            self.notify.showMessage(err.args[0])

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

    def check_descriptor_threshold(self):
        self.update_field(self.descriptor_threshold, float, self.orb_config.set_descriptor_threshold)

    def check_minimum_descriptor_count(self):
        self.update_field(self.minimum_descriptor_count, int, self.orb_config.set_minimum_descriptor_count)

    # def check_descriptor_neighbor_count(self):
    #     self.update_field(self.descriptor_neighbor_count, int, self.orb_config.set_descriptor_nearest_neigbor_count)

    def after_update(self):
        self.redo_button.setEnabled(len(self.orb_config_redo) != 0)
        self.undo_button.setEnabled(len(self.orb_config_undo) != 0)

    def reset_all_fields(self):
        self.reset_field(self.nFeatures, self.orb_config.get_nFeatures)
        self.reset_field(self.scaleFactor, self.orb_config.get_scaleFactor)
        self.reset_field(self.nLevels, self.orb_config.get_nLevels)
        self.reset_field(self.edgeThreshold, self.orb_config.get_edgeThreshold)
        self.reset_field(self.WTA_K, self.orb_config.get_WTA_K)
        self.reset_field(self.patchSize, self.orb_config.get_patchSize)
        self.reset_field(self.fastThreshold, self.orb_config.get_fastThreshold)
        self.reset_field(self.descriptor_threshold, self.orb_config.get_descriptor_threshold)
        self.reset_field(self.minimum_descriptor_count, self.orb_config.get_minimum_descriptor_count)
        #self.reset_field(self.descriptor_neighbor_count, self.orb_config.get_descriptor_nearest_neigbor_count)

    def apply_changes_action(self):
        app_model = self.main_view.get_app_model()
        self.reset_all_fields()
        self.push_do(self.orb_config_undo)
        #print(f'ConfigTab.apply_changes_action({str(self.orb_config)})')
        orb_matcher = app_model.get_orb_matcher()
        if orb_matcher:
            orb_matcher.set_orb_config(self.orb_config)
        else:
            #print(f'{self.__class__.__name__} #(cannot update ORB config)')
            pass
        self.after_update()
        files_setup = self.main_view.get_files_setup()
        files_setup.activation_handler()

    def reset_defaults_action(self):
        #print(f'ConfigTab.reset_defaults_action()')
        self.push_do(self.orb_config_undo)
        self.orb_config = orb.ORBConfig()
        self.reset_all_fields()

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
            pass

    def undo_action(self):
        self.shift_do(self.orb_config_undo, self.orb_config_redo)

    def redo_action(self):
        self.shift_do(self.orb_config_redo, self.orb_config_undo)

#---------------------------------------------------------------------------------------------------

class PatternMatcherView(qt.QTabWidget):
    """The Qt Widget containing the GUI for the whole pattern matching program.
    """

    def __init__(self, app_model, parent_view=None):
        super().__init__(parent_view)
        self.app_model = app_model
        self.visualizer = None
        self.init_pen_colors()
        algorithm = str(app_model.get_cli_config().algorithm).upper()
        if algorithm == 'ORB':
            self.visualizer = ORBMatchVisualizer(self)
        elif algorithm == 'RME':
            self.visualizer = RMEMatchVisualizer(self)
        else:
            raise ValueError(f'unexpected algorithm {str(algorithm)!r}Q')
        #----------------------------------------
        # Setup the GUI
        self.notify = qt.QErrorMessage(self)
        self.setWindowTitle("Image Pattern Matching Kit")
        self.resize(1280, 720)
        self.setTabPosition(qt.QTabWidget.North)
        self.files_tab = FilesTab(self)
        self.files_tab.default_image_display_widget()
        self.pattern_tab = PatternSetupTab(self)
        self.inspect_tab = InspectTab(self)
        self.algorithm_tab = AlgorithmSelector(self)
        self.addTab(self.files_tab, "Input")
        self.addTab(self.pattern_tab, "Pattern")
        self.addTab(self.inspect_tab, "Inspect")
        self.addTab(self.algorithm_tab, "Settings")
        self.currentChanged.connect(self.change_tab_handler)
        self.post_init()

    def init_pen_colors(self):
        self.feature_region_pen = qgui.QPen(qgui.QColor(0, 255, 0, 223))
        self.feature_region_pen.setCosmetic(True)
        self.feature_region_pen.setWidth(3)
        self.crop_region_pen = qgui.QPen(qgui.QColor(255, 0, 0, 223))
        self.crop_region_pen.setCosmetic(True)
        self.crop_region_pen.setWidth(3)
        self.feature_point_pen = qgui.QPen(qgui.QColor(0, 255, 0, 223))
        self.feature_point_pen.setCosmetic(True)
        self.feature_point_pen.setWidth(1)
        self.horizontal_feature_region_pen = qgui.QPen(qgui.QColor(255, 0, 255, 223))
        self.horizontal_feature_region_pen.setCosmetic(True)
        self.horizontal_feature_region_pen.setWidth(3)
        self.vertical_feature_region_pen = qgui.QPen(qgui.QColor(0, 255, 255, 223))
        self.vertical_feature_region_pen.setCosmetic(True)
        self.vertical_feature_region_pen.setWidth(3)
        self.opposite_feature_region_pen = qgui.QPen(qgui.QColor(255, 255, 0, 223))
        self.opposite_feature_region_pen.setCosmetic(True)
        self.opposite_feature_region_pen.setWidth(1)

    def post_init(self):
        self.files_tab.post_init()
        self.pattern_tab.post_init()
        self.inspect_tab.post_init()
        self.algorithm_tab.post_init()
        self.visualizer.draw_features()

    def error_message(self, message):
        self.notify.showMessage(message)

    def get_app_model(self):
        return self.app_model

    def get_reference_widget(self):
        return self.pattern_tab

    def get_inspect_widget(self):
        return self.inspect_tab

    def get_files_setup(self):
        return self.files_tab

    def change_tab_handler(self, index):
        """Does the work of actually changing the GUI display to the "InspectTab".
        """
        super().setCurrentIndex(index)
        self.widget(index).update()

    def show_inspect_tab(self):
        self.setCurrentWidget(self.inspect_tab)

    def show_pattern_tab(self):
        self.setCurrentWidget(self.pattern_tab)

    # def show_distance_map(self):
    #     self.inspect_tab.show_distance_map()

    def update_inspect_tab(self):
        self.inspect_tab.redraw_all_regions()

    def update_reference_pixmap(self):
        self.pattern_tab.update_reference_pixmap()
        self.show_pattern_tab()

    def get_visualizer(self):
        return self.visualizer

    def set_algorithm_RME(self):
        #print(f'{self.__class__.__name__}.set_algorithm_RME()')
        if self.visualizer is not None:
            self.visualizer.clear()
        else:
            pass
        self.visualizer = RMEMatchVisualizer(self)
        self.app_model.set_algorithm('RME')
        self.visualizer.draw_features()

    def set_algorithm_ORB(self):
        #print(f'{self.__class__.__name__}.set_algorithm_ORB()')
        if self.visualizer is not None:
            self.visualizer.clear()
        else:
            pass
        self.visualizer = ORBMatchVisualizer(self)
        self.app_model.set_algorithm('ORB')
        self.visualizer.draw_features()

    def show_progress(self, window_label, cancel_label, min_value, max_value):
        return ProgressDialog(
            window_label,
            cancel_label,
            min_value,
            max_value,
            main_view=self,
          )

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

    def get_horizontal_feature_region_pen(self):
        """When displaying a perspective rectangle, the bottom edge will be of
        this color. """
        return self.horizontal_feature_region_pen

    def set_horizontal_feature_region_pen(self, pen):
        """When displaying a perspective rectangle, the bottom edge will be of
        this color. """
        self.horizontal_feature_region_pen = pen

    def get_vertical_feature_region_pen(self):
        """When displaying a perspective rectangle, the left edge will be of
        this color."""
        return self.vertical_feature_region_pen

    def set_vertical_feature_region_pen(self, pen):
        """When displaying a perspective rectangle, the left edge will be of
        this color."""
        self.vertical_feature_region_pen = pen

    def get_opposite_feature_region_pen(self):
        """When displaying a perspective rectangle, the edges opposite the
        lower edge and left edge will be of this color."""
        return self.opposite_feature_region_pen

    def set_opposite_feature_region_pen(self, pen):
        """When displaying a perspective rectangle, the edges opposite the
        lower edge and left edge will be of this color."""
        self.opposite_feature_region_pen = pen

    def get_crop_region_pen(self):
        return self.crop_region_pen

    def set_crop_region_pen(self, pen):
        if not isinstance(pen, qgui.QPen):
            raise ValueError('received argument that is not a QPen')
        else:
            self.crop_region_pen = pen

    def get_feature_point_pen(self):
        return self.feature_point_pen

    def set_feature_point_pen(self, pen):
        if not isinstance(pen, qgui.QPen):
            raise ValueError('received argument that is not a QPen')
        else:
            self.feature_point_pen = pen
