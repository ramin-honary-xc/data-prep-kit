import DataPrepKit.ApplyPixmapMask as mask

import argparse
from pathlib import Path

def main():
    arper = argparse.ArgumentParser(
        description="""
          Apply a MASK image to every image file found all files
          and/or directories of files listed as arguments.
        """,
        exit_on_error=False,
        epilog="""
          The MASK image format *must* be a 8-bit grayscale image. It
          is assumed all images in the DIRECTORY is have the same
          width/height dimensions.
        """,
      )

    arper.add_argument(
        '-Q', '--quiet',
        dest="quiet",
        action='store_true',
        default=False,
        help="""
            Do *not* report to the CLI log which files are being read,
            which are being written. Error messages are still
            reported.
          """
      )

    arper.add_argument(
        '-m', '--mask',
        required=True,
        dest='mask_image_file',
        action='store',
        type=Path,
        help="""
            The mask file. It is expected that the width/height of the
            mask file must be exactly the same as the width/height for
            every other input image, and for every input file in any
            directory, which are specified as a command line
            argument. The mask file *must* be formatted as an 8-bit
            grayscale image. White pixels allow the associated pixel
            in the input image to show in the output, black pixels set
            the associated pixel in the output image to black pixels.
          """
    )

    arper.add_argument(
        'input_images',
        nargs='*',
        action='store',
        type=Path,
        help="""
          Path to image files, or directories containing image files,
          which are the same size as the MASK image file
          argument. Each file will be read as input, and a new masked
          output file is created with the same filename, but the
          string "masked_" prepended to the filename.
        """
      )

    (cli_config, remaining_argv) = arper.parse_known_args()

    mask.applyAllFiles(
        cli_config.input_images,
        cli_config.mask_image_file,
        verbose=(not cli_config.quiet),
      )

if __name__ == "__main__":
    main()
