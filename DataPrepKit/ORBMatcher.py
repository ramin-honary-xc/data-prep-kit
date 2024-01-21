from DataPrepKit.CachedCVImageLoader import CachedCVImageLoader
from DataPrepKit.AbstractMatcher import AbstractMatcher, AbstractMatchCandidate
import DataPrepKit.utilities as util

from copy import deepcopy
import math
import os
from pathlib import (PurePath, Path)
import statistics

import cv2 as cv
import numpy as np
import numpy.linalg

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
            #print(f'{self.__class__.__name__}.__init__() #({str(image)!r})')
            self.cached_image = CachedCVImageLoader(image)
            self.cached_image.load_image()
            self.image = self.cached_image.get_image()
        elif isinstance(image, CachedCVImageLoader):
            #print(f'{self.__class__.__name__}.__init__() #({str(image.get_path())!r})')
            self.cached_image = image
            self.cached_image.load_image()
            self.image = image.get_image()
        else:
            #print(f'{self.__class__.__name__}.__init__() #(<<raw-image>>)')
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
        #print(f'{self.__class__.__name__}.set_orb_config({orb_config})')
        if self.orb_config == orb_config:
            pass
        else:
            self.orb_config = deepcopy(orb_config)
            self.keypoints = None
            self.descriptors = None

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
        """Check if the ORB computation has been run yet and do nothing if it
        already has, otherwise if not compute it now. """
        #print(f'{self.__class__.__name__}.compute()')
        if (self.image is None):
            raise ValueError(f'{self.__class__.__name__}.compute() #(failed to load pixmap)')
        elif (self.descriptors is None) or (self.keypoints is None):
            # Set the init_crop_rect
            height = self.image.shape[0]
            width = self.image.shape[1]
            #print(f'compute ORB (image size ({width},{height}))')
            # Run the ORB algorithm
            #print(f'ImageWithORB.compute({str(orb_config)})')
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
            (keypoints, descriptors) = ORB.detectAndCompute(self.image, None)
            self.ORB = ORB
            self.keypoints = keypoints if keypoints is not None else []
            self.descriptors = descriptors if descriptors is not None else []
            #print(f'{self.__class__.__name__}.compute() #(generated {len(self.keypoints)} keypoints, {len(self.descriptors)} descriptors)')
        else:
            pass

#---------------------------------------------------------------------------------------------------

