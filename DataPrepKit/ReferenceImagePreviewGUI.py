import DataPrepKit.utilities as util
from DataPrepKit.SimpleImagePreview import SimpleImagePreview
import PyQt5.QtWidgets as qt

from pathlib import PurePath

class ReferenceImagePreview(SimpleImagePreview):
    """A QGraphicsView for displaying a reference image, such as the
    pattern image in the "Pattern Matcher Kit" GUI. It does not
    inherit from InspectImagePreview because it has different behavior
    for displaying the image, and for drag and drop. This class may be
    removed and replaced with a more featureful version of
    InspectImagePreview in the future.

    The 'app_model' given to the constructor of this class MUST
    provide an interface to the following methods:

      - 'set_reference_image_path(Path)' which is called by the
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
        app_model = self.main_view.get_app_model()
        if len(urls) > 0:
            path = urls[0]
            if len(urls) > 1:
                print(f'WARNING: drag dropped more than one file, will use only first: "{path}"')
            else:
                pass
            if isinstance(path, PurePath):
                app_model.set_reference_image_path(path)
                self.set_filepath(path)
            else:
                print(f'WARNING: ignoring drag dropped non-local-file path: "{path}"')
        else:
            print(f'WARNING: PatternPreview.drop_url_handler() #(received empty list)')

    def drop_text_handler(self, text):
        app_model = self.main_view.get_app_model()
        files = util.split_linebreaks(text)
        if len(files) > 0:
            path = PurePath(files[0])
            if path.exists():
                app_model.set_reference_image_path(path)
        else:
            print(f'WARNING: drag dropped text contains no file paths, ignoring')

    def update_reference_pixmap(self):
        app_model = self.main_view.get_app_model()
        pattern = app_model.get_reference()
        self.set_filepath(pattern.get_path())
