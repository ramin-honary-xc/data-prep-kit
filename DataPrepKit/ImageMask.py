from typing import Union, Optional, Callable, TextIO
from abc import ABC, abstractmethod
from dataclasses import dataclass
from json import JSONEncoder, JSONDecoder, loads, dump
import io

# ==================================================================================================
# These functions might be better off in a more general-purpose JSON parsing library.

@dataclass
class PrettyJSONError(Exception):
    message: Optional[str] = None
    inputObject: Optional[object] = None

    def __repr__(self):
        return \
          ( (self.message if self.message else '') +
            (repr(self.inputObject) if self.inputObject else '')
          )

@dataclass
class FromJSONError(Exception):
    message: Optional[str] = None
    decoderClass: Optional[str] = None
    inputJSON: Optional[object] = None
    inputNumArgs: Optional[int] = None
    expectedNumArgs: Optional[int] = None
    expectedFields: Optional[list[str]] = None
    inputIndex: Optional[int|str] = None
    expectedType: Optional[str] = None

    def __repr__(self):
        return \
          ( (f'{self.message}\n' if self.message else '') +
            (f'decoding {self.decoderClass}\n' if self.decoderClass else '') +
            (f'decoding input: {self.inputJSON}\n' if self.inputJSON else '') +
            (f'number of input arguments: {self.inputNumArgs}\n'
             if self.inputNumArgs else ''
             ) +
            (f'expected number of arguments: {self.expectedNumArgs}\n'
             if self.expectedNumArgs else ''
             ) +
            (f'expected fields: {self.expectedFields}\n'
             if self.expectedFields else ''
             )
          )

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

def assertArgCount(args: list|dict, expected: int, constrName: str) -> None:
    if len(args) != expected:
        raise FromJSONError(
            message='incorrect number of arguments',
            decoderClass=constrName,
            inputJSON=args,
            inputNumArgs=len(args),
            expectedNumArgs=expected,
          )
    else:
        pass

def decode(obj: list|dict, idx: int|str, decoder: Callable, constrName: str, expected: str) -> Optional[object]:
    """Runs a decoder on an argument and throws an exception if the
    decoder returns None."""
    arg = None
    if isinstance(idx, int):
        if not isinstance(obj, list):
            raise FromJSONError(
                expectedType='list',
                inputJSON=obj,
              )
        else:
            arg = obj[idx]
    elif isinstance(idx, str):
        if not isinstance(obj, dict):
            raise FromJSONError(
                expectedType='dict',
                inputJSON=obj
              )
        else:
            arg = obj[idx]
    else:
        raise FromJSONError(
            expectedType=('list' if isinstance(idx, int) else 'dict'),
            inputJSON=obj,
          )
    if arg is None:
        return None
    else:
        return decoder(arg)

def require(obj: list|dict, idx: int|str, decoder: Callable, constrName: str, expected: str) -> object:
    """Similar to decode, but throws an exception if the decoder returns None"""
    decoded = decode(obj, idx, decoder, constrName, expected)
    if decoded is None:
        raise \
          FromJSONError(
              message='JSON object format error',
              decoderClass=constrName,
              expectedType=expected,
              inputIndex=idx,
              inputJSON=obj,
            )
    else:
        return decoded

# --------------------------------------------------------------------------------------------------

JSONLikeType = None | bool | int | float | str | list | dict

