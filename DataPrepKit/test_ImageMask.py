from ImageMask import *

from typing import Any, Optional
from dataclasses import dataclass
import json
from json import JSONDecodeError
import traceback
from random import random, randint, choice
import math
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

bpoint = BPoint(
    point=Point(x=0, y=1),
    ctrl1=Point(x=2, y=3),
    ctrl2=Point(x=4, y=5),
  )
testToJSON(bpoint, BPoint, False)
testPrettyJSON(bpoint, BPoint, False)

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
testToJSON(bspline, BSpline, False)
testPrettyJSON(bspline, BSpline, False)

# --------------------------------------------------------------------------------------------------

translate = Translate(offset=Point(x=-5,y=4))
testToJSON(translate, Translate, False)
testPrettyJSON(translate, Translate, False)

rotate = Rotate(angle=0.707)
testToJSON(rotate, Rotate, False)
testPrettyJSON(rotate, Rotate, False)

scale = Scale(by=BoundArea(width=0.8,height=1.5))
testToJSON(scale, Scale, False)
testPrettyJSON(scale, Scale, False)

# --------------------------------------------------------------------------------------------------

guidepoint = GuidePoint(point=Point(x=50,y=75))
testToJSON(guidepoint, GuidePoint, False)
testPrettyJSON(guidepoint, GuidePoint, False)

guideline = GuideLine(a=Point(0,0),b=Point(50,75))
testToJSON(guideline, GuideLine, False)
testPrettyJSON(guideline, GuideLine, False)

horizontal = GuideHorizontal(x=50)
testToJSON(horizontal, GuideHorizontal, False)
testPrettyJSON(horizontal, GuideHorizontal, False)

vertical = GuideVertical(y=75)
testToJSON(vertical, GuideVertical, False)
testPrettyJSON(vertical, GuideVertical, False)

# --------------------------------------------------------------------------------------------------

imask = ImageMask(
    blitOp=Fill(),
    color=True,
    name="simple example",
    transforms=[translate, rotate, scale],
    guides=[guidepoint, guideline, horizontal, vertical],
    shapes=[circle, rectangle, bspline, ellipse, polygon],
  )
testPrettyJSON(imask, ImageMask, False)
testToJSON(imask, ImageMask, False)

# --------------------------------------------------------------------------------------------------

maxdepth = 3

def randListOf(randGen, d, minLength=0, maxLength=10):
  length = randint(minLength, maxLength)
  result = []
  for i in range(minLength, length):
    result.append(randGen(d))
  return result

def randName(d):
  a = choice([None, None, None, None, None, None, None, None, None, None, None, None, None,
              'near', 'far', 'close', 'distant', 'upper', 'lower', 'left', 'right', 'center',
              'middle', 'foreward', 'backward', 'tiny', 'small', 'medium', 'big', 'large',
              'sideways', 'diagonal', 'long', 'short', 'crooked', 'twisted', 'main', 'alternate'])
  b = choice([None, None, None, None, None, None,
              'red','orange','yellow','green','blue','purple','violet'])
  c = choice(['circle', 'polygon', 'triangle', 'square', 'pentagon', 'hexagon', 'octagon',
              'semicircle', 'star', 'trapezoid', 'rhombus', 'parallelogram', 'chip', 'chunk',
              'lead', 'stem', 'path', 'lamp', 'cell', 'switch', 'contact', 'pad', 'sample'])
  a = [a] if a else []
  b = [b] if b else []
  return ' '.join(a + b + [c])

randMaybeName = (
    lambda d: (choice([(lambda d: None), randName]))(d)
  )

