import PyQt5.QtGui as qgui #import QPixmap, QImage
import PyQt5.QtCore as qcore

import numpy as np

def numpy_array_to_QPixmap(array):
    """This function does the impedance matching between the in-memory
    data format of NumPy arrays to the image format used by
    QPixmap(). """
    d = qgui.QPixmap.defaultDepth()
    print(f'numpy_array_to_QPixmap() #(shape: {array.shape}, depth: {d})')
    if (len(array.shape) == 3) and (array.shape[2] == 3):
        # This is most likely an RGB color image
        (h, w, channels) = array.shape
        image = qgui.QImage(array.data, w, h, w*channels, qgui.QImage.Format_RGB888)
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
