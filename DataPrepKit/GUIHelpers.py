import PyQt5.QtGui as qgui #import QPixmap, QImage
import PyQt5.QtCore as qcore

import numpy as np

def numpy_array_to_QPixmap(array):
    """This function does the impedance matching between the in-memory
    data format of NumPy arrays to the image format used by
    QPixmap(). Unforuntately, the array usually has to be copied twice
    to do the conversion, first to transpose the image from
    column-major to row-major order, and then again to construct an
    image of the same pixel format as the graphics device of the
    widget (which is usually 32-bit ARGB).

    """
    d = qgui.QPixmap.defaultDepth()
    print(f'numpy_array_to_QPixmap() #(shape: {array.shape}, depth: {d})')
    if (len(array.shape) == 3) and (array.shape[2] == 3):
        # This is most likely an RGB color image
        #array = np.transpose(array, (1, 0, 2)).copy()
        (w, h, channels) = array.shape
        image = qgui.QImage(array, w, h, w*channels, qgui.QImage.Format_RGB888)
        pixmap = qgui.QPixmap(w, h)
        pixmap.convertFromImage(image, flags=qcore.Qt.ImageConversionFlag.ColorOnly)
        return pixmap
    elif len(array.shape) == 2:
        # This is most likely a grayscale image
        #array = np.transpose(array, (1, 0)).copy()
        (w, h) = array.shape
        image = qgui.QImage(array, w, h, w, qgui.QImage.Format_Grayscale8)
        pixmap = qgui.QPixmap(w, h)
        pixmap.convertFromImage(image, flags=qcore.Qt.ImageConversionFlag.ColorOnly)
        return pixmap
    else:
        raise ValueError(f'numpy_array_to_QPixmap: unexpected array shape {array.shape}', array)
