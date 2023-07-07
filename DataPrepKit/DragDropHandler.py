from pathlib import PurePath

import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

class DragDropHandler():
    """This class provides a higher-level wrapper around the Qt drag and
    drop event handlers. This class can be inhereited so it can make
    use of methods that let you easily activate or deactivate QWidiget
    event handlers that can respond to dropping files from some other
    application in the operating system into your GUIs window.

    If you inherit from this class, you MUST also inherit from QWidget
    or a child of QWidget. That is because the "setAcceptsDrops()"
    method is called by the methods in this class.

    There are two methods you should override:

      - 'drop_url_handler(urls)' which takes a list of QUrl objects as
        an argument.

      - 'drop_text_handler(text)' which takes a string as an argument.

    Any class that inherits from this class will be able to enable or
    disable drag and drop, by simply calling the
    'enable_drop_handlers()' method. You can also enable or disable
    each handler individually, however it is best to enable both or
    neither, since the operating system may not recognize file paths
    as URLs and input them to the program as text instead. Your
    program should be ready to handle either situation.
    """

    def __init__(self):
        self._drop_url_handler = False
        self._drop_text_handler = False

    def reset_accepts_drops(self):
        enable = self._drop_text_handler or self._drop_url_handler
        print(f'DragDropHandler.reset_accepts_drops() #( {self}.setAcceptDrops({enable}) )')
        self.setAcceptDrops(enable)

    def drop_url_handler(self, urls):
        """This is the default event handler that does nothing but print a log
        message."""
        print(f'DragDropHandler.drop_url_handler() #(urls: {urls})')

    def drop_text_handler(self, text):
        """This is the default event handler that does nothing but print a log
        message."""
        print(f'DragDropHandler.drop_url_handler() #(text: "{text}")')

    def enable_drop_text_handler(self, boolean):
        self._drop_text_handler = boolean
        self.reset_accept_drops()

    def enable_drop_url_handler(self, boolean):
        self._drop_url_handler = boolean
        self.reset_accept_drops()

    def enable_drop_handlers(self, boolean):
        """Enable both URL and text drop handlers at once. This function
        assumes you have overridden the drop_text_handler() and
        drop_url_handler() methods.

        """
        self._drop_url_handler = boolean
        self._drop_text_handler = boolean
        self.reset_accepts_drops()

    def dragEnterEvent(self, event):
        print(f'DragDropHandler.dragEnterEvent() #(self = {self})')
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if len(urls) > 0:
                return event.accept()
            else:
                print(f'DragDropHandler.dragEnterEvent() #(len(urls) <= 0: ignore)')
                return event.ignore()
        elif mime_data.hasText():
            return event.accept()
        else:
            print(f'DragDropHandler.dragEnterEvent() #(mime_data: hasUrls() -> False, hasText() -> False)')
            return event.ignore()

    def dragMoveEvent(self, event):
        return event.accept()

    def dropEvent(self, event):
        print(f'DragDropHandler.dropEvent() #(self = {self})')
        mime_data = event.mimeData()
        if mime_data.hasUrls() and self._drop_url_handler:
            urls = mime_data.urls()
            urls = list(
                map(( lambda url: \
                      PurePath(url.toLocalFile()) if \
                      url.isLocalFile() else \
                      url
                    ),
                    urls,
                  ),
              )
            print(f'DragDropHandler.dropEvent() #(urls: {urls})')
            return self.drop_url_handler(urls)
        elif mime_data.hasText() and self._drop_text_handler:
            text = mime_data.text()
            print(f'DragDropHandler.dropEvent() #(text: {text})')
            event.accept()
            return self.drop_text_handler(text)
        else:
            print(f'DragDropHandler.dropEvent() #( event.ignore() )')
            return event.ignore()
