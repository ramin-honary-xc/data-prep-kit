from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader

from copy import deepcopy
import math
import os
from pathlib import (PurePath, Path)

import cv2 as cv

import traceback

####################################################################################################

class ImageWithORB():
    """This class defines a reference image object associated with the key
    points and descriptors computed by the ORB algorithm.
    """

    def __init__(self, image, orb_config=None):
        self.orb_config = ORBConfig() if not orb_config else orb_config
        self.ORB = None
        self.keypoints = None
        self.descriptors = None
        if isinstance(image, PurePath) or isinstance(image, Path):
            self.cached_image = CachedCVImageLoader(image)
            self.cached_image.load_image()
            self.image = self.cached_image.get_image()
        elif isinstance(image, CachedCVImageLoader):
            self.cached_image = image
            self.cached_image.load_image()
            self.image = image.get_image()
        else:
            self.cached_image = None
            self.image = image

    def get_image(self):
        return self.image

    def get_cached_image(self):
        return self.cached_image

    def get_filepath(self):
        return (None if not self.cached_image else self.cached_image.get_path())

    def get_orb_config(self):
        return self.orb_config

    def set_orb_config(self, orb_config):
        #print(f'ImageWithORB.set_orb_config({orb_config})')
        self.orb_config = deepcopy(orb_config)

    def get_ORB(self):
        return self.ORB

    def get_keypoints(self):
        return self.keypoints

    def get_descriptors(self):
        return self.descriptors

    def get_crop_rect(self):
        if self.cached_image:
            return self.cached_image.get_crop_rect()
        else:
            return (0, 0, self.image.shape[1], self.image.shape[0])

    def compute(self):
        #print(f'ImageWithORB.force_run_orb() #(set self.orb_config {str(self.orb_config)})')
        if self.image is not None:
            # Set the init_crop_rect
            height = self.image.shape[0]
            width = self.image.shape[1]
            self.init_crop_rect = (0, 0, width, height)
            # Run the ORB algorithm
            #print(f'ImageWithORB.force_run_orb({str(orb_config)})')
            ORB = cv.ORB_create( \
                nfeatures=self.orb_config.get_nFeatures(), \
                scaleFactor=self.orb_config.get_scaleFactor(), \
                nlevels=self.orb_config.get_nLevels(), \
                edgeThreshold=self.orb_config.get_edgeThreshold(), \
                firstLevel=self.orb_config.get_firstLevel(), \
                WTA_K=self.orb_config.get_WTA_K(), \
                scoreType=self.orb_config.get_scoreType(), \
                patchSize=self.orb_config.get_patchSize(), \
                fastThreshold=self.orb_config.get_fastThreshold(), \
              )
            (keypoints, descriptor) = ORB.detectAndCompute(self.image, None)
            self.ORB = ORB
            self.keypoints = keypoints
            self.descriptor = descriptor
            num_points = len(self.keypoints)
            #print(f'ImageWithORB.force_run_orb() #(generated {num_points} keypoints)')
            x_sum = 0
            y_sum = 0
            for key in self.keypoints:
                (x, y) = key.pt
                x_sum = x_sum + x
                y_sum = y_sum + y
            if num_points > 0:
                self.midpoint = (x_sum / num_points, y_sum / num_points)
            else:
                print(f'ImageWithORB.force_run_orb() #(cannot find center of mass for zero points)')
                self.midpoint = None
        else:
            print(f'ImageWithORB.force_run_orb() #(failed to load pixmap for path {path}')

#---------------------------------------------------------------------------------------------------

