#! /usr/bin/env python3

import DataPrepKit.utilities as util
from DataPrepKit.BatchResizeView import BatchResizeView
from DataPrepKit.BatchResize import BatchResize
from DataPrepKit.FileSet import image_file_suffix_set
from cv2 import INTER_LANCZOS4

import argparse
import sys
from pathlib import PurePath

import PyQt5.QtWidgets as qt

####################################################################################################
# The main function, and functions for searching the filesystem for program input

def main():
    arper = argparse.ArgumentParser(
        description="""
          Apply scaling transformation (resize) of a list of images,
          optionally by using a GUI.
          """,
        exit_on_error=False,
        epilog="""
          Simply specify desired width and height. You can also specify an
          interpolation method. Specify the outpu directory, and then the
          list of input files as arguments to this program. The GUI allows
          you to visualize each results before generating output.
          """,
      )

    arper.add_argument(
        '-x', '--width',
        dest='width',
        action='store',
        type=int,
        help="""
          The result width of the image, whatever input is given,
          it will be made to fit this exact width.
          """
      )

    arper.add_argument(
        '-y', '--height',
        dest='height',
        action='store',
        type=int,
        help="""
          The result height of the image, whatever input is given,
          it will be made to fit this exact height.
          """
      )

    arper.add_argument(
        '-v', '--verbose',
        dest='verbose',
        action='store_true',
        default=False,
        help="""
          Reports each image output as it is created.
          """,
      )

    arper.add_argument(
        '--gui',
        dest='gui',
        action='store_true',
        default=False,
        help="""
          Inlcude this arugment to launch the GUI utility.
          """,
      )

    arper.add_argument(
        '--no-gui',
        dest='gui',
        action='store_false',
        help="""
          Program runs in "batch mode," without presenting a GUI or requesting user feedback.
          """
      )

    arper.add_argument(
        '-o', '--output-dir',
        dest='output_dir',
        action='store',
        default=PurePath('./resized-images'),
        type=PurePath,
        help="""
          Specify the output directory into which multiple image files can be created.
          """,
      )

    arper.add_argument(
        '-n', '--interpolation',
        dest='interpolate',
        action='store',
        default=INTER_LANCZOS4,
        type=util.interpolation_from_string,
        help=
          f'Specifies the scaling interpolation method to be used. See the OpenCV'
          f'documentation for more about the algorithms corresponding to each of'
          f'these choices:'
          f'https://docs.opencv.org/3.4/da/d54/group__imgproc__transform.html#ga5bb5a1fea74ea38e1a5445ca803ff121'
          f'Valid options for this argument include: {util.interpolation_set!r}'
          f'Defaults to "util.interpolation_default_symbol".'
      )

    arper.add_argument(
        '--encoding',
        dest='encoding',
        action='store',
        default='png',
        help=\
          f'A file extension symbol (without a dot) indicating how to encode\n'
          f'the output image files. The set of valid file encodings and their\n'
          f'symbols is defined by OpenCV, please refer to this documentation:\n'
          f'https://docs.opencv.org/3.4/d4/da8/group__imgcodecs.html#ga288b8b3da0892bd651fce07b3bbd3a56\n'
          f'Encoding symbols accepted as this argument include:\n'
          f'{image_file_suffix_set!r}',
        )

    arper.add_argument(
        'inputs',
        nargs='*',
        action='store',
        type=PurePath,
        help="""
          A set of images, or directories containing images, in which the pattern image is searched.
          Directories are searched for images, but not recursively. See the --recursive option.
          """,
      )

    (config, remaining_argv) = arper.parse_known_args()
    resizer = BatchResize(config)
    if config.gui:
        app = qt.QApplication(remaining_argv)
        appWindow = BatchResizeView(resizer)
        appWindow.show()
        sys.exit(app.exec_())
    else:
        resizer.batch_resize_images()

####################################################################################################

if __name__ == "__main__":
    main()
