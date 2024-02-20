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

def check_rect_config(r, err_msg):
    if (isinstance(r, list) or isinstance(r, tuple)) and len(r) == 4:
        for e in r:
            if isinstance(e, int) or isinstance(e, float):
                pass
            else:
                raise ValueError(f'{err_msg} region rectangles must be a list of 4 numbers [x,y,width,height]', e, r)
        return (r[0], r[1], r[2], r[3])
    else:
        raise ValueError(f'{err_msg}, dictionary values must be a list of 4 numbers')

def check_region_config(d, err_msg):
    result = dict()
    for k,v in d:
        if isinstance(k, str):
            result[k] = check_rect_config(v, f'{err_msg}, (key={k!r})')
        else:
            raise ValueError(f'{err_msg}, dictionary keys must be strings', k, d)
    return result

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

def check_param(label, param, gte, lte):
    """This function is used mostly when setting arguments taken from the
    GUI. It raises a ValueError if the parameter is out of the bounds
    given by 'gte' and 'lte', the GUI even handler needs to catch this
    and report the error to the user."""
    if gte <= param and param <= lte:
        pass
    else:
        raise ValueError(
            f'Parameter "{label}" must be greater/equal to {gte} and less/equal to {lte}',
            (lte, gte)
          )

def rect_to_list(rect):
    return [rect[0], rect[1], rect[2], rect[3]]

def list_to_rect(rect):
    return (rect[0], rect[1], rect[2], rect[3],)

def crop_region_json(json_string):
    """Parse a JSON string from the command line into a dictionary of
    4-tuple crop regions."""
    crop_regions = json.loads(json_string)
    if not isinstance(crop_regions, dict):
        raise ValueError('"--crop-regions" argument must be a JSON dictionary')
    else:
        for label, region in crop_regions.items():
            if not isinstance(region, list):
                raise ValueError(
                    '"--crop-regions" argument, {label!r}, expected list, got {type(region)}',
                    (label, region),
                  )
            elif len(region) != 4:
                raise ValueError(
                    f'"--crop-regions" argument, {label!r} expected length 4, got length {len(region)}',
                    (label, region),
                  )
            else:
                for i,n in zip(range(0,4), region):
                    if not (isinstance(n, int) or isinstance(n, float)):
                        raise ValueError(
                            '"--crop-regions" argument, {label!r}[{i}] expected number, got {type(n)}',
                            (label, region),
                          )
                    else:
                        crop_regions[label] = list_to_rect(region)
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
            'first argument must be np.ndarray of dtype uint8',
          )
    elif not isinstance(color_map, np.ndarray) or \
      (color_map.dtype != np.uint8) or \
      (color_map.shape != (256,3)):
        raise ValueError(
            'second argument must be a color map, i.e. np.ndarray of dtype uint8 and of shape (256,3)',
          )
    else:
        (h, w) = gray_image.shape
        mapped = np.empty((h, w, 3), dtype=np.uint8)
        for y in range(0,h):
            for x in range(0,w):
                mapped[y,x] = color_map[gray_image[y,x]]
        return mapped

####################################################################################################
# rectangle operations

def bounding_rect(rect_list):
    x_list = []
    y_list = []
    for (x,y,width,height) in rect_list:
        x_list.append(x)
        x_list.append(x+width)
        y_list.append(y)
        y_list.append(y+height)
    x = min(x_list)
    y = min(y_list)
    return (x, y, max(x_list) - x, max(y_list) - y)

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

def rect_to_spline_matrix(rect):
    """Similar to 'rect_to_lines_matrix()' but only returns four lines
    from head to tail."""
    (x0, y0, width, height) = rect
    x1 = x0 + width
    y1 = y0 + height
    return np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])

def spline_matrix4x2_to_lines(p):
    """Convert a matrix constructed by 'rect_to_spline_matrix()' (which
    assumes a 4x2 matrix) into a list of line segments, each segment
    being of the form ((x0, y0), (x1, y1)). This function returns the
    first two segments adjacent to the origin vertex and the last two
    segments adjacent to the vertex opposite the origin.
    """
    p = np.int32(p)
    return \
        [ ((p[0,0], p[0,1],), (p[1,0], p[1,1],),),
          ((p[0,0], p[0,1],), (p[3,0], p[3,1],),),
          ((p[1,0], p[1,1],), (p[2,0], p[2,1],),),
          ((p[3,0], p[3,1],), (p[2,0], p[2,1],),),
        ]

def spline_matrix_to_lines_rh(p):
    """Convert an Nx2 matrix (for example, a matrix constructed by
    'rect_to_spline_matrix()') into a list of line segments, each
    segment being of the form ((x0, y0), (x1, y1)). This function
    returns a list of segments from head to tail going around each
    vertex in 'p'. In the case of rectangles, this constructs line
    segments traveling between vertices following the right-hand rule.
    """
    p = np.int32(p)
    n = p.shape[0]
    segments = list(range(0,n))
    for i0 in segments:
        i1 = (i0 + 1) % n
        segments[i0] = ((p[i0,0], p[i0,1],), (p[i1,0], p[i1,1],),)
    return segments

def rect_transform_rebound(rect, matrix):
    """Given a rectangle 'rect' and a transformation matrix 'M', convert
    transform the vertex points of the rectangle by the matrix and
    then find a new bounding rect around those points. This is useful
    for cropping a larger image to a smaller area of interest prior to
    performing a perspective transform on the image so that the larger
    image does not have to be transformed in its entirety. """
    (x0, y0, width, height) = rect
    x1 = x0 + width
    y1 = y0 + height
    points = np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]).reshape(-1,1,2)
    transformed = cv.perspectiveTransform(points, matrix).reshape(-1,2)
    #print(f'#  transformed:\n{transformed}')
    xs = transformed[:,0:1]
    ys = transformed[:,1:2]
    #print(f'xs = {xs}\nys = {ys}')
    x_min = min(xs)[0]
    x_max = max(xs)[0]
    y_min = min(ys)[0]
    y_max = max(ys)[0]
    #print(f'# return({x_min}, {y_min}, {x_max - x_min}, {y_max - y_min})')
    return (transformed, (x_min, y_min, x_max - x_min, y_max - y_min))

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
    
def translate_point2d(point, matrix):
    (x,y) = point
    transformed = cv.perspectiveTransform(np.float32([x, y, 0]), matrix)
    return (transformed[0], transformed[1],)

def round_line2d(line):
    return (
        round_point2d(line[0]),
        round_point2d(line[1]),
      )

def translate_line2d(line, matrix):
    return (
        translate_point2d(line[0], matrix),
        translate_point2d(line[1], matrix),
      )