def randComment(d):
  # Almost as good as ChatGPT:
  nounChoices = [
      (lambda: f'the {randName(d)}'),
      (lambda: f'the {randName(d)} and the {randName(d)}'),
      (lambda: f'either the {randName(d)} or the {randName(d)}'),
      (lambda: f'any of the {randName(d)}s, the {randName(d)}s, and/or the {randName(d)}s'),
      (lambda: f'the {randName(d)} but not {randName(d)}'),
      (lambda: f'all of the {randName(d)}s'),
      (lambda: f'any one of the {randName(d)}'),
      (lambda: f'the {randName(d)} next to the {randName(d)}'),
    ]
  ##-------- start test --------
  #print('Nouns:')
  #for f in nounChoices:
  #  print(f'- {f()}')
  ##-------- end test --------
  noun = (lambda: (choice(nounChoices))())
  relativePlacement = \
    ( lambda:
        choice(
            [ 'next to', 'between', 'below', 'above', 'around', 'near',
              'parallel to', 'perpendicular to',
              'to the left of', 'to the right of', 'that is connected to'
            ]
          )
     )
  relativeNounChoices = [
      noun, noun, noun, noun, noun,
      (lambda: f'{noun()} {relativePlacement()} {noun()}'),
      (lambda: f'{noun()} and {noun()} that are {relativePlacement()} {noun()}'),
      (lambda: f'{noun()} that is {relativePlacement()} {noun()} and {noun()}'),
      (lambda: f'{noun()} and {noun()} that are {relativePlacement()} {noun()} and {noun()}'),
      (lambda: f'{noun()} {relativePlacement()} {noun()} and {relativePlacement()} {noun()}'),
      (lambda: f'{noun()} that is {relativePlacement()} {noun()}, but not {relativePlacement()} {noun()}'),
    ]
  ##-------- start test --------
  #print('Relative nouns:')
  #for f in relativeNounChoices:
  #  print(f'- {f()}')
  ##-------- end test --------
  relativeNoun = (lambda: (choice(relativeNounChoices))())
  intransitiveVerb = \
    ( lambda:
        choice(['is connected to', 'is detatched from', 'overlays', 'awaits signals from', 'is set to move toward'])
    )
  intransitiveClause = (lambda: f'{relativeNoun()} {intransitiveVerb()} {relativeNoun()}')
  transitiveVerb = \
    ( lambda:
        choice(['connects to', 'detaches from', 'recedes from', 'signals', 'moves toward'])
    )
  transitiveClause = (lambda: f'{relativeNoun()} {transitiveVerb()} {relativeNoun()}')
  factChoice = [
      intransitiveClause, intransitiveClause, intransitiveClause,
      (lambda: f'{intransitiveClause()}, and {intransitiveClause()}.'),
      (lambda: f'{intransitiveClause()}, and also {intransitiveClause()}.'),
      (lambda: f'{intransitiveClause()}, while {intransitiveClause()}.'),
      (lambda: f'{intransitiveClause()}, however {intransitiveClause()}.'),
      (lambda: f'{intransitiveClause()}, as opposed to {relativeNoun()} which {intransitiveVerb()} {relativeNoun()}.'),
    ]
  fact = (lambda: (choice(factChoice))())
  actionChoice = [
      (lambda: f'{relativeNoun()} {transitiveClause()} {relativeNoun()}.'),
      (lambda: f'{relativeNoun()} {transitiveClause()} {relativeNoun()}, which then {transitiveClause()} {relativeNoun()}.'),
      (lambda: f'Once {relativeNoun()} {transitiveClause()} {relativeNoun()}, {relativeNoun()} {transitiveClause()} {relativeNoun()}.'),
      (lambda: f'When {relativeNoun()} {transitiveClause()} {relativeNoun()}, {relativeNoun()} then {transitiveClause()} {relativeNoun()}.'),
      (lambda: f'While {relativeNoun()} {transitiveClause()} {relativeNoun()}, {relativeNoun()} {transitiveClause()} {relativeNoun()}.'),
      (lambda: f'{relativeNoun()} {transitiveClause()} {relativeNoun()}, while at the same time {relativeNoun()} {transitiveClause()} {relativeNoun()}.'),
    ]
  ##-------- start test --------
  #print('Action:')
  #for f in actionChoice:
  #  print(f'- {f()}')
  ##-------- end test --------
  action = (lambda: (choice(actionChoice))())
  factStatement = (lambda: (choice([fact, (lambda: f'{fact()} {fact()}')]))())
  actionStatement = (lambda: (choice([action, (lambda: f'{action()} {action()}')]))())
  conclusion = (lambda: (choice([(lambda: ''), (lambda: f' Finally, {factStatement()}')]))())
  return f'{factStatement()} {actionStatement()} {conclusion()}'