class FeatureProjection(AbstractMatchCandidate):
    """This class contains the result of matching ORB descriptors using
    brute-force matching as in the SegmentedImage.find_matching_points()
    method."""

    def __init__(self):
        super().__init__()
        self.image = None
        self.rect = None
        self.homography = None
        self.inverse_homography = None
        self.query_points = None
        self.train_points = None
        self.perspective_view = None
        self.closeness = 1.0 #(values closer to 0.0 are more accurate)
        self.similarity = 0.0 #(values closer to 100.0 are more accurate)
        self.bound_lines = None
        self.string_id = None
        self.in_bounds = None

    def make(image, rect, query_points, train_points, closeness):
        """This is the actual initailizer, the __init__() function sets all
        fields to None. A non-standard initializer is used to catch
        exceptions and other sanity checks that might occur during and
        return None instead if anything seems wrong, which cannot be
        done from an ordinary __init__() function.

        The homography matrix argument 'homography' is expected to
        have been computed with points in the given 'segment' argument
        relative to the reference image, and the 'rect' argument
        contains the position of the 'segment' in the 'image' (the
        segment was cropped from the image), along with the width and
        height of the reference image. This 'rect' is
        perspective-projected then used to recompute the homography
        matrix relative to the image, rather than the segment.
        """
        self = FeatureProjection()
        self.image = image
        self.rect = rect
        self.query_points = query_points # comes from the reference image
        self.train_points = train_points # comes from the target image
        self.closeness = closeness #(values closer to 0 are more accurate)
        self.similarity = 1.0 - closeness
        #--------------------------------------------------
        try:
            offset = np.float32([self.rect[0], self.rect[1]])
            self.train_points += offset
            (homography, _mask) = cv.findHomography(
                self.query_points,
                self.train_points,
                cv.RANSAC,
                5.0,
              )
            #print(f'homography:\n{homography}')
            self.homography = homography
        except Exception as err:
            traceback.print_exception(err)
            return None
        #--------------------------------------------------
        # Reject the homography if the computed perspective transfrom
        # produces points that lie outside of the target image
        height = self.image.shape[0]
        width  = self.image.shape[1]
        for (x,y) in self.get_perspective_bounds():
            if (x < 0) or (x >= width) or (y < 0) or (y >= height):
                return None
            else:
                continue
        #--------------------------------------------------
        try:
            self.inverse_homography = numpy.linalg.inv(homography)
        except Exception as err:
            #print(f'ignoring, failed to compute inverse matrix for:\n{homography}')
            return None
        return self

    def get_rect(self):
        return self.rect

    def get_match_score(self):
        return self.similarity

    def get_match_points(self):
        offset = np.float32([])
        return self.train_points.reshape(-1,2)

    def get_perspective_bounds(self):
        if self.perspective_view is None:
            rect_matrix = util.rect_to_spline_matrix(
                (0, 0, self.rect[2], self.rect[3],),
              ).reshape(-1,1,2)
            self.perspective_view = cv.perspectiveTransform(
                rect_matrix,
                self.homography,
              ).reshape(-1,2)
        else:
            pass
        return self.perspective_view

    def get_bound_lines(self, rect=None):
        #print(f'{self.__class__.__name__}.get_bound_lines({rect})')
        if (rect is None) and (self.perspective_view is not None):
            return util.spline_matrix4x2_to_lines(self.perspective_view)
        else:
            rect_matrix = util.rect_to_spline_matrix(
                (rect if rect is not None else (0, 0, self.rect[2], self.rect[3])),
              ).reshape(-1,1,2)
            perspective_view = cv.perspectiveTransform(
                rect_matrix,
                self.homography,
              ).reshape(-1,2)
            return util.spline_matrix4x2_to_lines(perspective_view)

    def get_string_id(self):
        """After the feature rectangle is transformed into some irregular
        quadrilateral, the a string representation of the midpoint of
        this quadrilateral is used as the unique ID for this candidate. """
        if self.string_id is None:
            bound_lines = self.get_bound_lines()
            xsum = 0
            ysum = 0
            count = 0
            for ((x1, y1), (x2, y2)) in bound_lines:
                xsum += x1 + x2
                ysum += y1 + y2
                count += 2
            x = round(xsum / count)
            y = round(ysum / count)
            self.string_id = f'{x:05}x{y:05}'
            return self.string_id
        else:
            return self.string_id

    def check_crop_region_size(self):
        return self.in_bounds

    def crop_image(self, relative_rect=None):
        relative_rect = relative_rect if relative_rect is not None else self.rect
        (_x, _y, width, height) = relative_rect
        return cv.warpPerspective(
            self.image,
            self.inverse_homography,
            (width, heigth),
          )

    def crop_write_images(self, crop_rects, output_path):
        image_ID = self.get_string_id()
        for (label, (x, y, width, height)) in crop_rects.items():
            outpath = str(output_path).format(label=label, image_ID=image_ID)
            #print(f'{self.__class__.__name__}.crop_write_images() #(save {outpath!r})')
            image = cv.warpPerspective(
                self.image,
                self.inverse_homography,
                (width, height),
              )
            cv.imwrite(outpath, image)

#---------------------------------------------------------------------------------------------------

