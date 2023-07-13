#! /usr/bin/env python3

import DataPrepKit.utilities as util
import DataPrepKit.PatternMatcher as patm
import DataPrepKit.PatternMatcherGUI as gui

import argparse
import sys
from pathlib import PurePath

import PyQt5.QtWidgets as qt

####################################################################################################
# The main function, and functions for searching the filesystem for program input

def main():
    arper = argparse.ArgumentParser(
        description="""
          Does "pattern matching" -- finding instances of a smaller image in a larger image.
          """,
        exit_on_error=False,
        epilog="""
          This program will search for a pattern image in each input image, regions found
          to be close to 100% similar within a certain specified threshold value will
          be cropped and saved as a separate image file in a specified output directory.

          The --gui option enables GUI mode (disabled by default), where you can view
          each image and the bounding boxes for each region that matches a pattern. If
          you do not enable GUI mode, this program operates in "batch mode", creating the
          output directory and images without user intervention.
          """,
      )

    arper.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="""
          Reports number of matching regions per input image,
          reports each file that is created.
          """,
      )

    arper.add_argument(
        "--gui",
        dest="gui",
        action="store_true",
        default=False,
        help="""
          Inlcude this arugment to launch the GUI utility.
          """,
      )

    arper.add_argument( \
        "--no-gui", \
        dest="gui", \
        action="store_false", \
        help="""
          Program runs in "batch mode," without presenting a GUI or requesting user feedback.
          """ \
      )

    arper.add_argument( \
        "-t", "--threshold", \
        dest="threshold", \
        action="store", \
        default="95", \
        type=util.threshold, \
        help="""
          The minimum percentage of similarity reqiured between a pattern and a
          region of the image in order for the region to be selected and cropped.
          """,
      )

    arper.add_argument( \
        "-p", "--pattern", \
        dest="pattern", \
        action="store", \
        default=None, \
        type=PurePath, \
        help="""
          Specify the file path of the image to be used as the pattern.
          """ \
      )

    arper.add_argument( \
        "-o", "--output-dir", \
        dest="output_dir", \
        action="store", \
        default=PurePath("./matched-images"), \
        type=PurePath, \
        help="""
          Specify the output directory into which multiple image files can be created.
          """,
      )

    arper.add_argument( \
        "--save-map", \
        dest="save_map", \
        action="store", \
        default=None, \
        help="""
          If a filename suffix string is supplied as this argument, the resulting image of
          the pattern matching convolution is saved to a file of the same name as the input
          file with the prefix apended to the filename (but before the file extension).
          """ \
      )

    arper.add_argument( \
        "inputs", \
        nargs="*", \
        action="store", \
        type=PurePath, \
        help="""
          A set of images, or directories containing images, in which the pattern image is searched.
          Directories are searched for images, but not recursively. See the --recursive option.
          """ \
      )

    (config, remaining_argv) = arper.parse_known_args()
    matcher = patm.PatternMatcher(config)
    #print(config)
    if config.gui:
        app = qt.QApplication(remaining_argv)
        appWindow = gui.PatternMatcherView(matcher)
        appWindow.show()
        sys.exit(app.exec_())
    else:
        if config.pattern is None or \
          (len(config.inputs) == 0):
            arper.print_usage()
        else:
            matcher.batch_crop_matched_patterns()

####################################################################################################

if __name__ == "__main__":
    main()
