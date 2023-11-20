import cv2 as cv
import numpy as np
import math
from pathlib import Path
import DataPrepKit.ORBMatcher as orb
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader

chips_image_path = Path('/home/ramin/datasets/crop-tool-testing/chips/chips-black-bg.png')
chip_ref_path    = Path('/home/ramin/datasets/crop-tool-testing/chips/chips-pattern.png')
output_dir_path  = Path('/home/ramin/Desktop/results')

def dice_image(imgpath, outdirpath):
    imgpath = str(imgpath)
    image = cv.imread(imgpath)
    squares = orb.SegmentedImage(image, (0, 0, image.shape[1], image.shape[0]))
    outdirpath.mkdir(parents=True, exist_ok=True)
    i = 0
    for ((x,y,_w,_h), seg) in squares.foreach():
        i += 1
        filename = outdirpath / Path(f'{x:05}x{y:05}.png')
        print(str(filename))
        cv.imwrite(str(filename), seg)

#dice_image(
#    chips_image_path,
#    output_dir_path
#  )

#---------------------------------------------------------------------------------------------------

def main():
    ref  = orb.ImageWithORB(CachedCVImageLoader(chip_ref_path))
    targ = CachedCVImageLoader(chips_image_path)
    targ.load_image()
    seg  = orb.SegmentedImage(targ.get_image(), ref.get_crop_rect())
    matching_points = seg.find_matching_points(ref)
    print(f'found {len(matching_points)} matching points')
    for fproj in matching_points:
        print(f'--------------- {fproj.get_rect()} ---------------')
        for line in fproj.get_bound_lines():
            print(f'  {line}')

main()