@dataclass
class JSONizable():
    """Abstract class declaring the functions that the various @dataclass
    nodes must implement in order to be read or written as JSON data.

    NOTE: this class cannot actually contain any methods methods
    decorated with @abstractmethod because of a bug in the MyPy
    typechecker in which types of a child class of an abstract class
    are not recognized as types of the abstract class. Making any part
    of this class abstract causes MyPy to throw the error: "Only
    concrete class can be given where "Type[JSONizable]" is expected"

    https://github.com/python/mypy/issues/5374

    """

    def prettyJSON(self, o: TextIO, level: int) -> None:
        """The JSON produced in this module might frequently be directly
        edited by people as well as computer programs, so a custom
        pretty printer is defined that outputs JSON that is easier for
        people to read.
        """
        raise Exception('call on abstract method JSONizable.prettyJSON')

    def toJSON(self) -> JSONLikeType:
        """Any child class of JSONizable (lets suppose there is such a child
        class called "JO") should override this "toJSON()" method to
        produce a JSON-like Python object. The JSON-like object
        constructed by "JO.toJSON()" should have the following
        properties:

          - be able to be converted to a JSON-formatted string using
            "json.dump()"

          - should also be converted back into the JSONizable object
            by calling "JO.fromJSON()" on the output of "JO.toJSON()".
        """
        raise Exception('call on abstract method JSONizable.toJSON')

    @staticmethod
    def fromJSON(obj: JSONLikeType):
        """A static function (called as "JSONizable.fromJSON()") which takes a
        Python object of some kind and tries to convert it to an
        object of whatever class has inherited this method from
        JSONizable. The object given to this function was presumably
        recieved from the result of calling "json.load()". If you want
        to decode a string use "JSONizable.parseJSON()" instead.
        """
        raise Exception('call on abstract method JSONizable.fromJSON')

    @staticmethod
    def parseJSON(i: TextIO):
        """This function parses a JSON object then passes the result to
        fromJSON. This function must be overridden so as to call the
        correct fromJSON() method. It might be easiest to simply use
        the defaultParseJSON() function to override this method.
        """
        raise Exception('call on abstract method JSONizable.parseJSON')

def defaultParseJSON(i: TextIO, c: type[JSONizable]):
    return c.parseJSON(i)

# --------------------------------------------------------------------------------------------------

def stringTooLong(offset, s):
    return (offset + len(result) > 80 or result.find('\n') >= 0)

def inlineJSON(o: TextIO, level: int, obj: object) -> None:
    if isinstance(obj, JSONizable):
        obj.prettyJSON(o, level)
    elif isinstance(obj, list):
        prettyListJSON(o, level, obj)
    elif isinstance(obj, dict):
        prettyDictJSON(o, level, obj)
    elif not obj or \
      isinstance(obj, bool)  or \
      isinstance(obj, int)   or \
      isinstance(obj, float) or \
      isinstance(obj, str):
        dump(obj, o)
    else:
        raise PrettyJSONError(
            message=f'no rules for pretty-printing objects of type {type(obj)}',
            inputObject=obj,
          )

def prettyDictJSON(o: TextIO, level: int, items: dict[str, object]) -> None:
    itemslen = len(items)
    if itemslen == 0:
        o.write('{}')
    else:
        level1 = level+1
        i = 0
        top = itemslen - 1
        o.write('\n')
        for (k,v) in items: #type: ignore
            buf = io.StringIO()
            dump(k, buf) #type: ignore
            buf.write(':')
            klen = buf.tell()
            inlineJSON(buf, level1, v) #type: ignore
            result = buf.getvalue()
            buf.close()
            if stringTooLong(0, result):
                if i == 0:
                    indented(o, level, '{')
                    o.write(result[0:klen])
                else:
                    indented(o, level1, kstr[0:klen]) #type: ignore
                o.write('\n')
                indented(o, level1+1, result[klen:])
            else:
                if i == 0:
                    indented(o, level, '{')
                    o.write(result)
                else:
                    indented(o, level1, result)
            if i >= top:
                if i == 1:
                    o.write('}')
                else:
                    o.write('\n')
                    indented(o, level, '}')
            else:
                o.write(',\n')

def prettyListJSON(o: TextIO, level: int, items: list[object]) -> None:
    """Can be inlined or indented depending on how many items there are."""
    itemslen = len(items)
    if itemslen == 0:
        o.write('[]')
    elif itemslen == 1:
        o.write('[')
        tempbuf = io.StringIO()
        inlineJSON(o, level+1, items[0])
        result = tempbuf.getvalue()
        if stringTooLong(0, result):
            o.write('\n')
            indented(o, level+1, result)
        else:
            o.write(result)
        o.write(']')
    else:
        o.write('\n')
        level1 = level+1
        indented(o, level, '[')
        inlineJSON(o, level1, items[0])
        for item in items[1:]:
            o.write(',\n')
            indented(o, level1, '')
            inlineJSON(o, level1, item)
        o.write('\n')
        indented(o, level, ']')

