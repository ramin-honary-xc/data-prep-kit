import DataPrepKit.utilities as util
from DataPrepKit.SimpleImagePreview import SimpleImagePreview
import PyQt5.QtWidgets as qt

from pathlib import Path, PurePath

class ReferenceImagePreview(SimpleImagePreview):
    """A QGraphicsView for displaying a reference image, such as the
    pattern image in the "Pattern Matcher Kit" GUI. It does not
    inherit from InspectImagePreview because it has different behavior
    for displaying the image, and for drag and drop. This class may be
    removed and replaced with a more featureful version of
    InspectImagePreview in the future.

    The 'app_model' given to the constructor of this class MUST
    provide an interface to the following methods:

      - 'set_reference_image(Path)' which is called by the
        drag-drop event handlers.

      - 'get_reference()' which is called to update the
        SimpleImagePreview file path.

    """

    def __init__(self, main_view):
        super().__init__()
        self.main_view = main_view
        self.enable_drop_handlers(True)
        self.setSizePolicy(
            qt.QSizePolicy(
                qt.QSizePolicy.Expanding,
                qt.QSizePolicy.Preferred,
              ),
          )
        self.update_reference_pixmap()

    def drop_url_handler(self, urls):
        #app_model = self.main_view.get_app_model()
        if len(urls) > 0:
            path = urls[0]
            if len(urls) > 1:
                print(f'WARNING: drag dropped more than one file, will use only first: "{path}"')
            else:
                pass
            if isinstance(path, PurePath) or isinstance(path, Path):
                self.set_reference_image(path)
            elif isinstance(path, str):
                self.set_reference_image(Path(path))
            else:
                self.report_file_not_found(path)
        else:
            #print(f'WARNING: PatternPreview.drop_url_handler() #(received empty list)')
            pass

    def drop_text_handler(self, text):
        #app_model = self.main_view.get_app_model()
        files = util.split_linebreaks(text)
        if len(files) > 0:
            path = PurePath(files[0])
            if path.exists():
                self.set_reference_image(path)
            else:
                self.report_file_not_found(path)
        else:
            print('WARNING: drag dropped text contains no file paths, ignoring')
            pass

    def report_file_not_found(self, path):
        self.main_view.error_message(f'file not found: {str(path)!r}')

    def update_reference_pixmap(self):
        app_model = self.main_view.get_app_model()
        pattern = app_model.get_reference_image()
        self.set_filepath(pattern.get_path())

    def set_reference_image(self, path):
        #print(f'{self.__class__.__name__}.set_reference_image({path})')
        self.set_filepath(path)
        app_model = self.main_view.get_app_model()
        app_model.set_reference_image(path)
        self.redraw()
