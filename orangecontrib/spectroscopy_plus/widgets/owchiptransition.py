import numpy as np
import pyqtgraph as pg

import Orange.data

from AnyQt import QtCore, QtGui, QtWidgets

from Orange.widgets import gui, widget, settings

from orangecontrib.spectroscopy.widgets.gui import lineEditFloatRange
from orangecontrib.spectroscopy.widgets.preprocessors.registry import \
    preprocess_editors
from orangecontrib.spectroscopy.widgets.preprocessors.utils import \
    BaseEditorOrange, PreviewMinMaxMixin

from orangecontrib.spectroscopy.widgets.owspectra import CurvePlot, SELECTNONE


from orangewidget.utils.visual_settings_dlg import VisualSettingsDialog





class VerticalLine(pg.InfiniteLine):
    def __init__(self, pos):
        super().__init__(pos, angle=90, movable=False, span=(0.02, 0.98))
        self.deactivate()


    def activate(self):
        self.setPen(pg.mkPen(color=QtGui.QColor(QtCore.Qt.red), width=2, style=QtCore.Qt.DotLine))


    def deactivate(self):
        self.setPen(pg.mkPen(color=QtGui.QColor(QtCore.Qt.black), width=2, style=QtCore.Qt.DotLine))




class Line(QtWidgets.QFrame):
    BTN_WIDTH = 60

    inclusion_changed = QtCore.pyqtSignal()

    class STATES:
        INCLUDED = 0
        EXCLUDED = 1
        ACTIVE = 2
        DELAYED_ACTIVE = 3

    def __init__(self, pos, parent=None):
        QtWidgets.QFrame.__init__(self, parent)

        self.parent = parent
        self.pos = pos

        self.state = self.STATES.INCLUDED

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(3, 3, 3, 3)

        label = QtWidgets.QLabel(str(pos))
        self.button = QtWidgets.QPushButton("Exclude")
        self.button.clicked.connect(self.toggle_inclusion)
        self.button.setFixedWidth(Line.BTN_WIDTH)

        self.setFixedHeight(40)

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

    
    @property
    def included(self):
        return self.state != self.STATES.EXCLUDED
    


    #region Include/Exclude/Activate/Deactivate
    def include(self):
        self.state = self.STATES.INCLUDED
        self.button.setText("Exclude")
        self.setStyleSheet(f"background-color: ghostwhite;")

        self.vline.deactivate()
        self.vline.setVisible(True)
        self.update_inclusion()
        

    def exclude(self):
        self.state = self.STATES.EXCLUDED
        self.button.setText("Include")
        self.setStyleSheet(f"background-color: lightgray;")

        self.vline.deactivate()
        self.vline.setVisible(False)
        self.update_inclusion()

    
    def activate(self):
        if self.state == self.STATES.INCLUDED or self.state == self.STATES.DELAYED_ACTIVE:
            self.setStyleSheet(f"background-color: tomato;")
            self.state = self.STATES.ACTIVE
            self.vline.activate()
        else:
            raise Exception("A")
        
    
    def delayed_activate(self):
        if self.state == self.STATES.INCLUDED:
            self.state = self.STATES.DELAYED_ACTIVE


    def deactivate(self):
        if self.state == self.STATES.ACTIVE:
            self.include()
        
        if self.state == self.STATES.DELAYED_ACTIVE:
            self.activate()

    
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


    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        if event.button() == QtCore.Qt.LeftButton and self.state == self.STATES.INCLUDED:
            self.delayed_activate()




class Lines(QtWidgets.QWidget):
    inclusion_changed = QtCore.pyqtSignal()


    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.parent = parent

        # self.activated = False

        layout = QtWidgets.QVBoxLayout()
        self.scroll = QtWidgets.QScrollArea()
        self.widget = QtWidgets.QWidget()

        container = QtWidgets.QVBoxLayout()
        self.layout = QtWidgets.QVBoxLayout()

        container.addLayout(self.layout)
        container.addStretch()

        self.widget.setLayout(container)

        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        container.setSpacing(0)
        container.setContentsMargins(0, 0, 0, 0)

        self.layout.setSpacing(5)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setWidgetResizable(True)

        sp = self.sizePolicy()
        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
        # self.scroll.setFixedHeight(500)

        self.scroll.setWidget(self.widget)
        layout.addWidget(self.scroll)
        self.setLayout(layout)

        self.lines = []


    #region Markings
    def add_marking(self, marking):
        self.parent.add_marking(marking)


    def remove_marking(self, marking):
        self.parent.remove_marking(marking)
    #endregion


    def deactivate_all(self):
        for line in self.lines:
            line.deactivate()


    #region Set, add, remove, clear lines
    def set_lines(self, positions):
        self.clear()

        for pos in positions:
            self.add_line(pos)


    def add_line(self, pos):
        line = Line(pos, self)
        line.inclusion_changed.connect(self.inclusion_changed.emit)
        line.include()
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










