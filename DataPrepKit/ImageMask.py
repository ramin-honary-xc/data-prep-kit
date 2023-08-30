from typing import Union, Optional, TextIO
from abc import abstractmethod
from dataclasses import dataclass
from json import JSONEncoder, JSONDecoder, loads, dump
import io

def indented(o: TextIO, level: int, s: str) -> None:
    o.write((' '*level) + s)

def boolToJSON(b: bool) -> str:
    return ('true' if b else 'false')

def numFromJSON(obj: int|float|str) -> Optional[int|float]:
    if isinstance(obj, int):
        return obj
    elif isinstance(obj, float):
        return obj
    elif isinstance(obj, str):
        return int(obj) or float(obj)
    else:
        return None

def inlineBool(b: bool, o: TextIO, level: int) -> None:
    o.write(boolToJSON(b))

def goodLengthOrDie(args: list|dict, expected: int, constrName: str) -> None:
    if len(args) != expected:
        raise ValueError('{len(args)} arguments given to {constrName}, {expected} expected')
    else:
        pass

def goodArgOrDie(arg, argn: int, constrName: str, expected: str) -> None:
    """Assertion that checks if the first argument is not 'None'. In the
    event of 'None', eports an error for the constructor and what type
    was expected."""
    if not arg:
        raise ValueError('incorrect format for {constrName} argument {argn}, expected {expected}')
    else:
        pass

# --------------------------------------------------------------------------------------------------

class JSONizable():
    """Abstract class declaring the functions that the various @dataclass
    nodes must implement in order to be read or written as JSON data."""

    @abstractmethod
    def prettyJSON(self, o: TextIO, level: int) -> None: pass

    @abstractmethod
    def toJSON(self): pass

    @abstractmethod
    def fromJSON(obj): pass

def writeListJSON(o: TextIO, level: int, items: list[JSONizable]) -> None:
    """Can be inlined or indented depending on how many items there are."""
    itemslen = len(items)
    if itemslen == 0:
        o.write('[]')
    elif itemslen == 1:
        o.write('[')
        tempbuf = io.StringIO()
        items[0].prettyJSON(tempbuf, level+1)
        result = tempbuf.getvalue()
        if len(result) > 80 or result.find('\n') >= 0:
            o.write('\n')
            indented(o, level+1, result)
        else:
            o.write(result)
        o.write(']')
    else:
        o.write('[\n')
        level1 = level+1
        indented(o, level1, '')
        items[0].prettyJSON(o, level1)
        for item in items[1:]:
            o.write(',\n')
            indented(o, level1, '')
            item.prettyJSON(o, level1)
        o.write('\n')
        indented(o, level, ']')

# ==================================================================================================

class MaskShape(JSONizable):
    """This is a value used to create shapes that mask or unmask bits in a
    bitmap image. Note the naming convention I am using here: "black"
    means opaque (masked), white is transparent (unmasked).

    The GUI for this model places a black layer over an image, and the
    end user subtracts spaces from this black layer. So masking adds
    black back to the layer, unmasking removes black (makes it
    transparent).
    """
    visible: bool = True

    def fromJSON(obj):
        return \
            Rectangle.fromJSON(obj) or \
            Circle.fromJSON(obj) or \
            Ellipse.fromJSON(obj) or \
            Polygon.fromJSON(obj) or \
            Bspline.fromJSON(obj) or \
            ShapeGroup.fromJSON(obj)

# --------------------------------------------------------------------------------------------------

