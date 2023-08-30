from ImageMask import *

import sys

# --------------------------------------------------------------------------------------------------

imask = ImageMask(
    name="simple example",
    blitOp=Fill(),
    color=True,
    transforms=[],
    shapes=[
        Circle(
            point=Point(x=0, y=0),
            radius=5
          ),
        Rectangle(
            point=Point(x=0, y=0),
            bounds=BoundArea(width=5, height=5)
          )
      ],
  )

imask.prettyJSON(sys.stdout, 0)
