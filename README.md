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

After setting up your Python environment with the "activate" commad,
your shell is now ready to run the scripts in this directory. The main
scripts are `patmatkit.py`, `imgsizekit.py`, and `imgdiffkit.py`. Run
any one of them like so:

```shell
python ./patmatkit.py --gui
python ./imgsizekit.py --gui
python ./imgdiffkit.py --gui
```

**Note** that the `--gui` argument is  required if you want to use the
script with a GUI, the default beahvior is to run as a batch process.

There  is also  an **experimental**  cropping tool  that uses  the ORB
algorithm to find  patterns, rather than an  ordinary convolution with
the root-mean error:

```
python ./imgcropkit.py
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

  - `-p` or `--pattern=<image-file>` -- "pattern image" (the reference image)
  
  - `-t` or `--threshold=<percentage>` -- a similarity threshold value
    between 0.0  and 100.0. Note  that a 100.0 precent  threshold only
    accepts **exact** pixel-for-pixel matches to the reference image.

  -  `-o` or  `--output-dir=<directory>` --  the directory  into which
    cropped image  files (areas  of each target  image that  match the
    reference) should be written. The  directory is created if it does
    not exist.

  - `-A` or `--algorithm={RME|ORB}` -- set the algorithm to RME (Root
    Mean Error, this is the default) to do pattern matching using the
    pattern image as a convolution where the root-mean error equation
    is used to determine how similar a portion of the image is to the
    pattern. Error values closer to zero are more similar and will be
    cropped from the input image.

    See below for more details about the [ORB algorithm].

    [ORB algorithm]: #the-oriented-fast-rotated-brief-orb-algorithm

  - `-x`  or `--crop-regions='{"region-name":[x,y,width,height],...}'`
    -- this  allows you to enter  crop regions on the  command line. A
    crop region  is a region  relative to  the the location  where the
    pattern has been found in an  input image. Rather than cutting out
    the portion  of the  image exactly  equal in  size to  the pattern
    image, you  can specify a  different rectangular area to  crop out
    instead. The  `x` and `y`  values can  be negative or  positive as
    they are  relative to the location  of the match within  the input
    image. The `width` and `height` values must be greater than zero.

  - `--encoding={PNG|JPG|BMP}` -- when creating files, force the files
    created from cropping the input image to assume this file
    encoding, rather than the default behavior which is to use the
    same encoding as the input image file. The full list of valid file
    encodings is determined by the capabilities of the OpenCV library,
    refer to the [OpenCV documentation][OpenCV-Docs].
    
    [OpenCV-Docs]:  https://docs.opencv.org/3.4/d4/da8/group__imgcodecs.html#ga288b8b3da0892bd651fce07b3bbd3a56

  -  `--config=<path-to-config>`  --   rather  than  configuring  this
    program using these CLI arguments,  you can save the configuration
    to a JSON  file (usually done in the GUI),  and use these settings
    again when  running the program in  batch mode (in the  CLI rather
    than the GUI).  If this argument is specified on  the command line
    but the `<path-to-config>` does not exist, it is created using the
    configuration specified by all of the other CLI arguments.

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

#### The Oriented-FAST Rotated BRIEF (ORB) Algorithm

ORB is an algorithm in OpenCV used  to search for features in an image
similar to features found in  a reference image. This section provides
a  brief overview  of how  ORB  works, but  for detailed  information,
please  read the  [research  paper][ORB Paper]  published  by the  ORB
authors:

[ORB Paper]: https://www.researchgate.net/publication/221111151_ORB_an_efficient_alternative_to_SIFT_or_SURF

The algorithm looks for things in the picture that look like corners
or points or angles. When it finds one, it takes a circle of pixels
around the center of that point. It then guesses the angle that the
circle is rotated by comparing the position of the centroid of the
pixels within the circle. It then uses that circle of pixels as a
"descriptor" which is compared to other descriptors that are found.If
at least 4 (but by default 20) points are found to be similar, it is
assumed that the points are a projection of the reference image.The
important factors are:

**NOTE** it  is important  that the  pattern image  have distinguished
features. A smooth or round  solid-colored object with no texture will
not be useful to ORB when trying to determine the feature points.

The ORB algorithm takes a few parameters which can be configured in
the "Settings" tab of the GUI:

  - **number of features:** finds more points to identify the plane in
    the image.  Higher numbers takes more computing time.

  - **Number  of matches:** not all  1000 feature points are  going to
    match  exactly.  This  number  (defaulting to  20) determines  the
    minimum number  of matches that  are allowed  for a region  in the
    target image to be considered a match.

  - **feature  threshold:** the percentage difference  between feature
    points.   This value  effects the  sensitivity of  the interactive
    threshold slider in the "Inspect" tab.

  - **number of levels:** the reference image copied and resized to be
    bigger this  many times, each copy  is a "level". This  allows the
    algorithm  to  objects in  the  photo  that  are larger  than  the
    reference image.

  - **scale factor:**  when an image is copied resized  to construct a
    "level", how much bigger is it made.

For the other parameters, please read the [original research
paper][ORB Paper] noted above.

There  is also  a [tutorial  in the  OpenCV documentation][OpenCV  ORB
Tutorial]  that explains  how this  algorithm  can be  used in  Python
programs.

[OpenCV ORB Tutorial]: https://docs.opencv.org/4.x/d1/de0/tutorial_py_feature_homography.html

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

### `imgsizekit.py`: a batch image resizing tool

This program allows you to batch-resize a list of selected images.

### `imgshiftkit.py`: translate or shift images with wrapping

Shift with wrap, that is, to transform an image by moving it without
changing its size, and the part of the image that have gone off of the
canvas, for example off to the left, are moved to the right-most part
of the canvas, parts of the image that have gone off the bottom of the
canvas are moved to the top-most part of the cavnas.

This tool is intended to perform data augmentation of images for
computer vision applications. If you have a dataset of image files,
where each image is a pattern or texture of some kind, shifting the
image can create a new data point from an existing data point that
might be useful to the machine learning training process, "teaching" a
neural network to disregard artifacts in the patterns or textures that
might occur regularly in a particular location in each image.

Therefore, by default, without any other arguments, each image is
shifted by a random amount. It is also possible to specify shifts at
regular intervals, for example 3 equal shifts to the right and 2 equal
shifts down, which will result in 6 output images.