@dataclass
class Point(JSONizable):
    x: float
    y: float

    def prettyJSON(self, o, level):
        o.write('{' f'"x":{self.x},"y":{self.y}' '}')

    def toJSON(self):
        return {'x': self.x, 'y': self.y}

    def fromJSON(obj):
        if ('x' in obj) and ('y' in obj):
            goodLengthOrDie(obj, 2, '"Point"')
            x = numFromJSON(obj['x'])
            goodArgOrDie(x, 'x', 'Point', '"x: float"')
            y = numFromJSON(obj['y'])
            goodArgOrDie(x, 'y', 'Point', '"y: float"')
            return Point(x=float(x), y=float(y))
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class BoundArea(JSONizable):
    width: float
    height: float

    def prettyJSON(self, o, level):
        o.write('{' f'width:{self.width},height:{self.height}' '}')

    def toJSON(self):
        return {'width': self.width, 'height': self.height}

    def fromJSON(obj):
        if ('width' in obj) and ('height' in obj):
            goodLengthOrDie(obj, 2, 'BoundArea')
            width  = numFromJSON(obj['width'])
            goodArgOrDie(width, 'width', 'BoundArea', '"width: float"')
            height = numFromJSON(obj['height'])
            goodArgOrDie(width, 'height', 'BoundArea', '"height: float"')
            return BoundArea(width=float(width), height=float(width))
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Rectangle(MaskShape, JSONizable):
    point: Point
    bounds: BoundArea
    visible: bool = True

    def prettyJSON(self, o, level):
        o.write('["rectangle",')
        self.point.prettyJSON(o, level)
        self.bounds.prettyJSON(o, level)
        inlineBool(self.visible, o, level)
        o.write(']')

    def toJSON(self):
        return ['rectangle', self.point.toJSON(), self.bounds.toJSON(), self.visible]

    def fromJSON(obj):
        if obj[0] == 'rectangle':
            goodLengthOrDie(obj, 4, '"rectangle"')
            args = {}
            args['point'] = Point.fromJSON(obj[1])
            goodArgOrDie(args['point'], 1, '"rectangle"', 'Point')
            args['bounds'] = BoundArea.fromJSON(obj[2])
            goodArgOrDie(args['bounds'], 2, '"rectangle"', 'BoundArea')
            args['visible'] = bool(obj[3])
            goodArgOrDie(arg['visible'], 3, '"rectangle"', '"visible: bool"')
            return Rectangle(**args)
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Circle(MaskShape, JSONizable):
    point: Point
    radius: float
    startAngle: Optional[float] = None
    endAngle: Optional[float] = None
    visible: bool = True

    def prettyJSON(self, o, level):
        o.write(f'["circle",')
        self.point.prettyJSON(o, level)
        o.write(f',{self.radius},{self.startAngle},{self.endAngle},')
        inlineBool(self.visible, o, level)
        o.write(']')

    def toJSON(self):
        return (
            [ 'circle',
              self.point.toJSON(),
              self.radius,
              self.startAngle,
              self.endAngle,
              self.visible,
            ])

    def fromJSON(obj):
        if obj[0] == 'circle':
            goodLengthOrDie(obj, 6, '"circle"')
            args = {}
            args['point'] = Point.fromJSON(obj[1])
            goodArgOrDie(args['point'], 1, '"circle"', 'Point')
            args['radius'] = float(obj[2])
            goodArgOrDie(args['radius'], 2, '"circle"', '"radius: float"')
            args['startAngle'] = float(obj[3])
            goodArgOrDie(args['startAngle'], 3, '"circle"', '"startAngle: float"')
            args['endAngle'] = float(obj[4])
            goodArgOrDie(args['endAngle'], 4, '"circle"', '"endAngle: float"')
            args['visible'] = bool(obj[5])
            goodArgOrDie(arg['visible'], 5, '"circle"', '"visible: bool"')
            return Circle(**args)
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Ellipse(MaskShape, JSONizable):
    point: Point
    bounds: BoundArea
    visible: bool = True

    def prettyJSON(self, o, level):
        o.write('["ellipse",')
        self.point.prettyJSON(o, level)
        self.bounds.prettyJSON(o, level)
        o.write(f',{self.visible!r}]')

    def toJSON(self):
        return (
            [ 'ellipse',
              self.point.toJSON(),
              self.bounds.toJSON(),
              self.visible,
            ])

    def fromJSON(obj):
        if obj[0] == 'ellipse':
            goodLengthOrDie(obj, 4, '"ellipse"')
            args = {}
            args['point'] = Point.fromJSON(obj[1])
            goodArgOrDie(args['point'], 1, '"ellipse"', 'Point')
            args['bounds'] = BoundArea.fromJSON(obj[2])
            goodArgOrDie(args['bounds'], 2, '"ellipse"', 'BoundArea')
            args['visible'] = bool(obj[3])
            goodArgOrDie(args['visible'], 3, '"ellipse"', '"visible: bool"')
            return Ellipse(**args)
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Polygon(MaskShape, JSONizable):
    points: list[Point]

    def prettyJSON(self, o, level):
        o.write('["polygon"')
        for p in self.points:
            o.write(',\n')
            p.prettyJSON(o, level+1)
        indented(o, level, ']')

    def toJSON(self):
        result = ['polygon']
        for pt in self.points:
            result.append(pt.toJSON())
        return result

    def fromJSON(obj):
        if obj[0] == 'polygon':
            points = []
            for ptJSON in obj[1:]:
                points.append(Point.fromJSON(ptJSON))
            return Polygon(points=points)
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class BPoint(JSONizable):
    point: Point
    ctrl1: Point
    ctrl2: Point

    def prettyJSON(self, o, level):
        o.write('["bpt",')
        self.point.prettyJSON(o, level+1)
        self.ctrl1.prettyJSON(o, level+1)
        self.ctrl2.prettyJSON(o, level+1)
        o.write(']')

    def toJSON(self):
        return ['bpt', self.point, self.ctrl1, self.ctrl2]

    def fromJSON(obj):
        if obj[0] == 'bpt':
            goodLengthOrDie(obj, 4, '"bpt"')
            args = {}
            args['point'] = Point.fromJSON(obj[1])
            goodArgOrDie(args['point'], 1, '"bpt"', '"point: Point"')
            args['ctrl1'] = Point.fromJSON(obj[2])
            goodArgOrDie(args['ctrl1'], 2, '"bpt"', '"ctrl1: Point"')
            args['ctrl2'] = Point.fromJSON(obj[3])
            goodArgOrDie(args['ctrl2'], 3, '"bpt"', '"ctrl2: Point"')
            return BPoint(**args)
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Bspline(MaskShape, JSONizable):
    points: list[BPoint]

    def prettyJSON(self, o, level):
        o.write('["bspline"')
        for pt in self.points:
            o.write(',\n')
            pt.prettyJSON(o, level+1)
            comma = True
        indented(o, level, ']')

    def toJSON(self):
        points = ['bspline']
        for pt in self.points:
            points.append(pt.toJSON())

    def fromJSON(obj):
        if obj[0] == 'bspline':
            points = []
            for pt in obj[1:]:
                points.append(Point.fromJSON(pt))
            return Bspline(points=points)
        else:
            return None

