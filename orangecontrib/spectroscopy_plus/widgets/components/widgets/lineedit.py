from decimal import Decimal

from AnyQt.QtWidgets import QLineEdit, QApplication
from AnyQt.QtGui import QDoubleValidator

from AnyQt.QtCore import Qt

from orangewidget.utils import getdeepattr
from orangewidget.gui import CallFrontLineEdit, connectControl




class LineEdit(QLineEdit):
    FAST_KEY = Qt.Key_Shift
    SLOW_KEY = Qt.Key_Control

    def __init__(self, master, value=None, label=None, labelWidth=None, callback=None,
             valueType=None, bounds=None, controlWidth=None,
             callbackOnType=False, focusInCallback=None, **misc):
        """
        Insert a line edit.

        :param widget: the widget into which the box is inserted
        :type widget: QWidget or None
        :param master: master widget
        :type master: OWBaseWidget or OWComponent
        :param value: the master's attribute with which the value is synchronized
        :type value:  str
        :param label: label
        :type label: str
        :param labelWidth: the width of the label
        :type labelWidth: int
        :param orientation: tells whether to put the label above or to the left
        :type orientation: `Qt.Vertical` (default) or `Qt.Horizontal`
        :param box: tells whether the widget has a border, and its label
        :type box: int or str or None
        :param callback: a function that is called when the check box state is
            changed
        :type callback: function
        :param valueType: the type into which the entered string is converted
            when synchronizing to `value`. If omitted, the type of the current
            `value` is used. If `value` is `None`, the text is left as a string.
        :type valueType: type or None
        :param validator: the validator for the input
        :type validator: QValidator
        :param controlWidth: the width of the line edit
        :type controlWidth: int
        :param callbackOnType: if set to `True`, the callback is called at each
            key press (default: `False`)
        :type callbackOnType: bool
        :param focusInCallback: a function that is called when the line edit
            receives focus
        :type focusInCallback: function
        :rtype: QLineEdit or a box
        """
        
        super().__init__(master)
        self.faster = False
        self.slower = False
        self.editingFinished.connect(self._ensureDecimal)
        
        if callbackOnType:
            self.textChanged.connect(callback)
        else:
            self.editingFinished.connect(callback)
        

        if bounds:
            validator = QDoubleValidator(*bounds)
        
        else:
            validator = QDoubleValidator()

        self.setValidator(validator)

        if controlWidth:
            self.setFixedWidth(controlWidth)

        current_value = getdeepattr(master, value) if value else 0.0
        self.setText(str(current_value))

        if value:
            self.cback = connectControl(
                master, value,
                callbackOnType and callback, self.textChanged[str],
                CallFrontLineEdit(self), fvcb=valueType or type(current_value))[1]


    def keyPressEvent(self, event):
        if event.key() == LineEdit.FAST_KEY:
            self.faster = True

        if event.key() == LineEdit.SLOW_KEY:
            self.slower = True

        QLineEdit.keyPressEvent(self, event)


    def keyReleaseEvent(self, event):
        if event.key() == LineEdit.FAST_KEY:
            self.faster = False

        if event.key() == LineEdit.SLOW_KEY:
            self.slower = False

        if event.key() == Qt.Key_Return:
            self.clearFocus()

        QLineEdit.keyReleaseEvent(self, event)


    def focusInEvent(self, event):
        self.setReadOnly(False)
        super().focusInEvent(event)

    
    def focusOutEvent(self, event):
        self.setReadOnly(True)
        self._ensureDecimal()
        super().focusOutEvent(event)

    
    def _ensureDecimal(self):
        print(1)
        if self.text().strip() == "":
            self.setText("0.0")
        
        elif '.' not in self.text():
            self.setText(self.text() + ".0")


    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() > 0 else -1

        modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.ShiftModifier:
        # if self.faster:
            delta *= 10

        if modifiers == Qt.ControlModifier :
        # if self.slower:
            delta *= 0.1

        self.setText(str(float(Decimal(self.text()) + Decimal(delta))))
        event.accept()