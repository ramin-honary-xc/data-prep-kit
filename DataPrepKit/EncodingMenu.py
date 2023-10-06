import PyQt5.QtWidgets as qt
from DataPrepKit.FileSet import FileSet, image_file_suffix_set

class EncodingMenu(qt.QWidget):
    """Group box showing the popup-down menu where the image encoding can be selected."""

    def __init__(self, title, app_model, parent=None):
        super().__init__(parent=parent)
        self.app_model = app_model
        self.setSizePolicy(
            qt.QSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Minimum)
          )
        self.label = qt.QLabel(title)
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
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.popup_menu)
        self.layout.setSizeConstraint(qt.QLayout.SizeConstraint.SetFixedSize)
        self.setLayout(self.layout)

    def menu_item_selected(self, action):
        print(f'InspectTabControl.menu_item_selected("{action.text()}")')
        self.app_model.set_file_encoding(action.text())
        self.popup_menu.setText(action.text())