# --------------------------------------------------------------------------------------------------

class Transform(JSONizable):
    def fromJSON(obj):
        return \
            Rotate.fromJSON(obj) or \
            Translate.fromJSON(obj) or \
            Scale.fromJSON(obj)

# --------------------------------------------------------------------------------------------------

@dataclass
class Rotate(Transform, JSONizable):
    angle: float

    def prettyJSON(self, o, level):
        o.write('["rotate",')
        self.offset.prettyJSON(o, level)
        o.write(']')

    def toJSON(self):
        return ["rotate", self.angle]

    def fromJSON(obj):
        if obj[0] == 'rotate':
            goodLengthOrDie(obj, 2, '"rotate"')
            angle = float(obj[1]) if isinstance(obj[1], float) else None
            goodArgOrDie(angle, 1, '"rotate"', '"angle: float"')
            return Rotate(angle=float(obj[1]))
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Translate(Transform, JSONizable):
    offset: Point

    def prettyJSON(self, o, level):
        o.write('["translate",')
        self.offset.prettyJSON(o, level)
        o.write(']')

    def toJSON(self):
        return ['transform', self.offset.toJSON()]

    def fromJSON(obj):
        if obj[0] == 'translate':
            goodLengthOrDie(obj, 2, '"translate"')
            offset = Point.fromJSON(obj[1])
            goodArgOrDie(offset, 1, '"translate"', '"offset: Point"')
            return Translate(offset=offset)
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Scale(Transform, JSONizable):
    offset: BoundArea

    def prettyJSON(self, o, level):
        o.write(f'["scale",')
        self.offset.prettyJSON(o, level)
        o.write(f']')

    def toJSON(self):
        return ['translate', self.offset.toJSON()]

    def fromJSON(obj):
        if obj[0] == 'scale':
            goodLengthOrDie(obj, 2, '"scale"')
            offset = BoundArea.fromJSON(obj[1])
            goodArgOrDie(offset, 1, '"scale"', '"offset: BoundArea"')
            return Scale(offset=offset)
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class ShapeGroup(MaskShape, JSONizable):
    transforms: list[Transform]
    shapes: list[MaskShape]
    name: str

    def prettyJSON(self, o, level):
        o.write('["group",{')
        self.prettyJSONName(o, level+1)
        self.prettyJSONContent(o, level+1, '"group"', False)
        indent(o, level, '}]')

    def prettyJSONName(self, o, level):
        o.write('"name":')
        dump(self.name, o)
        o.write(',\n')

    def prettyJSONContent(self, o, level, constrName, trailingComma):
        level1 = level+1
        indented(o, level1, '"transforms":')
        writeListJSON(o, level, self.transforms)
        o.write(',\n')
        indented(o, level1, '"shapes":')
        writeListJSON(o, level1, self.shapes)
        if trailingComma:
            o.write(',\n')
        else:
            o.write('\n')

    def toJSON(self):
        result = {}
        self.toJSONName(result)
        self.toJSONContent(result)
        return ['group', result]

    def toJSONName(self, result):
        if self.name:
            result['name'] = self.name
        else:
            pass

    def toJSONContent(self, result):
        transforms = []
        for t in self.transforms:
            transforms.append(t.toJSON())
        shapes = []
        for s in self.shapes:
            shapes.append(s.toJSON())
        result['transforms'] = transforms
        result['shapes'] = shapes

    def fromJSON(obj):
        if (obj[0] != 'group'):
            return None
        else:
            pass
        args = Group.fromJSONContent(obj[1], '"group"')
        return ShapeGroup(**args)

    def fromJSONContent(obj, constrName):
        if not \
           (('transforms' in obj) and \
            ('shapes' in obj) and \
            ((len(obj) == 2) or \
             ((len(obj) == 3) and \
              ('name' in obj)
              )
             )
            ):
            raise ValueError(
                'incorrect format for '
                f'{constrName}'
                ', require {"transforms", "shapes"}, optional {"name"}'
              )
        else:
            goodLengthOrDie(obj, 2, '"group"')
            name = obj['name'] if 'name' in obj else None
            transforms = []
            transformsJSON = obj['transforms']
            for (i,transJSON) in zip(range(0,len(transformsJSON)),transformsJSON):
                trans = Transform.fromJSON(transJSON)
                goodArgOrDie(
                    trans, f'"transforms"[{i}]', 'Transform',
                    '["translate", "rotate, "scale"]',
                  )
                transforms.append(trans)
            shapes = []
            shapesJSON = obj['shapes']
            for (i,shapeJSON) in zip(range(0,shapesJSON),shapesJSON):
                shape = Shape.fromJSON(shapeJSON)
                goodArgOrDie(
                    shape, f'"shapes"[{i}]', 'MaskShape',
                    '["rectangle", "circle", "ellipse", "polygon", "bspline", "group"]',
                  )
                shapes.append(shape)
            return {'transforms':transforms, 'shapes':shapes, 'name':name}