# ==================================================================================================
# Here begins the definitions of the various nodes that define the
# structure of an ImageMask drawing.

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

    @staticmethod
    def getSymbols():
        return {
            Rectangle.symbol: Rectangle,
            Circle.symbol: Circle,
            Ellipse.symbol: Ellipse,
            Polygon.symbol: Polygon,
            BSpline.symbol: BSpline,
            ShapeGroup.symbol: ShapeGroup,
          }

    def fromJSON(obj):
        if isinstance(obj,list) and len(obj) > 1:
            return MaskShape.getSymbols()[obj[0]].fromJSON(obj)
        else:
            return None

    @staticmethod
    def parseJSON(i: TextIO):
        return defaultParseJSON(i, MaskShape)

# --------------------------------------------------------------------------------------------------

@dataclass
class Point(JSONizable):
    x: float
    y: float

    def prettyJSON(self, o, level):
        o.write('{"x":')
        dump(self.x, o)
        o.write(',"y":')
        dump(self.y, o)
        o.write('}')

    def toJSON(self):
        return {'x': self.x, 'y': self.y}

    def fromJSON(obj):
        if ('x' in obj) and ('y' in obj):
            assertArgCount(obj, 2, '"Point"')
            x = require(obj, 'x', numFromJSON, 'Point', 'number')
            y = require(obj, 'y', numFromJSON, 'Point', 'number')
            return Point(x=float(x), y=float(y))
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class BoundArea(JSONizable):
    width: float
    height: float

    def prettyJSON(self, o, level):
        o.write('{"width":')
        dump(self.width, o)
        o.write(',"height":')
        dump(self.height, o)
        o.write('}')

    def toJSON(self):
        return {'width': self.width, 'height': self.height}

    def fromJSON(obj):
        if ('width' in obj) and ('height' in obj):
            assertArgCount(obj, 2, 'BoundArea')
            width  = require(obj, 'width',  numFromJSON, 'BoundArea', 'number')
            height = require(obj, 'height', numFromJSON, 'BoundArea', 'number')
            return BoundArea(width=float(width), height=float(height))
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Rectangle(MaskShape, JSONizable):
    origin: Point
    bounds: BoundArea
    visible: bool = True

    symbol = 'rectangle'

    def prettyJSON(self, o, level):
        o.write(f'["{Rectangle.symbol}",')
        self.origin.prettyJSON(o, level)
        o.write(',')
        self.bounds.prettyJSON(o, level)
        o.write(',')
        inlineJSON(o, level, self.visible)
        o.write(']')

    def toJSON(self):
        return [Rectangle.symbol, self.origin.toJSON(), self.bounds.toJSON(), self.visible]

    def fromJSON(obj):
        if obj[0] == Rectangle.symbol:
            assertArgCount(obj, 4, Rectangle.symbol)
            return Rectangle(
                origin  = require(obj, 1, Point.fromJSON,     f'"{Rectangle.symbol}"', 'Point'),
                bounds  = require(obj, 2, BoundArea.fromJSON, f'"{Rectangle.symbol}"', 'BoundArea'),
                visible = require(obj, 3, bool,               f'"{Rectangle.symbol}"', 'bool'),
              )
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Circle(MaskShape, JSONizable):
    origin: Point
    radius: float
    startAngle: Optional[float] = None
    endAngle: Optional[float] = None
    visible: bool = True

    symbol = 'circle'

    def prettyJSON(self, o, level):
        level1 = level+1
        o.write(f'["{Circle.symbol}",')
        self.origin.prettyJSON(o, level1)
        o.write(',')
        inlineJSON(o, level1, self.radius)
        o.write(',')
        inlineJSON(o, level1, self.startAngle)
        o.write(',')
        inlineJSON(o, level1, self.endAngle)
        o.write(',')
        inlineJSON(o, level1, self.visible)
        o.write(']')

    def toJSON(self):
        return (
            [ Circle.symbol,
              self.origin.toJSON(),
              self.radius,
              self.startAngle,
              self.endAngle,
              self.visible,
            ])

    def fromJSON(obj):
        if obj[0] == Circle.symbol:
            assertArgCount(obj, 6, f'"{Circle.symbol}"')
            return Circle(
                origin = require(obj, 1, Point.fromJSON, f'"{Circle.symbol}"', 'origin: Point'),
                radius = require(obj, 2, numFromJSON   , f'"{Circle.symbol}"', 'radius: number')
              )
            args = {}
            args['point'] = (obj[1])
            return Circle(
                origin     = require(obj, 1, Point.fromJSON, f'"{Circle.symbol}"', 'origin: Point'),
                radius     = require(obj, 2, numFromJSON,    f'"{Circle.symbol}"', 'radius: float'),
                startAngle =  decode(obj, 3, numFromJSON,    f'"{Circle.symbol}"', 'startAngle: float'),
                endAngle   =  decode(obj, 4, numFromJSON,    f'"{Circle.symbol}"', 'endAngle: float'),
                visible    = require(obj, 5, bool,           f'"{Circle.symbol}"', 'visible: bool')
              )
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Ellipse(MaskShape, JSONizable):
    origin: Point
    bounds: BoundArea
    visible: bool = True

    symbol = 'Ellipse'

    def prettyJSON(self, o, level):
        o.write(f'["{Ellipse.symbol}",')
        self.origin.prettyJSON(o, level)
        o.write(',')
        self.bounds.prettyJSON(o, level)
        o.write(',')
        inlineJSON(o, level, self.visible)
        o.write(']')

    def toJSON(self):
        return (
            [ Ellipse.symbol,
              self.origin.toJSON(),
              self.bounds.toJSON(),
              self.visible,
            ])

    def fromJSON(obj):
        if obj[0] == Ellipse.symbol:
            assertArgCount(obj, 4, f'"{Ellipse.symbol}"')
            return Ellipse(
                origin  = require(obj, 1, Point.fromJSON    , f'"{Ellipse.symbol}"', 'origin: Point'),
                bounds  = require(obj, 2, BoundArea.fromJSON, f'"{Ellipse.symbol}"', 'bounds: BoundArea'),
                visible = require(obj, 3, bool,               f'"{Ellipse.symbol}"', 'visible: bool'),
              )
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Polygon(MaskShape, JSONizable):
    points: list[Point]

    symbol = 'polygon'

    def prettyJSON(self, o, level):
        o.write(f'["{Polygon.symbol}"')
        i = 0
        for p in self.points:
            if not isinstance(p, Point):
                raise ValueError(f'polygon object contains non-point at index {i}')
            else:
                i += 1
                o.write(',\n')
                p.prettyJSON(o, level+1)
        indented(o, level, ']')

    def toJSON(self):
        result = [Polygon.symbol]
        for pt in self.points:
            result.append(pt.toJSON())
        return result

    def fromJSON(obj):
        if obj[0] == Polygon.symbol:
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
        o.write('{"point":')
        self.point.prettyJSON(o, level+1)
        o.write(',"ctrl1":')
        self.ctrl1.prettyJSON(o, level+1)
        o.write(',"ctrl2":')
        self.ctrl2.prettyJSON(o, level+1)
        o.write('}')

    def toJSON(self):
        return {'point': self.point, 'ctrl1': self.ctrl1, 'ctrl2': self.ctrl2}

    def fromJSON(obj):
        if ('point' in obj) and ('ctrl1' in obj) and ('ctrl2' in obj):
            assertArgCount(obj, 4, '"bpt"')
            point = require(obj, 'point', Point, 'BPoint', 'Point')
            ctrl1 = require(obj, 'ctrl1', Point, 'BPoint', 'Point')
            ctrl2 = require(obj, 'ctrl2', Point, 'BPoint', 'Point')
            return BPoint(point=point, ctrl1=ctrl1, ctrl2=ctrl2)
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class BSpline(MaskShape, JSONizable):
    points: list[BPoint]

    symbol = 'bspline'

    def prettyJSON(self, o, level):
        o.write(f'["{BSpline.symbol}"')
        i = 0
        for pt in self.points:
            if not isinstance(pt, BPoint):
                raise ValueError(f'BSpline contains non-BPoint value at index {i}')
            else:
                i += 1
                o.write(',\n')
                pt.prettyJSON(o, level+1)
                comma = True
        indented(o, level, ']')

    def toJSON(self):
        points = [BSpline.symbol]
        for pt in self.points:
            points.append(pt.toJSON())

    def fromJSON(obj):
        if obj[0] == BSpline.symbol:
            points = []
            for pt in obj[1:]:
                points.append(Point.fromJSON(pt))
            return BSpline(points=points)
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
        dump(self.angle, o)
        o.write(']')

    def toJSON(self):
        return ["rotate", self.angle]

    def fromJSON(obj):
        if obj[0] == 'rotate':
            assertArgCount(obj, 2, '"rotate"')
            return Rotate(
                angle = require(obj, 2, numFromJSON, '"rotate"', 'angle: float'),
              )
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
            assertArgCount(obj, 2, '"translate"')
            return Translate(
                offset = require(),
              )
            offset = Point.fromJSON(obj[1])
            require(offset, 1, '"translate"', 'offset: Point')
            return Translate(offset=offset)
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class Scale(Transform, JSONizable):
    scale: BoundArea

    def prettyJSON(self, o, level):
        o.write(f'["scale",')
        self.scale.prettyJSON(o, level)
        o.write(f']')

    def toJSON(self):
        return ['translate', self.scale.toJSON()]

    def fromJSON(obj):
        if obj[0] == 'scale':
            assertArgCount(obj, 2, '"scale"')
            return Scale(
                scale = require(obj, 1, numFromJSON, '"scale"', 'scale: BoundArea')
              )
        else:
            return None

