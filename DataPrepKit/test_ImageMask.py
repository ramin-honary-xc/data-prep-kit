from ImageMask import *

import json
import sys

# --------------------------------------------------------------------------------------------------

def withOutputToString(f, *args):
    tempbuf = io.StringIO()
    f(tempbuf, *args)
    return tempbuf.getvalue()

def testPrettyJSON(obj, show=False):
    prettystr = withOutputToString(imask.prettyJSON, 0)
    if show:
        print(prettystr)
    else:
        pass
    reloaded = json.load(io.StringIO(prettystr), object_hook=ImageMask.fromJSON)
    if reloaded == obj:
        pass#es the test
    else:
        print('TEST FAILED: Decoding pretty-printed JSON yields different object from original')
        print('-------------------- original --------------------')
        print(prettystr)
        print('-------------------- decoded ---------------------')
        json.dump(reloaded, sys.stdout, indent=2)
        raise

def testToJSON(inobj, show=False):
    jsonobj = inobj.toJSON()
    jsonobjstr = json.dumps(jsonobj, indent=2)
    if show:
        print(jsonobjstr)
    else:
        pass
    reloaded = ImageMask.fromJSON(inobj)
    if reloaded == inobj:
        pass#es the test
    else:
        print('TEST FAILED: Decoding toJSON() generated object yeilds different object from original')
        print('-------------------- toJSON() --------------------')
        json.dump(inobj, sys.stdout, indent=2)
        print('\n-------------------- fromJSON ---------------------')
        json.dump(reloaded, sys.stdout, indent=2)

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

testPrettyJSON(imask, True)
testToJSON(imask, True)
