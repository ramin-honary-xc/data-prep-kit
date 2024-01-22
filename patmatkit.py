#! /usr/bin/env python3

import DataPrepKit.utilities as util
import DataPrepKit.RMEMatcher as rme
from DataPrepKit.SingleFeatureMultiCrop import SingleFeatureMultiCrop, algorithm_name
import DataPrepKit.PatternMatcherGUI as gui
from DataPrepKit.FileSet import image_file_suffix_set, image_file_format_suffix

import argparse
import sys
from pathlib import PurePath, Path

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
        '-v', '--verbose',
        dest='verbose',
        action='store_true',
        default=False,
        help="""
          Reports number of matching regions per input image,
          reports each file that is created.
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
        '-A', '--algorithm',
        dest='algorithm',
        action='store',
        default="ORB",
        type=algorithm_name,
        help="""
            Choose the matching algorithm: MSE or ORB. MSE, "Mean
            Squared Error", treats the reference image as a
            convolution kernel and applies the mean square error
            between it and the input image, selects with a single
            threshold (simple effective, but does not work on rotated
            items).  ORB, "Oriented-FAST Rotated BRIEF", selects
            matches by comparing clusters of feature points (works
            regardless of scaling or rotation, but might be harder to
            get good results).
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
        '-t', '--threshold',
        dest='threshold',
        action='store',
        default='92',
        type=util.threshold,
        help="""
          The minimum percentage of similarity reqiured between a pattern and a
          region of the image in order for the region to be selected and cropped.
          """,
      )

    arper.add_argument(
        '-p', '--pattern',
        dest='pattern',
        action='store',
        default=None,
        type=PurePath,
        help="""
          Specify the file path of the image to be used as the pattern.
          """
      )

    arper.add_argument(
        '-x', '--crop-regions',
        dest='crop_regions_json',
        action='store',
        default=None,
        type=util.crop_region_json,
        help="""
          Without specifying this option, the image file used as the "--pattern"
          argument will specify the pattern to seek in each input image, and
          will also determine how big of an image to crop. However it is
          possible to specify a list of crop regions relative to the pattern
          image using this argument. The argument must be a string of valid
          JSON. The JSON data must be a dictionary of crop regions, where each
          crop region is a list of 4 numbers: X coordinate, Y coordinate, width,
          and height. For example:

          '--crop-regions={"lower-right":[5,5,30,20],"upper-left":[-25,-15,30,20]}'

          This will crop two regions for every matched pattern of each input
          image. In this example, the first crop region is labeled "lower-right"
          which is situated at point x=5,y=5, and has a size of width=30,
          height=20. The second crop region is labeled "upper-left" starts at
          x=-25 (25 pixels to the left of the candidate point) and y=-15
          (15 pixels above the candidate point), and also has a width=30 and
          height=20.

          Region labels are used to create directories for storing cropped
          images, so region labels must contain only characters that can be used
          as names for directories in the filesystem.
          """
      )

    arper.add_argument(
        '-o', '--output-dir',
        dest='output_dir',
        action='store',
        default=PurePath('./matched-images'),
        type=PurePath,
        help="""
          Specify the output directory into which multiple image files can be created.
          """,
      )

    arper.add_argument(
        '--overlap',
        dest='overlap_ok',
        action='store_true',
        default=False,
        help="""
          Candidate matching points within a input that are similar may match the
          pattern image such that the crop region arount one candidate point overlaps
          with the crop region around a nearby candidate point. By default, when
          overlapping crop regions are found, the candidate point with the higher
          similarity value will be used and regions that overlap it will be removed
          as candidates. Using this flag asks all candidates to be used regardless
          of whether they overlap candidates with higher similarity values.
          """
      )

    arper.add_argument(
        '--save-map',
        dest='save_map',
        action='store',
        default=None,
        help="""
          If a filename suffix string is supplied as this argument, the resulting image of
          the pattern matching convolution is saved to a file of the same name as the input
          file with the prefix apended to the filename (but before the file extension).
          """,
      )

    arper.add_argument(
        '--encoding',
        dest='encoding',
        action='store',
        default='png',
        type=image_file_format_suffix,
        help=\
          f'A file extension symbol (without a dot) indicating how to encode\n'
          f'the output image files. The set of valid file encodings and their\n'
          f'symbols is defined by OpenCV, please refer to this documentation:\n'
          f'https://docs.opencv.org/3.4/d4/da8/group__imgcodecs.html#ga288b8b3da0892bd651fce07b3bbd3a56\n'
          f'Encoding symbols accepted as this argument include:\n'
          f'{image_file_suffix_set!r}',
        )

    arper.add_argument(
        '--config',
        dest='config_file_path',
        action='store',
        default=None,
        type=Path,
        help="""
          All of settings, whether specified as CLI arguments, or  set in the GUI, can be saved to a
          configuration  file. Use  this  argument  to specify  the  location  of the  configuration
          file. If it does not  exist, it is created as soon as image  processing begins. If it does
          exist, the file is  used to change the default settings. Settings specified  in the GUI or
          on the CLI as arguments can still override the settings specified in the config file.
          """,
      )

    arper.add_argument(
        '--report',
        dest='report_file_name',
        action='store',
        default='report.json',
        type=str,
        help="""
          Change the name of the report file that is written to the output directory along with all
          image files created, which contains a record of information about the process which
          created the image files.
          """
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

    (cli_config, remaining_argv) = arper.parse_known_args()
    app_model = SingleFeatureMultiCrop(cli_config)
    if cli_config.gui:
        app = qt.QApplication(remaining_argv)
        appWindow = gui.PatternMatcherView(app_model)
        appWindow.show()
        sys.exit(app.exec_())
    else:
        app_model.batch_crop_matched_patterns()

####################################################################################################

if __name__ == "__main__":
    main()
 
