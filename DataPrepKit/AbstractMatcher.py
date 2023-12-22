class AbstractMatchCandidate():

    def __init__(self):
        pass

    def get_rect(self):
        return None

    def get_match_score(self):
        """This function should return a value between 0.0 and 1.0 where
        values closer to 1.0 are candidates more similar to the
        reference, and values closer to 0.0 are candidates less
        similar to the reference. Candidates will be filtered by
        end-users of this app in using the interactive "threshold"
        control which is a percentage computed by multiplying the
        value returned by this function by 100.0. """
        return 0.0

    def get_string_id(self):
        """This function should return a string that can be appended to a fill
        path when writing the result of the pattern match to a file on disk."""
        return ''

    def check_crop_region_size(self):
        return False

    def crop_write_image(self, crop_rects, output_path):
        """The arguments are as follows:

          - rect_list: the dictionary of string labels associated with
            rectangles, each rectangle formatted as a 4-tuple
            (x,y,width,height) to crop from the current result.

          - output_path: a string to be formatted by the Python
            "format()" function, where the variables "{label}" and
            "{image_ID}" is replaced with a string that uniquely
            identifies the output image for this batch.

        """
        pass

#---------------------------------------------------------------------------------------------------

class AbstractMatcher():
    """This class contains methods and fields common to all of the
    '*Matcher' algorithms (ORBMatcher, and RMEMatcher)."""

    def __init__(self, app_model):
        self.app_model = app_model
        self.matched_points = None
        self.last_run_target = None
        self.last_run_reference = None

    def _get_matched_points(self):
        return self.matched_points

    def _update_inputs(self, target, reference):
        self.last_run_reference = reference.get_path()
        self.last_run_target = target.get_path()

    def _update_matched_points(self, matched_points):
        self.matched_points = matched_points
        return matched_points

    def needs_refresh(self):
        """Computes whether conditions have changes such that the pattern
        match algorithm needs to be run again. Conditions that would
        return True include when the match has not been run yet, when
        the target or reference images have changed, or when the
        threshold has changed. """
        return \
            (self.matched_points is None) \
            (self.last_run_target != self.app_model.get_target_image().get_path()) or \
            (self.last_run_reference != self.app_model.get_reference_image().get_path())

    def match_on_file(self):
        """Runs the pattern matching algorithm regardless of whether the
        computation needs to be refreshed, and caches the result. To
        obtain cached results, use 'get_matched_points() instead,
        which will only run this computation if necessary. """
        return self.matched_points

    def get_matched_points(self):
        """This function lazily computes a list of patterm matching regions
        that are most similar to the reference image. It runs
        'needs_refresh()' to see if the result needs to be computes,
        computes and caches the result if necessary, and then returns
        the most recently cached results. """
        #print(f'{self.__class__.__name__}.get_matched_points()')
        return self.matched_points

    def set_threshold(self, threshold):
        """This method should update the state of the matcher so that
        candidates are added or removed to the list of candidates
        returned by 'match_on_file()' and return this upadted
        list. This function by default calls the 'match_on_file()'
        method and returns its result."""
        if threshold != self.threshold:
            self.threshold = threshold
        else:
            pass
        return self.get_matched_points()

    def save_calculations(self):
        """This function is called to save the intermediate steps used to
        comptue the pattern matching operation. In the case of the RME
        matching algorithm, the distance map is saved to a file. """
        pass

