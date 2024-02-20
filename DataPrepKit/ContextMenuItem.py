import PyQt5.QtWidgets as qt

def context_menu_item(label, action, shortcut=None):
    """A simplified constructor for a QAction item."""
    menu_item = qt.QAction(label)
    menu_item.triggered.connect(action)
    if shortcut is not None:
        menu_item.setShortcut(shortcut)
    else:
        pass
    return menu_item
