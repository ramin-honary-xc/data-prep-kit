import re
import numpy as np
import json
import cv2 as cv

####################################################################################################
# Operating on data structures

def dict_keep_defined(d):
    """filter out any keys in the dictionary that are None, return a new dictionary."""
    return \
      {k:v for k,v in d.items() if v is not None} \
        if d is not None else {}


####################################################################################################

interpolation_dict = {
    'nearest': cv.INTER_NEAREST,
    'linear': cv.INTER_LINEAR,
    'cubic': cv.INTER_CUBIC,
    'area': cv.INTER_AREA,
    'lanczos4': cv.INTER_LANCZOS4,
    'nearest-exact': cv.INTER_NEAREST_EXACT,
    'linear-exact': cv.INTER_LINEAR_EXACT,
    'max': cv.INTER_MAX,
  }

interpolation_set = set(interpolation_dict.keys())
interpolation_default_symbol = 'linear'

def interpolation_from_string(s):
    if s in interpolation_dict:
        return interpolation_dict[s]
    else:
        raise ValueError('invalid interpolation method symbol {s!r}')


####################################################################################################
# Parsing command line arguments

def width_height_from_string(s):
    args = re.split('[Xx,]', s)
    if len(args) == 2:
        return (args[0], args[1])
    else:
        raise ValueError('invalid width,height specification {s!r}')

def threshold(val):
    val = float(val)
    if val >= 0.0 and val <= 100.0:
        return (float(val) / 100.0)
    else:
        raise ValueError("threshold must be percentage value between 0 and 100")

def crop_region_json(json_string):
    """Parse a JSON string from the command line into a dictionary of
    4-tuple crop regions."""
    crop_regions = json.loads(json_string)
    if not isinstance(crop_regions, dict):
        raise ArgumentError('"--crop-regions" argument must be a JSON dictionary')
    else:
        for label, region in crop_regions.items():
            if not isinstance(region, list):
                raise ArgumentError(
                    '"--crop-regions" argument, {label!r}, expected list, got {type(region)}',
                    (label, region),
                  )
            elif len(region) != 4:
                raise ArgumentError(
                    f'"--crop-regions" argument, {label!r} expected length 4, got length {len(region)}',
                    (label, region),
                  )
            else:
                for i,n in zip(range(0,4), region):
                    if not (isinstance(n, int) or isinstance(n, float)):
                        raise ArgumentError(
                            '"--crop-regions" argument, {label!r}[{i}] expected number, got {type(n)}',
                            (label, region),
                          )
                    else:
                        crop_regions[label] = (
                            region[0],
                            region[1],
                            region[2],
                            region[3],
                          )
    return crop_regions

####################################################################################################
# Miscelaneous utilities (that ought to already exist somewhere else, but do not).

__linebreaker = re.compile(r'[\n\r]')

def get_linebreaker():
    return __linebreaker

def split_linebreaks(str):
    return __linebreaker.split(str)

def float_to_uint32(input_image):
    height, width = input_image.shape
    output_image = np.empty((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            output_image[y,x] = round(input_image[y,x] * 255)
    return output_image

def flatten_list(input):
    result = []
    for x in input:
        if isinstance(x, list):
            result.extend(x)
        else:
            result.append(x)
    input.clear()
    input.extend(result)
    return input

def numpy_map_colors(gray_image, color_map):
    """Construct a color RGB image from a gray image."""
    if not isinstance(gray_image, np.ndarray) or \
      (gray_image.dtype != np.uint8) or \
      (len(gray_image.shape) != 2):
        raise ValueError(
            f'first argument must be np.ndarray of dtype uint8',
          )
    elif not isinstance(color_map, np.ndarray) or \
      (color_map.dtype != np.uint8) or \
      (color_map.shape != (256,3)):
        raise ValueError(
            f'second argument must be a color map, i.e. np.ndarray of dtype uint8 and of shape (256,3)',
          )
    else:
        (h, w) = gray_image.shape
        mapped = np.empty((h, w, 3), dtype=np.uint8)
        for y in range(0,h):
            for x in range(0,w):
                mapped[y,x] = color_map[gray_image[y,x]]
        return mapped

#---------------------------------------------------------------------------------------------------

def rect_to_lines_matrix(rect):
    """Transform a rectangle encoded as a tuple(x,y,width,height) into a
    matrix of float32 2D points, each encoded as a np.float32 array.
    This function function creates lines that point away from the
    origin if they touch the origin, or points away from the point
    opposite diagonally from the origin. See also the
    rect_to_lines_rh() which creates lines following the right-hand
    rule. """
    (x0, y0, width, height) = rect
    x1 = x0 + width
    y1 = y0 + height
    return np.float32(
        [[x0, y0], [x1, y0],
         [x0, y0], [x0, y1],
         [x1, y1], [x0, y1],
         [x1, y1], [x1, y0]],
      )

def rect_to_lines_matrix_rh(rect):
    """Transform a rectangle encoded as a tuple(x,y,width,height) into a
    matrix of float32 2D points, each encoded as a np.float32 array.
    This function creates lines that follow the right-hand rule,
    starting from the origin the head of each line points to the tail
    of the next line, and the lines point in a way that rotates around
    the midpoint of the rectangle following the right-hand rule. """
    (x0, y0, width, height) = rect
    x1 = x0 + width
    y1 = y0 + height
    return np.float32(
        [[x0, y0], [x1, y0,],
         [x1, y0], [x1, y1,],
         [x1, y1], [x0, y1,],
         [x0, y1], [x0, y0,]],
      )

def lines_matrix_to_tuples(lines_matrix):
    i = 0
    result = []
    while (i < lines_matrix.shape[0]):
        a = (lines_matrix[i,0], lines_matrix[i,1],)
        i += 1
        b = (lines_matrix[i,0], lines_matrix[i,1],)
        i += 1
        result.append( (a,b,) )
    return result

def round_point2d(point):
    return (round(point[0]), round(point[1]),)
    
def translate_point2d(matrix, point):
    (x,y) = point
    tpoint = cv.perspectiveTransform(np.float32([x, y, 0]), matrix)
    return (tpoint[0], tpoint[1],)

def round_line2d(line):
    return (
        round_point2d(line[0]),
        round_point2d(line[1]),
      )

def translate_line2d(matrix, line):
    return (
        translate_point2d(matrix, line[0]),
        translate_point2d(matrix, line[1]),
      )
