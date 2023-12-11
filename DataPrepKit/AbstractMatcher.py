class AbstractMatchCandidate():

    def __init__(self):
        pass

    def get_rect(self):
        return None

    def get_match_score(self):
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
        return []

    def get_matched_points(self):
        """This function lazily computes a list of patterm matching regions
        that are most similar to the reference image. It runs
        'needs_refresh()' to see if the result needs to be computes,
        computes and caches the result if necessary, and then returns
        the most recently cached results. """
        print(f'{self.__class__.__name__}.get_matched_points()')
        if self.matched_points is None:
            self.match_on_file()
        else:
            pass
        return self.matched_points

    def save_calculations(self):
        """This function is called to save the intermediate steps used to
        comptue the pattern matching operation. In the case of the RME
        matching algorithm, the distance map is saved to a file. """
        pass

