import PyQt5.QtCore as qcore
import PyQt5.QtGui as qgui
import PyQt5.QtWidgets as qt

#---------------------------------------------------------------------------------------------------

class PercentSlider(qt.QWidget):
    """This is a simple Qt Widget composed of 3 other widgets: a Label, a
    LineEdit text box, and a Slider. Dragging the slider changes the
    percentage value shown in the LineEdit box, changing the value in
    the LineEdit field sets the slider to the correct position. You
    can set a callback function that is called whenever the percentage
    value is changed.
    """

    def __init__(self, label, init_value, callback):
        super().__init__()
        self.init_value = init_value
        self.percent = init_value
        self.callback = callback
        self.label = qt.QLabel(label)
        self.slider = qt.QSlider(1, self)
        self.slider.setMinimum(500)
        self.slider.setMaximum(1000)
        self.slider.setPageStep(50)
        self.slider.setSingleStep(10)
        self.slider.setValue(round(self.percent * 1000.0))
        self.slider.setObjectName("InspectTab slider")
        self.slider.valueChanged.connect(self.value_changed_handler)
        self.setSizePolicy(self.slider.sizePolicy())
        self.textbox = qt.QLineEdit(str(round(self.percent * 1000.0) / 10.0), self)
        self.textbox.setMaxLength(5)
        self.textbox.setObjectName("InspectTab textbox")
        font_metrics = qt.QLabel("100.0 %").fontMetrics()
        self.textbox.setFixedWidth(font_metrics.width("100.0 %"))
        self.textbox.editingFinished.connect(self.textbox_handler)
        #---------- The top bar is always visible ----------
        self.layout = qt.QHBoxLayout(self)
        self.layout.setObjectName("InspectTab layout")
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.textbox)
        self.layout.addWidget(self.slider)

    def reset_to_init_value(self):
        self.value_changed_handler(self.init_value)

    def get_percent(self):
        """Return the value of the percentage slider. This should always be a
        value between 0.0 and 1.0.  return self.percent"""
        return self.percent

    def value_changed_handler(self, new_value):
        self.slider.setValue(new_value)
        self.textbox.clear()
        self.textbox.setText(f"{new_value/10.0}")
        self.percent = new_value / 1000.0
        self.callback(new_value)

    def reset_value(self):
        self.textbox.setText(f"{self.percent * 100.0}")
        self.slider.setValue(round(self.percent * 1000.0))

    def textbox_handler(self):
        # editingFinished signal handler
        txt = self.textbox.text()
        try:
            new_value = float(txt)
            if new_value >= 50.0 and new_value <= 100.0:
                self.percent = new_value / 100.0
            else:
                pass
        except ValueError:
            pass
        self.reset_value()
