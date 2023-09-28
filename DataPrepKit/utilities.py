import re
import numpy as np
import json

####################################################################################################
# Operating on data structures

def dict_keep_defined(d):
    """filter out any keys in the dictionary that are None, return a new dictionary."""
    return \
      {k:v for k,v in d.items() if v is not None} \
        if d is not None else {}


####################################################################################################
# Parsing command line arguments

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
