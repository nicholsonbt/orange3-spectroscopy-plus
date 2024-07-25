import numpy as np
import pyqtgraph as pg

from AnyQt import QtCore, QtGui, QtWidgets

from Orange.widgets import gui

from orangecontrib.spectroscopy.widgets.gui import lineEditFloatRange
from orangecontrib.spectroscopy.widgets.preprocessors.registry import \
    preprocess_editors
from orangecontrib.spectroscopy.widgets.preprocessors.utils import \
    BaseEditorOrange, PreviewMinMaxMixin

from orangecontrib.spectroscopy_plus.preprocess import ChipTransition




class VerticalLine(pg.InfiniteLine):
    def __init__(self, pos):
        super().__init__(pos, angle=90, movable=False, span=(0.02, 0.98))
        self.deactivate()


    def activate(self):
        self.setPen(pg.mkPen(color=QtGui.QColor(QtCore.Qt.red), width=2, style=QtCore.Qt.DotLine))


    def deactivate(self):
        self.setPen(pg.mkPen(color=QtGui.QColor(QtCore.Qt.black), width=2, style=QtCore.Qt.DotLine))




class Line(QtWidgets.QFrame):
    inclusion_changed = QtCore.pyqtSignal()

    def __init__(self, pos, parent=None):
        QtWidgets.QFrame.__init__(self, parent)

        self.parent = parent
        self.pos = pos

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)

        label = QtWidgets.QLabel(str(pos))
        self.button = QtWidgets.QPushButton("Exclude")
        self.button.clicked.connect(self.toggle_inclusion)

        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Plain)
        self.setLineWidth(1)

        layout.addWidget(label)
        layout.addWidget(self.button)

        self.setLayout(layout)

        self.vline = VerticalLine(pos)

        self.parent.add_marking(self.vline)

        self.include()
        self.deactivate()


    def activate(self):
        self.setStyleSheet(f"background-color: tomato;")
        self.vline.activate()


    def deactivate(self):
        self.setStyleSheet(f"background-color: ghostwhite;") # lightgray
        self.vline.deactivate()


    #region Include/Exclude
    def include(self):
        self.included = True
        self.button.setText("Exclude")

        self.vline.setVisible(True)
        self.update_inclusion()
        

    def exclude(self):
        self.included = False
        self.button.setText("Include")

        self.vline.setVisible(False)
        self.update_inclusion()

    
    def set_inclusion(self, included):
        if included:
            self.include()
        
        else:
            self.exclude()


    def toggle_inclusion(self):
        self.set_inclusion(not self.included)


    def update_inclusion(self):
        self.inclusion_changed.emit()
    #endregion
        

    def delete(self):
        self.parent.remove_marking(self.vline)
        self.vline.deleteLater()
        self.deleteLater()




class Lines(QtWidgets.QWidget):
    inclusion_changed = QtCore.pyqtSignal()


    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.parent = parent

        # self.activated = False

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.lines = []

    #region Markings
    def add_marking(self, marking):
        self.parent.add_marking(marking)


    def remove_marking(self, marking):
        self.parent.remove_marking(marking)
    #endregion


    #region Set, add, remove, clear lines
    def set_lines(self, positions):
        self.clear()

        for pos in positions:
            self.add_line(pos)


    def add_line(self, pos):
        line = Line(pos, self)
        line.inclusion_changed.connect(self.inclusion_changed.emit)
        self.lines.append(line)
        self.layout.addWidget(line)


    def remove_line(self, line):
        self.layout.removeWidget(line)
        self.lines.remove(line)
        line.delete()

    
    def clear(self):
        while len(self.lines) > 0:
            self.remove_line(self.lines[0])
    #endregion


    def get_positions(self):
        return [(line.pos, line.included) for line in self.lines]
    

    def set_inclusion(self, index, included):
        self.lines[index].set_inclusion(included)


    def set_inclusions(self, included):
        for i, include in enumerate(included):
            self.set_inclusion(i, include)