class SegmentedImage():
    """This class takes an image and segments it into squares in such a
    way that allows a smaller reference image to be found within each
    segment. The hypotenuse of the given RECT argument is used to
    construct segments, but if the hypotenuse is larger than the width
    or height of the target image, the minimum of the width, height,
    and hypotenuse is chosen as the segment size.
    """

    def __init__(self, orb_config, nparray2d, rect, progress=None):
        #print(f'{self.__class__.__name__}.__init__()')
        (_x, _y, seg_width, seg_height) = rect
        shape = nparray2d.shape
        img_height = shape[0]
        img_width  = shape[1]
        self.orb_config = orb_config
        self.progress_dialog = progress
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
        self.matched_points = None
        
    def guess_compute_steps_1D(img, seg, step_size_ratio=(1/4)):
        """For the sake of a progress bar, this function is used to compute
        how many tiles the image will contain, and so how many times
        an OpenCV API must be called. """
        top = img - seg
        subseg = round(seg*step_size_ratio)
        num_steps = max(1, math.ceil(top / subseg))
        step = math.floor(top / num_steps)
        return math.ceil(max(1, top / step))

    def foreach_1D(img, seg, step_size_ratio=(1/4)):
        """1-dimensional version of a kind of convolution-like operator that
        sub-divides an array "img" into segments of size "seg" with a
        step_size_ratio of 1/4th, meaning the window moves (seg*(1/4))
        pixels across the "img" on each iteration. Pass an optional
        "step_size_ratio" argument to modify that parameter, but the
        closer this value is to zero, the more time it will take to
        compute."""
        top = img - seg
        subseg = round(seg*step_size_ratio)
        num_steps = max(1, math.ceil(top / subseg))
        step = top / num_steps
        i = 0.0
        while (i < top):
            i = math.floor(i)
            yield (i, i+seg)
            i += step

    def guess_compute_steps(self):
        #print(f'{self.__class__.__name__}.guess_compute_steps()')
        return \
            SegmentedImage.guess_compute_steps_1D(self.image_height, self.segment_height) * \
            SegmentedImage.guess_compute_steps_1D(self.image_width,  self.segment_width)

    def foreach(self):
        #print(f'{self.__class__.__name__}.foreach()')
        for (y_min,y_max) in SegmentedImage.foreach_1D(self.image_height, self.segment_height):
            for (x_min,x_max) in SegmentedImage.foreach_1D(self.image_width, self.segment_width):
                #print(f'x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max}')
                yield \
                    ( (x_min, y_min, x_max-x_min, y_max-y_min,),
                      self.image[y_min:y_max, x_min:x_max],
                    )
                if self.progress_dialog is not None:
                    self.progress_dialog.update_progress(1)
                else:
                    pass

    def find_matching_points(self, ref):
        #print(f'{self.__class__.__name__}.find_matching_points(ref) #(ref is a {type(ref)})')
        if self.matched_points is not None:
            return self.matched_points
        else:
            self.matched_points = self.compute(ref)
            return self.matched_points

    def compute(self, ref):
        #print(f'{self.__class__.__name__}.compute(ref) #(ref is a {type(ref)})')
        ref.compute()
        (_x, _y, width, height) = ref.get_crop_rect()
        descriptor_threshold = self.orb_config.get_descriptor_threshold()
        reference_keypoints = ref.get_keypoints()
        reference_descriptors = ref.get_descriptors()
        if reference_descriptors is None:
            raise Exception('no reference descriptors')
        elif reference_keypoints is None:
            raise Exception('no reference keypoints')
        else:
            pass
        matched_points = []
        for ((x, y, _w, _h), segment) in self.foreach():
            segment_orb = ImageWithORB(segment, ref.get_orb_config())
            segment_orb.compute()
            segment_keypoints = segment_orb.get_keypoints()
            segment_descriptors = segment_orb.get_descriptors()
            if len(segment_descriptors) < self.orb_config.get_minimum_descriptor_count():
                #print(f'ignore block ({x:05},{y:05}), only {len(segment_descriptors)} descriptors created')
                pass
            else:
                bruteforce_match = cv.BFMatcher()
                matches = bruteforce_match.knnMatch(
                    reference_descriptors,
                    segment_descriptors,
                    k=2
                  )
                best_matches = []
                nsum = 0
                bestsum = 0
                for m,n in matches:
                    #print(f'M: {m.distance}, N: {n.distance}')
                    nsum += n.distance
                    if m.distance < descriptor_threshold * n.distance:
                        bestsum += m.distance
                        best_matches.append(m)
                    else:
                        pass
                if len(best_matches) < self.orb_config.get_minimum_descriptor_count():
                    #print(f'ignore block ({x:05},{y:05}), only {len(best_matches)} best matches (out of {len(matches)})')
                    pass
                else:
                    target_keypoints = segment_orb.get_keypoints()
                    reference_selection = np.float32(
                        [reference_keypoints[m.queryIdx].pt for m in best_matches],
                      )
                    reference_selection = reference_selection.reshape(-1,1,2)
                    target_selection = np.float32(
                        [target_keypoints[m.trainIdx].pt for m in best_matches],
                      )
                    target_selection = target_selection.reshape(-1,1,2)
                    proj = FeatureProjection.make(
                        self.image,
                        (x, y, width, height,),
                        reference_selection,
                        target_selection,
                        (bestsum/nsum)/descriptor_threshold,
                      )
                    if proj is not None:
                        matched_points.append(proj)
                    else:
                        #print(f'{self.__class__.__name__}.find_matching_points() #(({x},{y}) ignored)')
                        pass
        return matched_points

