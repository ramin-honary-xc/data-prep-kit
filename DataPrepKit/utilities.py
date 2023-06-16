import re

####################################################################################################
# Parsing command line arguments

def threshold(val):
    val = float(val)
    if val >= 0.0 and val <= 100.0:
        return (float(val) / 100.0)
    else:
        raise ValueError("threshold must be percentage value between 0 and 100")

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