class ChipTransitionEditor(BaseEditorOrange, PreviewMinMaxMixin):
    name = "Chip Transition"
    qualname = "preprocessors.chiptransition"

    ALPHA_DEFAULT = 3
    BETA_DEFAULT = 1


    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.preview_data = None
        self.order = None
        self.alpha = self.ALPHA_DEFAULT
        self.beta = self.BETA_DEFAULT
        self.indices = []
        self.selected = []

        self.controlArea.setLayout(QtWidgets.QVBoxLayout())
        
        box = gui.widgetBox(self.controlArea)

        self.alpha_value = lineEditFloatRange(None, master=self, bottom=0,
                                              value='alpha', default=self.ALPHA_DEFAULT,
                                              callback=self.argument_changed)
        
        self.alpha_value.setPlaceholderText(str(self.ALPHA_DEFAULT))
        gui.widgetLabel(box, label="Alpha:", labelWidth=50)
        box.layout().addWidget(self.alpha_value)

        self.beta_value = lineEditFloatRange(None, master=self, bottom=0,
                                             value='beta', default=self.BETA_DEFAULT,
                                             callback=self.argument_changed)
        
        self.beta_value.setPlaceholderText(str(self.BETA_DEFAULT))
        gui.widgetLabel(box, label='Beta:', labelWidth=60)
        box.layout().addWidget(self.beta_value)
        
        self.lines = Lines(self)
        self.lines.inclusion_changed.connect(self.derived_changed)

        self.connect_control("indices", lambda *args: self.derived_changed())
        self.connect_control("selected", lambda *args: self.selection_changed())

        box.layout().addWidget(self.lines)

        self.user_changed = False
    

    def add_marking(self, marking):
        self.parent_widget.curveplot.add_marking(marking)


    def remove_marking(self, marking):
        self.parent_widget.curveplot.remove_marking(marking)


    def set_preview_data(self, data):
        if data == self.preview_data:
            return
        
        self.order = None
        self.preview_data = data
        self.init_order()
        self.argument_changed()


    def init_order(self):
        if self.preview_data is None:
            self.order = None

        self.order = np.argsort([float(attr.name) for attr in self.preview_data.domain.attributes])


    def get_wavenumbers(self, indices):
        if self.preview_data is None or self.order is None or indices is None:
            return []
        
        attributes = np.array(self.preview_data.domain.attributes)[self.order]
        return np.array([(float(attributes[index].name) + float(attributes[index+1].name)) / 2.0 for index in indices])


    def argument_changed(self):
        # Alpha, beta or preview_data have changed, so indices must also change.
        indices = []
        wavenumbers = []

        if self.preview_data is not None:
            indices = ChipTransition.calculate_indices(self.preview_data.X[:, self.order], float(self.alpha), float(self.beta))
            wavenumbers = self.get_wavenumbers(indices)

        self.lines.set_lines(wavenumbers)

        self.indices = indices


    def derived_changed(self):
        # Indices changed, so excluded values are now included.
        self.selected = [self.indices[i] for i, (_, flag) in enumerate(self.lines.get_positions()) if flag]


    def selection_changed(self):
        self.edited.emit()


    def setParameters(self, params):
        if params:
            self.user_changed = True

        alpha = params.get("alpha", self.ALPHA_DEFAULT)
        beta = params.get("beta", self.BETA_DEFAULT)
        indices = params.get("indices", [])
        selected = params.get("selected", [])

        if self.alpha != alpha:
            self.alpha = alpha

        if self.beta != beta:
            self.beta = beta

        if not np.array_equal(self.indices, indices):
            self.indices = indices

        if not np.array_equal(self.selected, selected):
            self.selected = selected

        
    @classmethod
    def createinstance(cls, params):
        indices = params.get('selected', None)

        if indices is None:
            indices = []

        return ChipTransition(indices)
    

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        lines_pos = self.lines.mapFromParent(event.pos())

        for line in self.lines.lines:
            line.deactivate()

            if line.geometry().contains(lines_pos):
                line.activate()




preprocess_editors.register(ChipTransitionEditor, 201)
