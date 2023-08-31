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
        json.dump(inobj, sys.stdout, indent=2)
        print('\n-------------------- fromJSON ---------------------')
        json.dump(reloaded, sys.stdout, indent=2)

# --------------------------------------------------------------------------------------------------

pt0 = Point(x=0, y=0)
testToJSON(pt0, Point, False)
testPrettyJSON(pt0, Point, False)

# --------------------------------------------------------------------------------------------------

circle = Circle(origin=pt0, radius=5)
testToJSON(circle, Circle, False)
testPrettyJSON(circle, Circle, False)

# --------------------------------------------------------------------------------------------------

rectangle = Rectangle(origin=Point(x=0, y=0), bounds=BoundArea(width=5, height=5))
testToJSON(rectangle, Rectangle, False)
testPrettyJSON(rectangle, Rectangle, False)

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
