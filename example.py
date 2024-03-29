import cv2 as cv
from pathlib import Path
import DataPrepKit.ORBMatcher as orb
from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader
from DataPrepKit.SingleFeatureMultiCrop import SingleFeatureMultiCrop

usage = """
  Modify these variables to point to the two input images: the path to
  the reference image, which is searched for in the target image, and
  the path to the target image. Also provide a directory to which
  resulting matches can be saved.
  """
chips_image_path = Path('/home/ramin/datasets/crop-tool-testing/chips/chips-black-bg.png')
chips_ref_path   = Path('/home/ramin/datasets/crop-tool-testing/chips/chips-pattern.png')
output_dir_path  = Path('/home/ramin/Desktop/results')

#---------------------------------------------------------------------------------------------------

def check_paths():
    """Check that the input images exist."""
    return \
        chips_image_path.exists() and \
        chips_ref_path.exists() 

#---------------------------------------------------------------------------------------------------

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

#dice_image()

#---------------------------------------------------------------------------------------------------

def write_segments():
    ref  = orb.ImageWithORB(CachedCVImageLoader(chips_ref_path))
    targ = CachedCVImageLoader(chips_image_path)
    targ.load_image()
    seg  = orb.SegmentedImage(targ.get_image(), ref.get_crop_rect())
    matching_points = seg.find_matching_points(ref)
    print(f'found {len(matching_points)} matching points')
    for fproj in matching_points:
        print(f'--------------- {fproj.get_rect()} ---------------')
        for line in fproj.get_bound_lines():
            print(f'  {line}')

def main():
    M = SingleFeatureMultiCrop()
    M.set_algorithm('ORB')
    M.set_target_image(chips_image_path)
    M.set_reference_image(chips_ref_path)
    return M

#---------------------------------------------------------------------------------------------------

if __name__ == 'main':
    if check_paths():
        main()
    else:
        print(usage)
else:
    pass
