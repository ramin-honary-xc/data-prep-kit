from ImageMask import *

from typing import Any, Optional
from dataclasses import dataclass
import json
from json import JSONDecodeError
import traceback
import sys

# --------------------------------------------------------------------------------------------------

@dataclass
class FailedTest(BaseException):
  message: Optional[str] = None
  expected: Any = None
  received: Any = None
  source: Optional[str] = None
  exception: Optional[BaseException] = None

  def __repr__(self):
    return \
      ( 'TEST FAILED:' +
        (f' {self.message}\n' if self.message else '\n') +
        (f'-------------------- Expected --------------------\n{self.expected}\n'
         if self.expected else ''
         ) +
        (f'-------------------- Received --------------------\n{self.received}\n'
         if self.received else ''
         ) +
        ( f'-------------------- Exception --------------------\n{self.exception}'
          if self.exception else ''
         ) +
        ( f'-------------------- Source --------------------\n{self.source}'
          if self.source else ''
        )
      )

def withOutputToString(f, *args):
    tempbuf = io.StringIO()
    f(tempbuf, *args)
    return tempbuf.getvalue()

def testPrettyJSON(obj, CLASS, show=False):
    prettystr = withOutputToString(obj.prettyJSON, 0)
    if show:
        print(prettystr)
    else:
        pass
    try:
        parsed = json.load(io.StringIO(prettystr))
        reloaded = CLASS.fromJSON(parsed)
        if reloaded == obj:
            pass#es the test
        else:
            raise FailedTest(
                message='Decoding pretty-printed JSON yields different object from original',
                expected=obj,
                received=reloaded,
                source=prettystr,
              )
    except Exception as err:
        traceback.print_exception(err)
        print(repr(err))

def testToJSON(inobj, CLASS, show=False):
    jsonobj = inobj.toJSON()
    if jsonobj is None:
      print('TEST FAILED: toJSON() resulted in None')
      return
    else:
        pass
    jsonobjstr = json.dumps(jsonobj, indent=2)
    if show:
        print(jsonobjstr)
    else:
        pass
    reloaded = CLASS.fromJSON(jsonobj)
    if reloaded == inobj:
        pass#es the test
    else:
        print('TEST FAILED: Decoding toJSON() generated object yeilds different object from original')
        print('-------------------- toJSON() --------------------')
        json.dump(jsonobj, sys.stdout, indent=2)
        print('\n-------------------- fromJSON ---------------------')
        print(f'{reloaded!r}')
        print('--------------------------------------------------\n')

# --------------------------------------------------------------------------------------------------

pt0 = Point(x=0, y=0.01)
testToJSON(pt0, Point, False)
testPrettyJSON(pt0, Point, False)

# --------------------------------------------------------------------------------------------------

area = BoundArea(width=5, height=6.3)
testToJSON(area, BoundArea, False)

# --------------------------------------------------------------------------------------------------

circle = Circle(origin=pt0, radius=5.8)
testToJSON(circle, Circle, False)
testPrettyJSON(circle, Circle, False)

# --------------------------------------------------------------------------------------------------

rectangle = Rectangle(origin=pt0, bounds=area)
testToJSON(rectangle, Rectangle, False)
testPrettyJSON(rectangle, Rectangle, False)

# --------------------------------------------------------------------------------------------------

ellipse = Ellipse(origin=pt0, bounds=area)
testToJSON(ellipse, Ellipse, False)
testPrettyJSON(ellipse, Ellipse, False)

# --------------------------------------------------------------------------------------------------

polygon = Polygon(
  points=[
      Point(x=14.2, y=1.0),
      Point(x=33.0, y=17.9),
      Point(x=3.3, y=24.5),
    ]
  )
testToJSON(polygon, Polygon, False)
testPrettyJSON(polygon, Polygon, False)

# --------------------------------------------------------------------------------------------------

bspline = BSpline(
  points=[
      BPoint(
          point=Point(x=14.2, y=1.0),
          ctrl1=Point(x=13.0, y=1.5),
          ctrl2=Point(x=30.9, y=16.8),
        ),
      BPoint(
          point=Point(x=33.0, y=17.9),
          ctrl1=Point(x=28.4, y=18.5),
          ctrl2=Point(x=5.7, y=25.6),
        ),
      BPoint(
          point=Point(x=3.3, y=24.5),
          ctrl1=Point(x=2.0, y=27.8),
          ctrl2=Point(x=11.3, y=2.0),
        ),
    ]
  )
testToJSON(bspline, BSpline, True)
testPrettyJSON(bspline, BSpline, True)

# --------------------------------------------------------------------------------------------------

imask = ImageMask(
    blitOp=Fill(),
    color=True,
    name="simple example",
    transforms=[],
    shapes=[circle, rectangle],
  )

testPrettyJSON(imask, ImageMask, True)
testToJSON(imask, ImageMask, True)