# --------------------------------------------------------------------------------------------------

@dataclass
class GuideObject(JSONizable):
    def fromJSON(obj):
        return \
            GuidePoint.fromJSON(obj) or \
            GuileLine.fromJSON(obj) or \
            GuideHorizontal.fromJSON(obj) or \
            GuideVertical.fromJSON(obj)

# --------------------------------------------------------------------------------------------------

@dataclass
class GuidePoint(GuideObject, JSONizable):
    point: Point

    def prettyJSON(self, o, level):
        o.write('["guide-point",')
        self.point.prettyJSON(o, level)
        o.write(']')

    def toJSON(self):
        return ['guidepoint', self.point.toJSON()]

    def fromJSON(obj):
        if obj[0] == 'guidepoint':
            goodLengthOrDie(obj, 2, '"guidepoint"')
            point = Point.fromJSON(obj[1])
            goodArgOrDie(point, 1, '"guidepoint"', '"point: Point"')
            return GuidePoint(point=point)
        else:
            return None

# --------------------------------------------------------------------------------------------------

class GuideLine(GuideObject, JSONizable):
    a: Point
    b: Point

    def prettyJSON(self, o, level):
        o.write('["guideline",{"a":')
        a.prettyJSON(o, level)
        o.write(',"b":')
        b.prettyJSON(o, level)
        o.write('}]')

    def toJSON(self):
        return ['guideline', self.a.toJSON(), self.b.toJSON()]

    def fromJSON(obj):
        if obj[0] == 'guideline':
            goodLengthOrDie(obj, 3, '"guideline"')
            args = {}
            args['a'] = Point.fromJSON(obj[1])
            goodArgOrDie(args['a'], 1, '"guideline"', '"a: Point"')
            args['b'] = Point.fromJSON(obj[2])
            goodArgOrDie(args['b'], 1, '"guideline"', '"b: Point"')
            return GuideLine(**args)

# --------------------------------------------------------------------------------------------------