#---------------------------------------------------------------------------------------------------

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
        self.descriptor_threshold = 0.7
        self.minimum_descriptor_count = 20
        #self.descriptor_nearest_neighbor_count = 2

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
            (self.fastThreshold == a.fastThreshold) and \
            (self.descriptor_threshold == a.descriptor_threshold) and \
            (self.minimum_descriptor_count == a.minimum_descriptor_count) \
            #(self.descriptor_nearest_neighbor_count == a.descriptor_nearest_neighbor_count) \
          )

    def from_dict(config):
        pass

    def to_dict(self):
        return \
          { 'N_features': self.nFeatures,
            'scale_factor': self.scaleFactor,
            'N_levels': self.nLevels,
            'edge_threshold': self.edgeThreshold,
            'first_level': self.firstLevel,
            'WTA_K': self.WTA_K,
            'score_type': self.scoreType,
            'patch_size': self.patchSize,
            'fast_threshold': self.fastThreshold,
            'descriptor_threshold': self.descriptor_threshold,
            'minimum_descriptor_count': self.minimum_descriptor_count,
            #'descriptor_nearest_neigbor_count': self.descriptor_nearest_neighbor_count,
          }

    def from_dict(config):
        self = ORBConfig()
        key_handlers = {
            'n_features': self.set_nFeatures,
            'scale_factor': self.set_scaleFactor,
            'n_levels': self.set_nLevels,
            'edge_threshold': self.set_edgeThreshold,
            'first_level': self.set_firstLevel,
            'wta_k': self.set_WTA_K,
            'score_type': self.set_scoreType,
            'patch_size': self.set_patchSize,
            'fast_threshold': self.set_fastThreshold,
            'descriptor_threshold': self.set_descriptor_threshold,
            'minimum_descriptor_count': self.set_minimum_descriptor_count,
          }
        used_handlers = set()
        for (key, value) in config.items():
            lkey = key.lower()
            if lkey in key_handlers:
                handler = key_handlers[lkey]
                del key_handlers[lkey]
                used_handlers |= {lkey}
                handler(value)
            elif lkey in used_handlers:
                raise ValueError('ORB config, parameter specified more than once', key, config)
            else:
                raise ValueError('ORB config, unknown parameter', key, config)
        return self

    def __str__(self):
        return str(self.to_dict())

    def get_nFeatures(self):
        return self.nFeatures

    def set_nFeatures(self, nFeatures):
        util.check_param('number of features', nFeatures, 20, 20000)
        self.nFeatures = nFeatures
        self.set_minimum_descriptor_count(self.minimum_descriptor_count)

    def get_scaleFactor(self):
        return self.scaleFactor

    def set_scaleFactor(self, scaleFactor):
        util.check_param('scale factor', scaleFactor, 1.0, 2.0)
        self.scaleFactor = scaleFactor

    def get_nLevels(self):
        return self.nLevels

    def set_nLevels(self, nLevels):
        util.check_param('number of levels', nLevels, 2, 32)
        self.nLevels = nLevels
        if self.firstLevel > nLevels:
            self.firstLevel = nLevels
        else:
            pass

    def get_edgeThreshold(self):
        return self.edgeThreshold

    def set_edgeThreshold(self, edgeThreshold):
        util.check_param('edge threshold', edgeThreshold, 2, 1024)
        self.edgeThreshold = edgeThreshold

    def get_firstLevel(self):
        return self.firstLevel

    def set_firstLevel(self, firstLevel):
        util.check_param('first level', firstLevel, 0, self.edgeThreshold)
        self.firstLevel = firstLevel

    def get_WTA_K(self):
        return self.WTA_K

    def set_WTA_K(self, WTA_K):
        util.check_param('"WTA" factor', WTA_K, 2, 4)
        self.WTA_K = WTA_K

    def get_scoreType(self):
        return self.scoreType

    def set_scoreType(self, scoreType):
        self.scoreType = scoreType

    def get_patchSize(self):
        return self.patchSize

    def set_patchSize(self, patchSize):
        util.check_param("patch size", patchSize, 2, 1024)
        self.patchSize = patchSize

    def get_fastThreshold(self):
        return self.fastThreshold

    def set_fastThreshold(self, fastThreshold):
        util.check_param('"FAST" threshold', fastThreshold, 2, 100)
        self.fastThreshold = fastThreshold

    def get_descriptor_threshold(self):
        return self.descriptor_threshold

    def set_descriptor_threshold(self, threshold):
        util.check_param('descriptor threshold', threshold, 0.01, 2.0)
        self.descriptor_threshold = threshold

    def get_minimum_descriptor_count(self):
        return self.minimum_descriptor_count

    def set_minimum_descriptor_count(self, count):
        """This parameter depends on the size of N-Features."""
        util.check_param('descriptor threshold', count, 4, round(self.nFeatures / 2))
        self.minimum_descriptor_count = count

    # def get_descriptor_nearest_neigbor_count(self):
    #     return self.descriptor_nearest_neighbor_count

    # def set_descriptor_nearest_neigbor_count(self, K):
    #     util.check_param('descriptor nearest neighbor count', K, 1, 5)
    #     self.descriptor_nearest_neighbor_count = K

