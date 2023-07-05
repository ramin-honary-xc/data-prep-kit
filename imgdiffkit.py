#! /usr/bin/env python3

import DataPrepKit.ImageDiffGUI as gui
from DataPrepKit.ImageDiff import ImageDiff

import sys

import PyQt5.QtWidgets as qt

####################################################################################################

def main():
    app_model = ImageDiff()
    app = qt.QApplication(sys.argv)
    app_window = gui.ImageDiffGUI(app_model)
    app_window.show()
    sys.exit(app.exec_())

####################################################################################################

if __name__ == '__main__':
    main()
