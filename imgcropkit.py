#! /usr/bin/env python3

import DataPrepKit.ImageCropperGUI as gui

import sys

import PyQt5.QtWidgets as qt

####################################################################################################

def main():
    app = qt.QApplication(sys.argv)
    app_window = gui.ImageCropKit()
    app_window.show()
    sys.exit(app.exec_())

####################################################################################################

if __name__ == '__main__':
    main()
