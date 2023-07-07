import DataPrepKit.utilities as util
from DataPrepKit.SimpleImagePreview import SimpleImagePreview

from pathlib import PurePath

class ReferenceImagePreview(SimpleImagePreview):
    """A QGraphicsView for displaying a reference image, such as the
    pattern image in the "Pattern Matcher Kit" GUI. It does not
    inherit from InspectImagePreview because it has different behavior
    for displaying the image, and for drag and drop. This class may be
    removed and replaced with a more featureful version of
    InspectImagePreview in the future.

    The 'app_model' given to the constructor of this class MUST
    contain a method called 'set_reference_image_path()' which is
    called by the drag-drop event handlers.
    """

    def __init__(self, app_model, main_view):
        super().__init__()
        self.app_model = app_model
        self.main_view = main_view
        self.enable_drop_handlers(True)

    def drop_url_handler(self, urls):
        if len(urls) > 0:
            path = urls[0]
            if len(urls) > 1:
                print(f'WARNING: drag dropped more than one file, will use only first: "{path}"')
            else:
                pass
            if isinstance(path, PurePath):
                self.app_model.set_reference_image_path(path)
                self.set_filepath(path)
            else:
                print(f'WARNING: ignoring drag dropped non-local-file path: "{path}"')
        else:
            print(f'PatternPreview.drop_url_handler() #(received empty list)')

    def drop_text_handler(self, text):
        files = util.split_linebreaks(text)
        if len(files) > 0:
            path = PurePath(files[0])
            if path.exists():
                self.app_model.set_reference_image_path(path)
        else:
            print(f'WARNING: drag dropped text contains no file paths, ignoring')

    def update_pattern_pixmap(self):
        pattern = self.app_model.get_pattern()
        self.set_filepath(pattern.get_path())

