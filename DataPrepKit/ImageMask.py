from dataclasses import dataclass
from json import JSONEncoder, JSONDecoder

class MaskShape():
    """This is a value used to create shapes that mask or unmask bits in a
    bitmap image. Note the naming convention I am using here: "black"
    means opaque (masked), white is transparent (unmasked).

    The GUI for this model places a black layer over an image, and the
    end user subtracts spaces from this black layer. So masking adds
    black back to the layer, unmasking removes black (makes it
    transparent).
    """
    visible: bool = True

@dataclass
class Point(MaskShape):
    x: float
    y: float

@dataclass
class Rectangle(MaskShape):
    point: Point
    width: float
    height: float
    visible: bool = True

@dataclass
class Circle(MaskShape):
    point: Point
    radius: float
    startAngle: float = None
    endAngle: float = None
    visible: True

@dataclass
class Elipse(MaskShape):
    point: Point
    width: float
    height: float
    visible: True

@dataclass
class Polygon(MaskShape):
    points: list[Point]

@dataclass
class BPoint(MaskShape):
    point: Point
    ctrl1: Point
    ctrl2: Point

@dataclass
class Bspline(MaskShape):
    points: list[BPoint]

class Transform():
    pass

@dataclass
class Rotate(Transform):
    angle: float

@dataclass
class Translate(Transform):
    offset: Point

@dataclass
class Scale(Transform):
    offset: Point

@dataclass
class ShapeGroup(MaskShape):
    transforms: list[Transform]
    shapes: list[MaskShape]
    name: str

@dataclass
class GuideObject():
    pass

@dataclass
class GuidePoint(GuideObject):
    point: Point

class GuideLine(GuideObject):
    a: Point
    b: Point

class GuideHorizontal(GuideObject):
    x: float

class GuideVertical(GuideObject):
    y: float

class BlitOp:
    pass

@dataclass
class Fill(BlitOp):
    pass

class StrokeJoin():
    pass

@dataclass
class RoundJoin(StrokeJoin):
    pass

class MiterJoin(StrokeJoin):
    pass

@dataclass
class Stroke(BlitOp):
    lineWidth: float
    joinStyle: StrokeJoin

@dataclass
class ImageMask(ShapeGroup):
    blitOp: BlitOp
    color: bool
    name: str = None