# --------------------------------------------------------------------------------------------------

@dataclass
class ShapeGroup(MaskShape, JSONizable):
    name: str
    transforms: list[Transform]
    shapes: list[MaskShape]

    symbol = 'group'

    def prettyJSON(self, o, level):
        o.write(f'["{ShapeGroup.symbol}",''{')
        self.prettyJSONName(o, level+1)
        self.prettyJSONContent(o, level+1, f'"{ShapeGroup.symbol}"', False)
        indent(o, level, '}]')

    def prettyJSONName(self, o, level):
        if self.name:
            o.write('"name":')
            dump(self.name, o)
            o.write(',\n')
        else:
            pass

    def prettyJSONContent(self, o, level, constrName, trailingComma):
        indented(o, level+1, '"transforms":')
        prettyListJSON(o, level+2, self.transforms)
        o.write(',\n')
        indented(o, level+1, '"shapes":')
        prettyListJSON(o, level+2, self.shapes)
        if trailingComma:
            o.write(',\n')
        else:
            o.write('\n')

    def toJSON(self):
        result = {}
        self.toJSONName(result)
        self.toJSONContent(result)
        return [ShapeGroup.symbol, result]

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
        if (obj[0] != ShapeGroup.symbol):
            return None
        else:
            pass
        return Group.fromJSONContent(obj[1], f'"{ShapeGroup.symbol}"')

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
            raise FromJSONError(
                message=f'invalid properties for "{ShapeGroup.symbol}" constructor\n',
                inputJSON=obj,
                expectedFields=['"name" (optional)', '"transforms"', '"shapes"']
              )
        else:
            name = obj['name'] if 'name' in obj else None
            transforms = []
            transformsJSON = obj['transforms']
            for i in range(0,len(transformsJSON)):
                trans = require(trans, i, Transform.fromJSON, 'Transform', f'{ShapeGroup.symbol}')
                transforms.append(trans)
            shapes = []
            shapesJSON = obj['shapes']
            for i in range(0,len(shapesJSON)):
                shape = require(shapesJSON, i, MaskShape.fromJSON, 'MaskShape', f'{ShapeGroup.symbol}')
                if not shape:
                    raise FromJSONError(
                        message='not a valid shape object',
                        inputJSON=shapeJSON,
                        inputIndex=i,
                        decoderClass=f'["{ShapeGroup.symbol}"]["shapes"]',
                      )
                shapes.append(shape)
            return ShapeGroup(name=name, transforms=transforms, shapes=shapes)