class SegmentedImage():
    """This class takes an image and segments it into squares in such a
    way that allows a smaller reference image to be found within each
    segment. The hypotenuse of the given RECT argument is used to
    construct segments, but if the hypotenuse is larger than the width
    or height of the target image, the minimum of the width, height,
    and hypotenuse is chosen as the segment size.
    """

    def __init__(self, nparray2d, rect):
        (_x, _y, seg_width, seg_height) = rect
        shape = nparray2d.shape
        img_height = shape[0]
        img_width  = shape[1]
        if (seg_height > img_height) and (seg_width > img_width):
            raise ValueError(f'bad reference image, both width and height ({seg_width},{seg_height}) are larger than search target image ({img_width},{img_height})', (seg_width, seg_height), (img_width, img_height))
        elif (seg_height > img_height):
            raise ValueError(f'bad reference image, height is larger than search target image', seg_height, img_height)
        elif (seg_width > img_width):
            raise ValueError(f'bad reference image, width is larger than search target image', seg_width, img_width)
        else:
            pass
        hypotenuse = math.ceil(math.sqrt(seg_width*seg_width + seg_height*seg_height))
        self.segment_width = hypotenuse if hypotenuse < img_width else img_width
        self.segment_height = hypotenuse if hypotenuse < img_height else img_height
        self.image = nparray2d
        self.image_width = img_width
        self.image_height = img_height
        #print(f'segment_width = {self.segment_width}')
        #print(f'segment_height = {self.segment_height}')
        #print(f'image_width = {self.image_width}')
        #print(f'image_height = {self.image_height}')
        #print(f'hypotenuse = {hypotenuse}')
        
    def foreach_1D(img, seg):
        top = img - seg
        subseg = round(seg/6)
        num_steps = math.ceil(top / subseg)
        step = top / num_steps
        i = 0.0
        #print(f'---------- img={img}, seg={seg}, halfseg={halfseg}, step={step} top={top} ----------')
        while (i < top):
            i = math.floor(i)
            yield (i, i+seg)
            i += step

    def foreach(self):
        for (y_min,y_max) in SegmentedImage.foreach_1D(self.image_height, self.segment_height):
            for (x_min,x_max) in SegmentedImage.foreach_1D(self.image_width, self.segment_width):
                #print(f'x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max}')
                yield \
                    ( (x_min, y_min, x_max-x_min, y_max-y_min,),
                      self.image[y_min:y_max, x_min:x_max],
                    )

    def find_matching_points(self, ref):
        bounds = ref.get_crop_rect()
        matched_points = []
        for ((x,y,_w,_h), segment) in self.foreach():
            segment_orb = ImageWithORB(segment, ref.get_orb_config())
            segment_orb.compute()
            bruteforce_match = cv.BFMatcher(cv.NORM_HAMMING, crossCheck=True)
            matches = bruteforce_match.match(
                ref.get_descriptors(),
                segment_orb.get_descriptors(),
              )
            best_matches = []
            for m,n in matches:
                if m.distance < 0.7 * n.distance:
                    best_matches.append(m)
                else:
                    pass
            if len(best_matches) < 20:
                print(f'ignore block ({x:05},{y:05}), only {len(best_matches)} best matches')
            else:
                reference_keypoints = ref.get_keypoints()
                target_keypoints = segment_orb.get_keypoints()
                reference_selection = np.float32(
                    [reference_keypoints[m.queryIdx].pt for m in best_matches],
                  )
                reference_selection = reference_selection.reshape(-1,1,2)
                target_selection = np.float32(
                    [target_keypoints[m.trainIdx].pt for m in best_matches],
                  )
                target_selection = target_selection.reshape(-1,1,2)
                (homo_matrix, mask) = cv.findHomography(
                    reference_selection,
                    target_selection,
                    cv.RANSAC,
                    5.0,
                  )
                print(f'block ({x:05},{y:05}) has {len(best_matches)} best matches')
                print(homo_matrix)
                matched_points.append((x,y,bounds,homo_matrix,mask,))
        return matched_points

#---------------------------------------------------------------------------------------------------

def check_param(label, param, gte, lte):
    """This function is used mostly when setting arguments taken from the
    GUI. It raises a ValueError if the parameter is out of the bounds
    given by 'gte' and 'lte', the GUI even handler needs to catch this
    and report the error to the user."""
    if gte <= param and param <= lte:
        pass
    else:
        raise ValueError(
            f'Parameter "{label}" must be greater/equal to {gte} and less/equal to {lte}'
          )

