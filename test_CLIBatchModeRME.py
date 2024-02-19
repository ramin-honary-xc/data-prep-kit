import unittest
from pathlib import Path
import shutil
from datetime import datetime
import cv2 as cv

import patmatkit
from DataPrepKit.SingleFeatureMultiCrop import SingleFeatureMultiCrop

class CLIBatchModeRME():

    # These static variables depend on the location of the test fixtures.
    # These were determined when the text fixtures were first constructed,
    # so never change them unless you create a new set of text fixtures,
    # or perhaps if you rename the pattern and target image files.

    pattern_image = './tests/fixtures/pattern.png'
    input_images = [
        './tests/fixtures/target1.png',
        './tests/fixtures/target2.png',
        './tests/fixtures/target3.png',
      ]
    crop_regions = '{"left":[2,2,8,14],"right":[8,2,8,14]}'
      # This should definitely only ever be changed if a new set of
      # test fixtures is constructed.

    fixtures_dir = Path('./tests/fixtures')

    ################################################################################

    def __init__(self, output_dir, threshold, do_cleanup=True):
        # Set 'do_cleanup' to False if tests are failing due to
        # creating files with incorrect results, and you want to
        # inspect the files after the test files. If this is True, all
        # files are deleted after the test reports are written.
        self.output_dir = output_dir
        self.do_cleanup = do_cleanup
        self.threshold = threshold
        self.init_args = [
            '--algorithm=RME',
            f'--threshold={self.threshold}',
            f'--pattern={CLIBatchModeRME.pattern_image!s}',
          ]
        threshold_subdir = Path(f'threshold-{threshold:03}')
        full_dir = Path('results-full')
        regions_dir = Path('results-crop-regions')
        self.output_dir_full = \
            output_dir / threshold_subdir / full_dir
        self.compare_dir_full = \
            CLIBatchModeRME.fixtures_dir / threshold_subdir / full_dir
        self.output_dir_regions = \
            output_dir / threshold_subdir / regions_dir
        self.compare_dir_regions = \
            CLIBatchModeRME.fixtures_dir / threshold_subdir / regions_dir
        #----------------------------------------
        self.args = list(self.init_args)
        self.args += [
            f'--output-dir={self.output_dir_full!s}',
          ] + CLIBatchModeRME.input_images
        #----------------------------------------
        self.args_with_regions = list(self.init_args)
        self.args_with_regions += [
            f'--output-dir={self.output_dir_regions!s}',
            f'--crop-regions={CLIBatchModeRME.crop_regions}',
          ] + CLIBatchModeRME.input_images

    def identify(self):
        return {'output_dir': self.output_dir, 'threshold': self.threshold}

    def identify_full(self):
        return {'output_dir': self.output_dir_full, 'threshold': self.threshold}

    def identify_regions(self):
        return {'output_dir': self.output_dir_regions, 'threshold': self.threshold}

    def __repr__(self):
        return repr(self.identify())

    def __str__(self):
        return repr(self)

    def run(self, args):
        cli_config = patmatkit.arper.parse_args(args)
        app_model = SingleFeatureMultiCrop(cli_config)
        app_model.batch_crop_matched_patterns()

    def compare_dir_contents(self, output_dir, compare_dir):
        output_tree = { f for f in output_dir.glob('**/*') if f.is_file() }
        compare_tree = { f for f in compare_dir.glob('**/*') if f.is_file() }
        trimmed_output_tree = {Path(*f.parts[1:]) for f in output_tree}
        trimmed_compare_tree = {Path(*f.parts[2:]) for f in compare_tree}
        if trimmed_output_tree != trimmed_compare_tree:
            missing = trimmed_compare_tree - trimmed_output_tree
            extra = trimmed_output_tree - trimmed_compare_tree
            raise ValueError(
                f'test case produced wrong directory content, '
                f'{len(missing)} of {len(compare_tree)} files missing, {len(extra)} extra files',
                {'missing':missing, 'extra':extra},
              )
        else:
            for (a, b) in zip(sorted(output_tree), sorted(compare_tree)):
                a_img = cv.imread(str(a))
                if a_img is None:
                    raise ValueError('failed to read image file', a)
                else:
                    pass
                b_img = cv.imread(str(b))
                if b_img is None:
                    raise ValueError('failed to read image file', b)
                else:
                    pass
                if not ((a_img.shape == b_img.shape) and (a_img==b_img).all()):
                    raise ValueError('file content do not match', a, b)
                else:
                    continue
            return True

    def cleanup(self, path):
        if self.do_cleanup:
            shutil.rmtree(path)
        else:
            pass

    def run_full(self):
        self.run(self.args)
        result = self.compare_dir_contents(self.output_dir_full, self.compare_dir_full)
        self.cleanup(self.output_dir_full)
        return result
        
    def run_regions(self):
        self.run(self.args_with_regions)
        result = self.compare_dir_contents(self.output_dir_regions, self.compare_dir_regions)
        self.cleanup(self.output_dir_regions)
        return result


class TestCLI_BatchModeRME(unittest.TestCase):
    """This runs the RME algorithm with test fixtures to ensure that
    setting up this application from the CLI works as expected. CLI
    usage is simulated by running the argument parser with arguments
    defined in this test case to construct an argument parser result
    which is then used to creating the batch file processing object.
    """
    
    def __init__(self, context):
        super().__init__(context)
        #----------------------------------------------------------------
        # Each sub-test runs the same test suite with different CLI
        # arguments. This is the list of CLI arguments that defines each
        # sub-test. This 

        t = datetime.today()
        self.output_dir = Path(
            f'./test-results'
            f'_{t.year:04}{t.month:02}{t.day:02}'
            f'_{t.hour:02}{t.minute:02}{t.second:02}'
            f'_{t.microsecond:06}',
          )
        self.subtest_cases = [
            CLIBatchModeRME(self.output_dir, threshold, do_cleanup=True) \
            for threshold in [100, 99, 90, 80, 50]
          ]

    def test_batch_mode_RME(self):
        self.output_dir.mkdir(exist_ok=True, parents=True)
        for subtest_case in self.subtest_cases:
            with self.subTest(subtest_case=subtest_case.identify_full()):
                self.assertTrue(subtest_case.run_full())
            with self.subTest(subtest_case=subtest_case.identify_regions()):
                self.assertTrue(subtest_case.run_regions())