# --------------------------------------------------------------------------------------------------

@dataclass
class GuideObject(JSONizable):
    def fromJSON(obj):
        return (
            GuidePoint.fromJSON(obj) or \
            GuileLine.fromJSON(obj) or \
            GuideHorizontal.fromJSON(obj) or \
            GuideVertical.fromJSON(obj)
          )

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
            assertArgCount(obj, 2, '"guidepoint"')
            return GuidePoint(
                point=require(obj, 1, Point.fromJSON, '"guide-point"', 'Point'),
              )
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
            assertArgCount(obj, 3, '"guideline"')
            return GuideLine(
                a = require(obj, 'a', Point.fromJSON, '"guideline"', 'a: Point'),
                b = require(obj, 'b', Point.fromJSON, '"guideline"', 'b: Point'),
              )
        else:
            return None

# --------------------------------------------------------------------------------------------------

class GuideHorizontal(GuideObject, JSONizable):
    x: float

    def prettyJSON(self, o, level):
        o.write('["horizontal",')
        dump(self.x, o)
        o.write(']')

    def toJSON(self):
        return ['horizontal', self.x]

    def fromJSON(obj):
        if obj[0] == 'horizontal':
            assertArgCount(obj, 2, '"horizontal"')
            return GuideHorizontal(
                require(obj, 1, numFromJSON, '"horizontal"', 'x: number'),
              )
        else:
            return None