class ORBConfig():
    """This data type contains values used to parameterize the ORB feature
    selection algorithm. It overrides the equality operator so that we
    can detect when the config has changed, and therefore when we need
    to re-run the ORB algorithm.
    """
    def __init__(self):
        self.nFeatures = 1000
        self.scaleFactor = 1.2
        self.nLevels = 8
        self.edgeThreshold = 31
        self.firstLevel = 0
        self.WTA_K = 2
        self.scoreType = 0 # O = HARRIS_SCORE (could also be 1 = FAST_SCORE)
        self.patchSize = 31
        self.fastThreshold = 20

    def __eq__(self, a):
        return (
            (a is not None) and \
            (self.nFeatures == a.nFeatures) and \
            (self.scaleFactor == a.scaleFactor) and \
            (self.nLevels == a.nLevels) and \
            (self.edgeThreshold == a.edgeThreshold) and \
            (self.firstLevel == a.firstLevel) and \
            (self.WTA_K == a.WTA_K) and \
            (self.scoreType == a.scoreType) and \
            (self.patchSize == a.patchSize) and \
            (self.fastThreshold == a.fastThreshold) \
          )

    def to_dict(self):
        return \
          { 'nFeatures': self.nFeatures,
            'scaleFactor': self.scaleFactor,
            'nLevels': self.nLevels,
            'edgeThreshold': self.edgeThreshold,
            'firstLevel': self.firstLevel,
            'WTA_K': self.WTA_K,
            'scoreType': self.scoreType,
            'patchSize': self.patchSize,
            'fastThreshold': self.fastThreshold,
          }

    def __str__(self):
        return str(self.to_dict())

    def get_nFeatures(self):
        return self.nFeatures

    def set_nFeatures(self, nFeatures):
        check_param('number of features', nFeatures, 20, 20000)
        self.nFeatures = nFeatures

    def get_scaleFactor(self):
        return self.scaleFactor

    def set_scaleFactor(self, scaleFactor):
        check_param('scale factor', scaleFactor, 1.0, 2.0)
        self.scaleFactor = scaleFactor

    def get_nLevels(self):
        return self.nLevels

    def set_nLevels(self, nLevels):
        check_param('number of levels', nLevels, 2, 32)
        self.nLevels = nLevels
        if self.firstLevel > nLevels:
            self.firstLevel = nLevels
        else:
            pass

    def get_edgeThreshold(self):
        return self.edgeThreshold

    def set_edgeThreshold(self, edgeThreshold):
        check_param('edge threshold', edgeThreshold, 2, 1024)
        self.edgeThreshold = edgeThreshold

    def get_firstLevel(self):
        return self.firstLevel

    def set_firstLevel(self, firstLevel):
        check_param('first level', firstLevel, 0, self.edgeThreshold)
        self.firstLevel = firstLevel

    def get_WTA_K(self):
        return self.WTA_K

    def set_WTA_K(self, WTA_K):
        check_param('"WTA" factor', WTA_K, 2, 4)
        self.WTA_K = WTA_K

    def get_scoreType(self):
        return self.scoreType

    def set_scoreType(self, scoreType):
        self.scoreType = scoreType

    def get_patchSize(self):
        return self.patchSize

    def set_patchSize(self, patchSize):
        check_param("patch size", patchSize, 2, 1024)
        self.patchSize = patchSize

    def get_fastThreshold(self):
        return self.fastThreshold

    def set_fastThreshold(self, fastThreshold):
        check_param('"FAST" threshold', fastThreshold, 2, 100)
        self.fastThreshold = fastThreshold

#---------------------------------------------------------------------------------------------------

class ORBMatcher():
    """This class creates objects that represents the state of the whole
    application.
    """

    def __init__(self, app_model, orb_config=None):
        self.app_model = app_model
        self.orb_config = ORBConfig()
        self.reference_image = None
        self.target_image = None

    def get_orb_config(self):
        return self.orb_config

    def set_orb_config(self, orb_config):
        #print(f'ORBMatcher.set_orb_config({orb_config})')
        if (orb_config is not None) and (not isinstance(orb_config, ORBConfig)):
            raise ValueError(
                f'MainAppMode.set_orb_config() called with value of type {str(type(orb_config))}',
                orb_config,
              )
        elif self.reference_image is not None:
            self.reference_image.set_orb_config(orb_config)
        else:
            pass
        #print(f'ORBMatcher.set_orb_config() #(set self.orb_config = {orb_config})')
        self.orb_config = deepcopy(orb_config)

    def get_reference(self):
        return self.reference_image

    def set_reference(self, image):
        self.reference_image = ImageWithORB(image)
        self.reference_image.compute()

    def get_keypoints(self):
        if self.reference_image is not None:
            return self.reference_image.get_keypoints()
        else:
            return None

    def get_descriptor(self):
        if self.reference_image is None:
            return None
        else:
            return self.reference_image.get_descriptor()

    def match_on_file(self):
        """This function is triggered when you double-click on an item in the image
        list in the "FilesTab". It starts running the pattern matching algorithm
        and changes the display of the GUI over to the "InspectTab".
        """
        if not self.reference_image:
            reference = self.app_model.get_reference()
            if not reference:
                raise ValueError('reference image has not been selected')
            else:
                self.reference_image = ImageWithORB(reference, self.get_orb_config())
                self.reference_image.compute()
        else:
            pass
        self.target_image = self.target.get_target()
        if self.target_image is None:
            print(f'RMEMatcher.match_on_file() #(self.reference.get_image() returned None)')
        else:
            target = self.target_image.get_image()
            segmented_image = SegmentedImage(target, boundds)
            matched_points = segmented_image.find_matching_points(self.reference_image)
            