class GuideHorizontal(GuideObject, JSONizable):
    x: float

    def prettyJSON(self, o, level):
        o.write(f'["horizontal",{self.x}]')

    def toJSON(self):
        return ['horizontal', self.x]

    def fromJSON(obj):
        if obj[0] == 'horizontal':
            goodLengthOrDie(obj, 2, '"horizontal"')
            x = numFromJSON(obj[1])
            goodArgOrDie(x, 1, '"horizontal"', '"x: float"')
            return GuideHorizontal(x=float(x))
        else:
            return None

class GuideVertical(GuideObject, JSONizable):
    y: float

    def prettyJSON(self, o, level):
        o.write(f'["vertical",{self.y}]')

    def toJSON(self):
        return ['vertical', self.x]

    def fromJSON(obj):
        if obj[0] == 'vertical':
            y = numFromJSON(obj[1])
            goodArgOrDie(y, 1, '"vertical"', '"y: float"')
            return GuideVertical(y=float(y))
        else:
            return None

class BlitOp(JSONizable):
    def fromJSON(obj):
        return \
            Fill.fromJSON(obj) or \
            Stroke.fromJSON(obj)

class StrokeJoin(JSONizable):
    def fromJSON(obj):
        return \
            RoundJoin.fromJSON(obj) or \
            MiterJoin.fromJSON(obj)

class RoundJoin(StrokeJoin, JSONizable):
    def prettyJSON(self, o, level):
        o.write('"round"')

    def toJSON(self):
        return 'round'

    def fromJSON(obj):
        return RoundJoin() if obj == 'round' else None

class MiterJoin(StrokeJoin, JSONizable):
    def prettyJSON(self, o, level):
        o.write( '"miter"')

    def toJSON(self):
        return 'miter'

    def fromJSON(obj):
        return MiterJoin() if obj == 'miter' else None

class Fill(BlitOp, JSONizable):
    def prettyJSON(self, o, level):
        o.write('"fill"')

    def toJSON(self):
        return 'fill'

    def fromJSON(obj):
        if obj == 'fill':
            return Fill()

@dataclass
class Stroke(BlitOp, JSONizable):
    lineWidth: float
    joinStyle: StrokeJoin

    def prettyJSON(self, o: TextIO, level: int):
        indented(o, level, f'["stroke",{self.lineWidth},')
        self.joinStyle.prettyJSON(o, level)
        indented(o, level, f']')

    def toJSON(self):
        return ['stroke', self.lineWidth.toJSON(), self.joinStyle.toJSON()]

    def fromJSON(obj):
        if obj[0] == 'stroke':
            goodLengthOrDie(args, 3, '"stroke"')
            args = {}
            args['lineWidth'] = numFromJSON(obj[1])
            goodArgOrDie(args['lineWidth'], 1, '"stroke"', '"lineWidth: float"')
            args['joinStyle'] = StrokeJoin.fromJSON(obj[2])
            goodArgOrDie(args['joinStyle'], 2, '"stroke"', '"joinStyle: StrokeJoin"')
            return Stroke(**args)
        else:
            return None

@dataclass
class ImageMask(ShapeGroup):
    blitOp: BlitOp
    color: bool
    name: str

    def prettyJSON(self, o: TextIO, level: int):
        indented(o, level, '["mask",')
        level1 = level+1
        self.blitOp.prettyJSON(o, level1)
        o.write(',')
        inlineBool(self.color, o, level1)
        o.write(',\n')
        indented(o, level1, '{')
        self.prettyJSONName(o, level1)
        self.prettyJSONContent(o, level1, '"mask"', False)
        indented(o, level1, '}]')

    def toJSON(self):
        result = {}
        self.toJSONName(result)
        self.toJSONContent(result)
        return ['mask', self.blitOp.toJSON(), self.color, result]

    def fromJSON(obj):
        if obj[0] == 'mask':
            goodLengthOrDie(obj, 2, '"mask"')
            content = ShapeGroup.fromJSONContent('"mask"')
            return ['mask', content]
        else:
            return None

class ImageMaskJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ShapeGroup):
            obj.toJSON()
        else:
            super(ImageMaskJSONEncoder, self).default(obj)

class ImageMaskJSONDecoder(JSONDecoder):
    def __init__(self, **inargs):
        kwargs = {'object_hook': ImageMask.fromJSON}
        kwargs.update(inargs)
        super(ImageMaskJSONDecoder, self).__init__(**kwargs)
