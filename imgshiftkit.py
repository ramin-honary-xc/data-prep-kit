import argparse
import sys
import traceback
from random import random
from pathlib import Path, PurePath

import cv2 as cv
import numpy as np

####################################################################################################

def create_steps(count, rand_count=None):
    rand_count = rand_count if rand_count else 1
    steps = []
    if (not count) or (count <= 0):
        for _i in range(0,rand_count):
            steps.append(random())
    else:
        for i in range(0,count):
            steps.append(i/count)
    return steps

def shift_image_file(input_path, x_count, y_count, rand_count, verbose=False):
    input_path = Path(input_path)
    if not input_path.exists():
        sys.stderr.write(f'no such file: {input_path!s}\n')
    else:
        pass
    steps = []
    if (not x_count) and (not y_count) and (rand_count > 0):
        for _i in range(0, rand_count):
            steps.append((random(), random(),))
    else:
        steps = \
            [ (x, y) \
                for x in create_steps(x_count, rand_count) \
                for y in create_steps(y_count, rand_count) \
             ]
    output_file_count = 0
    try:
        if verbose:
            sys.stderr.write(
                f'read image file: {input_path!s}\n'
                f'  steps = {steps!r}\n'
              )
        else:
            pass
        input_img = cv.imread(str(input_path))
        shape = input_img.shape
        height = shape[0]
        width = shape[1]
        for (x, y) in steps:
            x_shift = width*x
            y_shift = width*y
            M = np.float32([[1,0, x_shift], [0,1, y_shift]])
            output_img = cv.warpAffine(
                input_img, M, (width,height),
                flags=cv.INTER_LINEAR,
                borderMode=cv.BORDER_WRAP,
              )
            output_path = Path(input_path.parent)
            output_path = output_path.joinpath(
                input_path.stem + \
                f'_{round(x_shift):05}x{round(y_shift):05}' + \
                input_path.suffix \
              )
            if verbose:
                sys.stderr.write(
                    f'overwrite image file: {output_path!s}\n' \
                    if output_path.exists() else \
                    f'write image file: {output_path!s}\n' \
                  )
            else:
                pass
            cv.imwrite(str(output_path), output_img)
            output_file_count += 1
    except Exception as err:
        traceback.print_tb(err.__traceback__)
        sys.stderr.write(f'{err!r}\n')
    return output_file_count

####################################################################################################

def main():
    arper = argparse.ArgumentParser(
        description="""
          Shifts images with wrapping by regular or random intervals.
          """,
        exit_on_error=False,
        epilog="""

          Shift with wrap, that is, to transform an image by moving it
          without changing its size, and the part of the image that
          have gone off of the canvas, for example off to the left,
          are moved to the right-most part of the canvas, parts of the
          image that have gone off the bottom of the canvas are moved
          to the top-most part of the cavnas.

          By default, without any other arguments, each image is
          shifted by a random amount. It is also possible to specify
          shifts at regular intervals, for example 3 equal shifts to
          the right and 2 equal shifts down, which will result in 6
          output images.
        """,
      )

    arper.add_argument(
        '-v', '--verbose',
        dest='verbose',
        action='store_true',
        default=False,
        help="""
            Report every input file read and every output file
            written, along with how each input was transformed.
          """,
      )

    arper.add_argument(
        '-x', '--x-count',
        dest='x_count',
        action='store',
        type=int,
        default=None,
        help="""
            Shift the image left/right at X regular intervals.
          """,
      )

    arper.add_argument(
        '-y', '--y-count',
        dest='y_count',
        action='store',
        type=int,
        default=None,
        help="""
            Shift the image up/down at Y regular intervals.
          """,
      )

    arper.add_argument(
        '-R', '--rand-count',
        dest='rand_count',
        action='store',
        type=int,
        default=None,
        help="""
            Perform a random shift on each input image N times. If
            this argument is specified while one or both of of the -x
            or -y arguments are not specified, it can randomized the
            unspecified arguments. For example if you specify -n 3 -x 4
            (with -y unspecified), then 4 regular left/right (x) shifts
            are performed while 3 random up/down (y) shifts are
            performed. If both -x and -y are unspecified, -n will
            generate exactly N ouput images each shifted by a
            different random left/right and a random up/down amount.
        """,
      )

    (config, remaining_argv) = arper.parse_known_args()

    x_count = config.x_count
    y_count = config.y_count
    rand_count = config.rand_count
    verbose = config.verbose

    output_file_count = 0
    for file_path in remaining_argv:
        if verbose:
            sys.stderr.write(f'process argument: {file_path!r}\n')
        else:
            pass
        output_file_count += \
            shift_image_file(file_path, x_count, y_count, rand_count, verbose=verbose)

    if verbose:
        print(f'Done, wrote {output_file_count} files.')
    else:
        pass

    if output_file_count <= 0:
        sys.exit(1)
    else:
        sys.exit(0)
    
####################################################################################################

if __name__ == "__main__":
    main()
