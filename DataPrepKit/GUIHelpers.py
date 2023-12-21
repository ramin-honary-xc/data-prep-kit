import copy
import numpy as np

import PyQt5.QtGui as qgui #import QPixmap, QImage
import PyQt5.QtCore as qcore

####################################################################################################

def QRectF_to_tuple(qrectf):
    return (qrectf.x(), qrectf.y(), qrectf.width(), qrectf.height(),)

def QGraphicsRectItem_to_tuple(item):
    if isinstance(item, qgui.QGraphicsRectItem):
        return QRectF_to_tuple(item.rect())
    elif isinstance(item, qcore.QRectF):
        return QRectF_to_tuple(item)
    else:
        raise ValueError('value of unexpected type {type(item)}', item)

####################################################################################################

qt_image_format_assocs = \
  [ (qgui.QImage.Format_Invalid, 'Invalid'),
    (qgui.QImage.Format_Mono, 'Mono'),
    (qgui.QImage.Format_MonoLSB, 'MonoLSB'),
    (qgui.QImage.Format_Indexed8, 'Indexed8'),
    (qgui.QImage.Format_RGB32, 'RGB32'),
    (qgui.QImage.Format_ARGB32, 'ARGB32'),
    (qgui.QImage.Format_ARGB32_Premultiplied, 'ARGB32_Premultiplied'),
    (qgui.QImage.Format_RGB16, 'RGB16'),
    (qgui.QImage.Format_ARGB8565_Premultiplied, 'ARGB8565_Premultiplied'),
    (qgui.QImage.Format_RGB666, 'RGB666'),
    (qgui.QImage.Format_ARGB6666_Premultiplied, 'ARGB6666_Premultiplied'),
    (qgui.QImage.Format_RGB555, 'RGB555'),
    (qgui.QImage.Format_ARGB8555_Premultiplied, 'ARGB8555_Premultiplied'),
    (qgui.QImage.Format_RGB888, 'RGB888'),
    (qgui.QImage.Format_RGB444, 'RGB444'),
    (qgui.QImage.Format_ARGB4444_Premultiplied, 'ARGB4444_Premultiplied'),
    (qgui.QImage.Format_RGBX8888, 'RGBX8888'),
    (qgui.QImage.Format_RGBA8888, 'RGBA8888'),
    (qgui.QImage.Format_RGBA8888_Premultiplied, 'RGBA8888_Premultiplied'),
    (qgui.QImage.Format_BGR30, 'BGR30'),
    (qgui.QImage.Format_A2BGR30_Premultiplied, 'A2BGR30_Premultiplied'),
    (qgui.QImage.Format_RGB30, 'RGB30'),
    (qgui.QImage.Format_A2RGB30_Premultiplied, 'A2RGB30_Premultiplied'),
    (qgui.QImage.Format_Alpha8, 'Alpha8'),
    (qgui.QImage.Format_Grayscale8, 'Grayscale8'),
    (qgui.QImage.Format_Grayscale16, 'Grayscale16'),
    (qgui.QImage.Format_RGBX64, 'RGBX64'),
    (qgui.QImage.Format_RGBA64, 'RGBA64'),
    (qgui.QImage.Format_RGBA64_Premultiplied, 'RGBA64_Premultiplied'),
    (qgui.QImage.Format_BGR888, 'BGR888'),
  ]

qt_image_format_labels = { enumval: label for (enumval, label) in qt_image_format_assocs }
qt_image_format_enums  = { label: enumval for (enumval, label) in qt_image_format_assocs }

####################################################################################################

def numpy_array_to_QPixmap(array):
    """This function does the impedance matching between the in-memory
    data format of NumPy arrays to the image format used by
    QPixmap(). """
    d = qgui.QPixmap.defaultDepth()
    #print(f'numpy_array_to_QPixmap() #(shape: {array.shape}, depth: {d})')
    if (len(array.shape) == 3) and (array.shape[2] == 3 or array.shape[2] == 4):
        # This is most likely an RGB color image
        (h, w, channels) = array.shape
        fmt = qgui.QImage.Format_RGB888 if channels == 3 else qgui.QImage.Format_RGB32
        image = qgui.QImage(array.data, w, h, w*channels, fmt)
        pixmap = qgui.QPixmap(w, h)
        pixmap.convertFromImage(image, flags=qcore.Qt.ImageConversionFlag.ColorOnly)
        return pixmap
    elif len(array.shape) == 2:
        # This is most likely a grayscale image
        (h, w) = array.shape
        image = qgui.QImage(array.data, w, h, w, qgui.QImage.Format_Grayscale8)
        pixmap = qgui.QPixmap(w, h)
        pixmap.convertFromImage(image, flags=qcore.Qt.ImageConversionFlag.ColorOnly)
        return pixmap
    else:
        raise ValueError(f'numpy_array_to_QPixmap: unexpected array shape {array.shape}', array)

def QPixmap_to_numpy_array(pixmap, do_copy=False):
    qimage    = pixmap.toImage()
    imgformat = qimage.format()
    size      = qimage.size()
    shape     = [int(size.height()), int(size.width())]
    channels  = qimage.depth() // 8 # np.uint8
    buffer    = qimage.constBits().asarray(qimage.height() * qimage.bytesPerLine())
    if (imgformat == qgui.QImage.Format_Grayscale8 or \
        imgformat == qgui.QImage.Format_Alpha8 or \
        imgformat == qgui.QImage.Format_RGB888 or \
        imgformat == qgui.QImage.Format_RGB32 or \
        imgformat == qgui.QImage.Format_ARGB32 or \
        imgformat == qgui.QImage.Format_ARGB32_Premultiplied):
        if channels > 1:
            shape.append(channels)
        else:
            pass
    else:
        raise ValueError(f'unsupported image format "{qt_image_format_labels[format]}"')
    print(f'QPixmap_to_numpy_array({pixmap}) #(construct numpy.ndarray(shape={shape}, dtype=np.uint8)')
    ndarray = np.ndarray(shape=tuple(shape), dtype=np.uint8, buffer=buffer)
    return (copy.deepcopy(ndarray) if do_copy else ndarray)

# NOTE: if OpenCV functions ever print errors of this form:
#
# cv2.error: OpenCV(4.7.0) :-1: error: (-5:Bad argument) in function 'resize'
# > Overload resolution failed:
# >  - Can't parse 'dsize'. Sequence item with index 0 has a wrong type
# >  - Can't parse 'dsize'. Sequence item with index 0 has a wrong type
# Aborted (core dumped)
# 
# It probably means you are passing non-integers (such as floats) to
# OpenCV arguments that require integer arguments.