class GuideVertical(GuideObject, JSONizable):
    y: float

    def prettyJSON(self, o, level):
        o.write('["vertical",')
        dump(self.y, o)
        o.write(']')

    def toJSON(self):
        return ['vertical', self.x]

    def fromJSON(obj):
        if obj[0] == 'vertical':
            return GuideVertical(
                y = require(obj, 1, numFromJSON, '"vertical"', 'y: float'),
              )
        else:
            return None

class BlitOp(JSONizable):
    def fromJSON(obj):
        return (
            Fill.fromJSON(obj) or \
            Stroke.fromJSON(obj)
          )

class StrokeJoin(JSONizable):
    def fromJSON(obj):
        return (
            RoundJoin.fromJSON(obj) or \
            MiterJoin.fromJSON(obj)
          )

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

    symbol = 'stroke'

    def prettyJSON(self, o: TextIO, level: int):
        indented(o, level, '["stroke",')
        dump(self.lineWidth, o)
        o.write(',')
        self.joinStyle.prettyJSON(o, level)
        indented(o, level, ']')

    def toJSON(self):
        return [Stroke.symbol, self.lineWidth.toJSON(), self.joinStyle.toJSON()]

    def fromJSON(obj):
        if obj[0] == Stroke.symbol:
            assertArgCount(args, 3, '"stroke"')
            return Stroke(
                lineWidth = require(obj, 1, numFromJSON,         '"stroke"', 'lineWidth: float'),
                joinStyle = require(obj, 2, StrokeJoin.fromJSON, '"stroke"', 'joinStyle: StrokeJoin'),
              )
        else:
            return None

@dataclass
class ImageMask(ShapeGroup):
    blitOp: BlitOp
    color: bool

    def prettyJSON(self, o: TextIO, level: int):
        indented(o, level, '["mask",')
        level1 = level+1
        self.blitOp.prettyJSON(o, level1)
        o.write(',')
        dump(self.color, o)
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
        if not isinstance(obj, list):
            raise ValueError(f'ImageMask.fromJSON() expects list argument (got {type(obj)})')
        elif obj[0] == 'mask':
            assertArgCount(obj, 4, '"mask"')
            blitOp = require(obj, 1, BlitOp.fromJSON, '"mask"', 'BlitOp')
            color  = require(obj, 2, bool,            '"mask"', 'color: bool')
            group  = ShapeGroup.fromJSONContent(obj[3], '"mask"')
            return ImageMask(
                blitOp     = blitOp,
                color      = color,
                name       = group.name,
                transforms = group.transforms,
                shapes     = group.shapes,
              )
        else:
            return None

    def parseJSON(i):
        return defaultParseJSON(i, ImageMask)