class OWChipTransition(widget.OWWidget):
    name = "Chip Transition"
    qualname = "orangecontrib.spectroscopy_plus.widgets.owchiptransition"



    ALPHA_DEFAULT = 3
    BETA_DEFAULT = 1


    class Inputs:
        data = widget.Input("Data", Orange.data.Table, default=True)

    class Outputs:
        data = widget.Output("Data", Orange.data.Table, default=True)


    settingsHandler = settings.DomainContextHandler()

    curveplot = settings.SettingProvider(CurvePlot)
    curveplot_after = settings.SettingProvider(CurvePlot)

    autocommit = settings.Setting(True)

    alpha = settings.Setting(ALPHA_DEFAULT)
    beta = settings.Setting(BETA_DEFAULT)


    visual_settings = settings.Setting({}, schema_only=True)

    graph_name = "curveplot.plotview"  # need to be defined for the save button to be shown


    def __init__(self):
        widget.OWWidget.__init__(self)

        self.selected = []

        # self.curveplot = CurvePlot(self)
        # self.mainArea.layout().addWidget(self.curveplot)

        splitter = QtWidgets.QSplitter(self)
        splitter.setOrientation(QtCore.Qt.Vertical)
        self.curveplot = CurvePlot(self)
        self.curveplot_after = CurvePlot(self)
        self.curveplot.plot.vb.x_padding = 0.005  # pad view so that lines are not hidden
        self.curveplot_after.plot.vb.x_padding = 0.005  # pad view so that lines are not hidden

        splitter.addWidget(self.curveplot)
        splitter.addWidget(self.curveplot_after)
        self.mainArea.layout().addWidget(splitter)

        self.indices = []
        
        sigma_box = gui.widgetBox(self.controlArea, "Sigma Values")

        self.alpha_value = lineEditFloatRange(None, master=self, bottom=0,
                                              value='alpha', default=self.ALPHA_DEFAULT,
                                              callback=self.refresh_transition_indices)
        
        self.alpha_value.setPlaceholderText(str(self.ALPHA_DEFAULT))
        gui.widgetLabel(sigma_box, label="Alpha:", labelWidth=50)
        sigma_box.layout().addWidget(self.alpha_value)

        self.beta_value = lineEditFloatRange(None, master=self, bottom=0,
                                             value='beta', default=self.BETA_DEFAULT,
                                             callback=self.refresh_transition_indices)
        
        self.beta_value.setPlaceholderText(str(self.BETA_DEFAULT))
        gui.widgetLabel(sigma_box, label='Beta:', labelWidth=60)
        sigma_box.layout().addWidget(self.beta_value)

        lines_box = gui.widgetBox(self.controlArea, "Chip Transitions")
        
        self.lines = Lines(self)
        self.lines.inclusion_changed.connect(self.indices_changed)

        self.connect_control("indices", lambda *_: self.indices_changed())
        self.connect_control("selected", lambda *_: self.selection_changed())

        lines_box.layout().addWidget(self.lines)

        # gui.rubber(self.controlArea)
        gui.auto_commit(self.controlArea, self, "autocommit", "Send Data")

        self.resize(900, 700)
        VisualSettingsDialog(self, self.curveplot.parameter_setter.initial_settings)


    def get_corrected(self):
        if len(self.selected) == 0:
            return self.curveplot.data
        
        order = self.order
        
        rev_order = np.argsort(order)

        new_data = self.data.X[:, order].copy()

        for r_index in np.sort(self.selected):
            left = new_data[:, r_index]
            right = new_data[:, r_index+1]

            new_data[:, 0:r_index+1] *= (right / left)[:, np.newaxis]

        out_data = self.data.copy()
        out_data.X = new_data[:, rev_order]

        return out_data

    
    @Inputs.data
    def set_data(self, data):
        self.curveplot.set_data(data)
        self.refresh_transition_indices()
        self.commit.now()


    def set_visual_settings(self, key, value):
        self.curveplot.parameter_setter.set_parameter(key, value)
        self.visual_settings[key] = value


    def handleNewSignals(self):
        self.curveplot.update_view()


    def save_graph(self):
        # directly call save_graph so it hides axes
        self.curveplot.save_graph()


    @gui.deferred
    def commit(self):
        outdata = self.get_corrected()
        self.curveplot_after.set_data(outdata)
        self.Outputs.data.send(outdata)


    def add_marking(self, marking):
        self.curveplot.add_marking(marking)


    def remove_marking(self, marking):
        self.curveplot.remove_marking(marking)


    def get_wavenumbers(self, indices):
        if self.data is None or indices is None:
            return []
        
        attrs = self.wavenumbers
        
        return np.array([(attrs[index] + attrs[index+1]) / 2.0 for index in indices])


    @staticmethod
    def find_transition_indices(ys, alpha, beta):
        # Calculate the mean value for each column.
        mean_row = np.nanmean(ys, axis=0)

        # Get the moving sum of the differences (such that noise is
        # minimised).
        diff = np.diff(mean_row)
        diff_sum = np.abs(diff[:-1] + diff[1:])

        # Set the fist and last moving diff sum values to 0.
        diff_sum[[0, -1]] = 0

        # Get the standard deviation of the moving diff sum array.
        std = np.std(diff_sum)

        # If a moving diff sum value is less than alpha * std, set it
        # to 0. This aims to remove noise without removing actual chip
        # transitions.
        diff_sum[diff_sum < alpha * std] = 0

        # Calculate the difference of the moving diff sum array.
        diff_sum_2 = np.abs(np.diff(diff_sum))

        noise_mask = np.hstack((True, diff_sum_2 > beta * std))

        diff_sum[noise_mask] = 0

        indices = np.where(diff_sum > 0)

        return indices[0]
    

    def refresh_transition_indices(self):
        # Alpha, beta or data have changed, so indices must also change.
        self.indices = []
        self.lines.clear()

        if self.data is None:
            return

        ys = self.data.X[:, self.order]
        alpha = float(self.alpha)
        beta = float(self.beta)

        self.indices = OWChipTransition.find_transition_indices(ys, alpha, beta)

        wavenumbers = self.get_wavenumbers(self.indices)

        self.lines.set_lines(wavenumbers)


    def indices_changed(self):
        self.refresh_selected()


    def refresh_selected(self):
        self.selected = [self.indices[i] for i, (_, flag) in enumerate(self.lines.get_positions()) if flag]


    def selection_changed(self):
        self.commit.deferred()


    @property
    def data(self):
        return self.curveplot.data
    
    @property
    def wavenumbers(self):
        return np.sort(self.attributes)

    @property
    def order(self):
        return np.argsort(self.attributes)

    @property
    def attributes(self):
        return np.array([float(attr.name) for attr in self.data.domain.attributes])
    

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.lines.deactivate_all()
        
    

    # def setParameters(self, params):
    #     if params:
    #         self.user_changed = True

    #     alpha = params.get("alpha", self.ALPHA_DEFAULT)
    #     beta = params.get("beta", self.BETA_DEFAULT)
    #     indices = params.get("indices", [])
    #     selected = params.get("selected", [])

    #     if self.alpha != alpha:
    #         self.alpha = alpha

    #     if self.beta != beta:
    #         self.beta = beta

    #     if not np.array_equal(self.indices, indices):
    #         self.indices = indices

    #     if not np.array_equal(self.selected, selected):
    #         self.selected = selected

        
    # @classmethod
    # def createinstance(cls, params):
    #     indices = params.get('selected', None)

    #     if indices is None:
    #         indices = []

    #     return ChipTransition(indices)
    

    # def mousePressEvent(self, event):
    #     super().mousePressEvent(event)

    #     lines_pos = self.lines.mapFromParent(event.pos())

    #     for line in self.lines.lines:
    #         line.deactivate()

    #         if line.geometry().contains(lines_pos):
    #             line.activate()













if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    data = Orange.data.Table("C:\\Users\\ixy94928\\Downloads\\chip_transition_data.tab")
    WidgetPreview(OWChipTransition).run(data)