##test randComment
#print(randComment(0))

randBool       = lambda d: (randint(0,2**31) % 2 == 0)
randAngle      = lambda d: random()*math.pi
randScalar     = lambda d: randint(-1000000,1000000)/1000
randPoint      = lambda d: Point(x=randScalar(d), y=randScalar(d))
randBoundArea  = lambda d: BoundArea(width=randScalar(d), height=randScalar(d))
randPolygon    = lambda d: Polygon(points=randListOf(randPoint, d))
randRotate     = lambda d: Rotate(angle=randAngle(d))
randTranslate  = lambda d: Translate(offset=randPoint(d))
randScale      = lambda d: Scale(by=randBoundArea(d))
randGuidePoint = lambda d: GuidePoint(point=randPoint(d))
randGuideLine  = lambda d: GuideLine(a=randPoint(d), b=randPoint(d))
randTransform  = lambda d: (choice([randRotate, randTranslate, randScale]))(d)
randStrokeJoin = lambda d: (choice([(lambda d: RoundJoin()), (lambda d: MiterJoin())]))(d)

randGuideHorizontal = lambda d: GuideHorizontal(x=random()*10000)
randGuideVertical   = lambda d: GuideVertical(y=random()*10000)

randStroke = (
    lambda d:
      Stroke(
          lineWidth=(round(90*random()+10)/randint(2, 10)),
          joinStyle=randStrokeJoin(d),
        )
  )

randBlitOp = lambda d: (choice([(lambda d: Fill()), (lambda d: randStroke(d))]))(d)

randGuide = (
    lambda d:
      (choice([randGuidePoint, randGuideLine, randGuideHorizontal, randGuideVertical]))(d)
  )

randBPoint = (
    lambda d:
      BPoint(
          point=randPoint(d),
          ctrl1=randPoint(d),
          ctrl2=randPoint(d),
        )
  )

randBSpline = lambda d: BSpline(points=randListOf(randBPoint, d))

randRectangle = (
    lambda d:
      Rectangle(
          origin=randPoint(d),
          bounds=randBoundArea(d),
          visible=randBool(d),
        )
  )

randCircle = (
    lambda d:
      Circle(
          origin=randPoint(d),
          radius=randScalar(d),
          startAngle=randAngle(d),
          endAngle=randAngle(d),
          visible=randBool(d),
        )
  )

randEllipse = (
    lambda d:
      Ellipse(
          origin=randPoint(d),
          bounds=randBoundArea(d),
          visible=randBool(d),
        )
  )

randGroup = (
    lambda d:
      ShapeGroup(
          name=randMaybeName(d),
          transforms=randListOf(randTransform, d),
          guides=randListOf(randGuide, d),
          shapes=randListOf(randShape, d),
        )
  )

def randShape(d):
  shapeGens = [randBSpline, randRectangle, randCircle, randEllipse, randPolygon]
  if d < maxdepth:
    groupGen = (lambda d: randGroup(d+1))
    shapeGens += [groupGen, groupGen]
  else:
    pass
  return (choice(shapeGens))(d)

randImageMask = (
    lambda:
      ImageMask(
          blitOp=randBlitOp(0),
          color=randBool(0),
          name=randMaybeName(0),
          transforms=randListOf(randTransform, 0),
          guides=randListOf(randGuide, 0),
          shapes=randListOf(randShape, 0),
        )
  )

#test randImageMask()
def runRandomTest(showJSON, showPretty):
  obj = randImageMask()
  testToJSON(obj, ImageMask, showJSON)
  testPrettyJSON(obj, ImageMask, showPretty)

runRandomTest(True, True)

## Run many tests on procedurally generated objects
#for i in range(0,10000):
#  runRandomTest(False, False)
