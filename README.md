# Data Prep Kit

This repository contains a few simple Python scripts which run a PyQt5
GUI allowing you to interactively prepare data using algorithms in the
OpenCV libarary.  In particular these  tools are useful  for preparing
data stored in  PNG or JPEG files,  for use as input  to other machine
learning processes.

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

## About each of the tools in this kit

### `patmatkit.py`: a template matching tool
  
With  this tool,  first you  provide  a reference  image to  use as  a
"pattern". Then  you can  search many occurrences  in this  pattern in
larger  images.  The occurrences  need  not  match the  pattern  image
exactly, and  an interactive slider control  in the GUI allows  you to
select the best similarity threshold  value to maximimze true positive
matches and minimize false positive matches.

The reference image is used as a convolution on each target image, and
the [Normalized Square Difference](https://docs.opencv.org/4.x/d4/dc6/tutorial_py_template_matching.html)
equation is used to decide how similar every point in the target image
is to the reference image.

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

### `imgcropkit.py`: a feature matching tool
  
Used  for crop  specific objects  or recognizable  features in  larger
images. This  tool allows you to  select a reference image  to set the
cropping area relative to certain features in the image. Then, given a
larger set of images, similar  features are searched-for in each image
and cropped according to the reference image.

The [ORB feature-matching algorithm](https://docs.opencv.org/3.4/d1/d89/tutorial_py_orb.html)
is used to find and label features.

This script cannot be run as a batch script, so a GUI is always
displayed when the script runs.
