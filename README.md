# Data Prep Kit

This repository contains a few simple Python scripts which run a PyQt5
GUI allowing you to interactively prepare data using algorithms in the
OpenCV libarary.  In  particular these tools are  useful for preparing
data stored  in PNG,  BMP, or JPEG  files, for use  as input  to other
machine learning processes.

  **Note** that this repository does not included any machine learning
  algorithms, and only  makes use of algorithms present  in the OpenCV
  library.

Each of  the following  scripts is a  small, self-contained  tool that
presents an interactive GUI for preparing graphical data:

## How to build and run

**Python 3.10** or later should be used, any Python version prior to
this has not been tested.

This  project was  developed  under a  PIP  runtime environment  which
installs all required packages automatically  according to the list of
packages in `./requirements.txt`.

### Setup the runtime environment

#### On Unix (Mac OS X) or Linux systems:

Using a POSIX shell such as  `bash` with Python installed and included
in the `PATH` environment variable, you can run these steps:

```sh
python -m venv env               # 1. Setup the environment state directory
. ./env/bin/activate             # 2. Define the shell variables in the current shell
pip install -r requirements.txt  # 3. Install package requirements
```

#### On Windows systems:

Using  *PowerShell* with  the  Python installed  and  included in  the
`%PATH%` environment variable:

```sh
python -m venv env               # 1. Setup the environment state directory
. .\env\bin\Activate.ps1         # 2. Define the shell variables in the current shell
pip install -r requirements.txt  # 3. Install package requirements
```

### Running the program

After setting up  your Python environment with  the "activate" commad,
your shell is now ready to run the scripts in this directory. The main
script is `patmatkit.py` script, run it like this:

```shell
python3 ./patmatkit.py --gui
```

**Note** that the `--gui` argument is  required if you want to use the
script with a GUI, the default beahvior is to run as a batch process.

There is  also a  script for  visualizing differences  between cropped
images and the reference image:

```
python3 ./imgdiffkit.py
```

There  is also  an **experimental**  cropping tool  that uses  the ORB
algorithm to find  patterns, rather than an  ordinary convolution with
the root-mean error:

```
python3 ./imgcropkit.py
```

## About each of the tools in this kit

### `patmatkit.py`: a template matching tool
  
With  this tool,  first you  provide  a reference  image to  use as  a
"pattern". Then  you can  search many occurrences  in this  pattern in
larger  images.  The occurrences  need  not  match the  pattern  image
exactly, and  an interactive slider control  in the GUI allows  you to
select the best similarity threshold  value to maximimze true positive
matches and minimize false positive matches.

The reference  image is used  as a  convolution kernel on  each target
image, and the [Normalized Square Difference](https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html)
equation (sometimes  the Root-Mean Error  function or RME) is  used to
decide how similar every point in the target image is to the reference
image.

**By default**  this script runs as  a batch process with  no GUI. You
must  run the  script with  the `--gui`  flag in  order to  launch the
GUI. Without the `--gui` flag,  output files will be generated without
user feedback.

When  running  as a  batch  script,  you  must provide  the  following
parameters:

  - `--pattern <image-file>` -- "pattern image" (the reference image)
  
  - `--threshold <percentage>` -- a similarity threshold value between
    0.0 and  100.0. Note that  a 100.0 precent threshold  only accepts
    **exact** pixel-for-pixel matches to the reference image.

  - `--output-dir <directory>`  --  the  directory into  which cropped
    image files (areas of each  target image that match the reference)
    should be written. The directory is created if it does not exist.

Other CLI arguments include:

  - **A list of files** -- this list of files are the target images
    for which the reference image is searched.

  - `--gui` -- displays the GUI.  This argument may be used alone with
    no  other arguments,  as  all  parameters can  be  set within  the
    GUI.  This also  stops  the script  from  generating output  files
    automatically. Select "Save all selected regions" (Control-S) from
    the context menu in the "Inspect" tab to generate files.
  
    When the GUI is enabled, all other CLI arguments are inserted into
    the correct  controls of the  GUI automatically. For  example, the
    file  specified  by  the  `--pattern` argument  is  displayed  the
    "*Pattern*" tab, the  list of file arguments specified  on the CLI
    shows up in the "*Select*" tab, the default value of the threshold
    slider control  is set  to the  number specified  by `--threshold`
    argument, and so on.
    
  - `--verbose` -- will cause the  script to write log messages to the
    process  standard  output --  therefore  these  log messages  will
    usually be  visible in  the CLI  window from  which the  script is
    launched.

### `imgdiffkit.py`: an image comparison tool

This program is used to validate the results of the `patmatkit.py`
tool. If two images are provided, (1) an "input" image and (2) a
"reference" image, both being the exact same size, every pixel of the
reference image is subtracted from its corresponding (same x,y
coordinate) pixel in the input image, producing a new "difference"
image where each corresponding pixel contains the difference
value. Difference values are color-coded:

- Black -- identical
- Green -- 25% difference
- Yellow -- 50% difference
- Orange -- 75% difference
- Red -- 100% difference

#### Using this application in GUI mode

 1. Open the result images created by `patmatkit.py` in the "Search"
    tab by right-clicking in the left-hand file list, or by dragging and
    dropping the directory containing the results.

 2. In the "Reference" tab, select the pattern image that was used to
    construct the results.

 3. Go back to the "Search" tab and click on each file in the file
    list to select the "input" image to be compared to the "reference"
    image selected in the previous step. You may also use up/down
    arrow keys to navigate through each item in the list.

    In the right-hand display you will see the difference image
    visualization computed for each as described above.

### `imgcropkit.py`: a feature matching tool

**WARNING:** experimental.
  
Used for crop specific objects or recognizable features in larger
images. This tool allows you to select a reference image to set the
cropping area relative to certain features in the image. Then, given a
larger set of images, similar features are searched-for in each image
and cropped according to the reference image.

The [ORB feature-matching algorithm](https://docs.opencv.org/3.4/d1/d89/tutorial_py_orb.html)
is used to find and label features.

This script cannot be run as a batch script, so a GUI is always
displayed when the script runs.