#---------------------------------------------------------------------------------------------------

class ORBMatcher(AbstractMatcher):

    """This class creates objects that represents the state of the whole
    application.
    """

    def __init__(self, app_model, orb_config=None):
        super().__init__(app_model)
        self.orb_config = ORBConfig()
        self.last_run_orb_config = None
        self.cached_image = None
        self.reference_with_orb = None
        reference = self.app_model.get_reference_image()
        if reference.get_path() is not None:
            self.update_reference_image(reference=reference)
        else:
            pass

    def configure_from_json(self, config):
        if 'threshold' in config:
            threshold = config['threshold']
            if isinstance(threshold, int):
                threshold = threshold / 100.0
            elif isinstance(threshold, float):
                pass
            else:
                raise ValueError('ORB config parameter "threshold" is not a number', threshold, config)
            self.app_model.set_threshold(threshold)
            del config['threshold']
            self.orb_config = ORBConfig.from_dict(config)
        else:
            pass

    def configure_to_json(self):
        config = self.orb_config.to_dict()
        config['threshold'] = self.app_model.get_threshold()
        return config

    def get_orb_config(self):
        return self.orb_config

    def set_orb_config(self, orb_config):
        #print(f'ORBMatcher.set_orb_config({orb_config})')
        if (orb_config is not None) and (not isinstance(orb_config, ORBConfig)):
            raise ValueError(
                f'MainAppMode.set_orb_config() called with value of type {str(type(orb_config))}',
                orb_config,
              )
        elif self.reference_with_orb is not None:
            self.reference_with_orb.set_orb_config(orb_config)
        else:
            pass
        #print(f'ORBMatcher.set_orb_config() #(set self.orb_config = {orb_config})')
        self.orb_config = deepcopy(orb_config)

    def get_reference_with_orb(self):
        return self.reference_with_orb

    def set_reference_with_orb(self, image):
        #print(f'{self.__class__.__name__}.set_Reference_with({image})')
        self.reference_with_orb = ImageWithORB(image, self.orb_config)
        self.reference_with_orb.compute()

    def get_keypoints(self):
        if self.reference_with_orb is not None:
            return self.reference_with_orb.get_keypoints()
        else:
            return None

    def get_descriptors(self):
        if self.reference_with_orb is None:
            return None
        else:
            return self.reference_with_orb.get_descriptors()

    def needs_refresh(self):
        return \
            AbstractMatcher(self) or \
            (self.orb_config != self.last_run_orb_config) or \
            (self.cached_image is None)

    def set_threshold(self, threshold):
        """This function filters the list of matched items by their threshold
        value. All other functions which access the matched points in
        the image go through this function. """ 
        item_list = AbstractMatcher.get_matched_points(self)
        if item_list is not None:
            #print(f'{self.__class__.__name__}.set_threshold({threshold:.3}) #(filter list of {len(item_list)} items)')
            return \
              [ item for item in item_list \
                if item.get_match_score() >= threshold \
              ]
        else:
            #print(f'{self.__class__.__name__}.set_threshold({threshold:.3}) #(self.get_matched_points() returned None)')
            return None

    def guess_compute_steps(self):
        cached = self.cached_image
        if cached is None:
            return 0
        else:
            return cached.guess_compute_steps()

    def match_on_file(self, progress=None):
        #print(f'{self.__class__.__name__}.match_on_file()')
        points = AbstractMatcher.get_matched_points(self)
        if points is None or self.needs_refresh():
            return self.force_match_on_file(progress=progress)
        else:
            return self.get_match_points()

    def update_reference_image(self, reference=None):
        # Reference must be a CachedCVImageLoader object
        reference = reference if reference is not None else self.app_model.get_reference_image()
        if not reference or reference.get_path() is None:
            raise ValueError('reference image has not been selected')
        else:
            reference.load_image()
            self.reference_with_orb = ImageWithORB(reference, self.orb_config)
            self.reference_with_orb.compute()
            self.last_run_orb_config = self.orb_config
    
    def force_match_on_file(self, progress=None):
        """This function is triggered when you double-click on an item in the image
        list in the "FilesTab". It starts running the pattern matching algorithm
        and changes the display of the GUI over to the "InspectTab". """
        #print(f'{self.__class__.__name__}.force_match_on_file()')
        target = self.app_model.get_target_image()
        if not self.reference_with_orb:
            self.update_reference_image()
        else:
            pass
        target = self.app_model.get_target_image()
        target_image = target.get_image()
        reference_bounds = self.reference_with_orb.get_crop_rect()
        if target_image is None:
            #print(f'{self.__class__.__name__}.match_on_file() #(self.reference.get_image() returned None)')
            raise ValueError('input image not selected')
        else:
            #print(f'{self.__class__.__name__}.force_match_on_file() #(construct SegmentedImage())')
            segmented_image = SegmentedImage(
                self.orb_config,
                target_image,
                reference_bounds,
                progress=progress
              )
            self.cached_image = segmented_image
            if progress is not None:
                guess = self.guess_compute_steps()
                progress.add_work(guess, label='Scanning image')
            else:
                pass
            matched_points = segmented_image.find_matching_points(self.reference_with_orb)
            AbstractMatcher._update_matched_points(self, matched_points)
            return self.get_matched_points()
            
    def get_matched_points(self):
        """See documentation for DataPrepKit.AbstractMatcher.get_matched_points()."""
        #print(f'{self.__class__.__name__}.get_matched_points()')
        threshold = self.app_model.get_threshold()
        return self.set_threshold(threshold)

    def get_feature_points(self):
        if self.reference_with_orb is not None:
            #print(f'{self.__class__.__name__}.get_feature_points()')
            points = self.reference_with_orb.get_keypoints()
            return [point.pt for point in points]
        else:
            #print(f'{self.__class__.__name__}.get_feature_points() #(ignored: self.reference_with_orb is None)')
            return None
