from AnyQt.QtWidgets import QWidget, QGraphicsItem, QPushButton, QMenu, \
    QGridLayout, QAction, QVBoxLayout, QApplication, QWidgetAction, \
    QShortcut, QToolTip, QGraphicsRectItem, QGraphicsTextItem
from AnyQt.QtGui import QColor, QPixmapCache, QPen, QKeySequence, QFontDatabase, \
    QPalette
from AnyQt.QtCore import Qt, QRectF, QPointF, QObject
from AnyQt.QtCore import pyqtSignal

from AnyQt import QtCore, QtGui, QtWidgets

import bottleneck
import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.ViewBox import ViewBox
from pyqtgraph import Point, GraphicsObject

from orangewidget.utils.visual_settings_dlg import VisualSettingsDialog

import Orange.data
from Orange.data import DiscreteVariable
from Orange.widgets.widget import OWWidget, Msg, OWComponent, Input, Output
from Orange.widgets import gui
from Orange.widgets.settings import \
    Setting, ContextSetting, DomainContextHandler, SettingProvider
from Orange.widgets.utils.itemmodels import DomainModel
from Orange.widgets.utils.plot import \
    SELECT, PANNING, ZOOMING
from Orange.widgets.utils import saveplot
from Orange.widgets.visualize.owscatterplotgraph import LegendItem
from Orange.widgets.utils.concurrent import TaskState, ConcurrentMixin
from Orange.widgets.visualize.utils.plotutils import HelpEventDelegate, PlotWidget
from Orange.widgets.visualize.utils.customizableplot import CommonParameterSetter

from orangecontrib.spectroscopy.data import getx
from orangecontrib.spectroscopy.utils import apply_columns_numpy
from orangecontrib.spectroscopy.widgets.line_geometry import \
    distance_curves, intersect_curves_chunked
from orangecontrib.spectroscopy.widgets.gui import pixel_decimals, \
    VerticalPeakLine, float_to_str_decimals as strdec
from orangecontrib.spectroscopy.widgets.utils import \
    SelectionGroupMixin, SelectionOutputsMixin
from orangecontrib.spectroscopy.widgets.visual_settings import FloatOrUndefined

from orangecontrib.spectroscopy.widgets.owhyper import QTest, Domain, Identity, refresh_integral_markings, Integrate, MovableVline, ContinuousVariable

from orangecontrib.spectroscopy.widgets.owspectra import CurvePlot, SELECTNONE


from orangecontrib.spectroscopy_plus.widgets.components.editors.hypereditor.integrationtypes import UseFeature, UseRGB, FromSpectra
from orangecontrib.spectroscopy_plus.widgets.components.editors.tableview import TableView

from orangecontrib.spectroscopy_plus.widgets.components.editors.oweditor import OWEditor

from orangecontrib.spectroscopy_plus.utils.plots import setBackgroundColour




class HyperEditor(OWEditor):
    name = "HyperEditor"

    icon = "icons/spectra.svg"

    priority = 10
    keywords = ["curves", "lines", "spectrum"]


    curveplot = SettingProvider(CurvePlot)
    tableview = SettingProvider(TableView)

    from_spectra = SettingProvider(FromSpectra)
    use_feature = SettingProvider(UseFeature)
    use_rgb = SettingProvider(UseRGB)


    updated = pyqtSignal()

    # Not sure how to do settings for an editor.
    value_type = 0 #Setting(0)

    visual_settings = {} #Setting({}, schema_only=True)

    graph_name = "curveplot.plotview"  # need to be defined for the save button to be shown

    # class Information(SelectionOutputsMixin.Information):
    #     showing_sample = Msg("Showing {} of {} curves.")
    #     view_locked = Msg("Axes are locked in the visual settings dialog.")

    # class Warning(OWEditor.Warning):
    #     no_x = Msg("No continuous features in input data.")


    def __init__(self, parent):
        OWEditor.__init__(self, parent)

        self.setup_curveplot()

        self.integration_types = [
            FromSpectra(self),
            UseFeature(self),
            UseRGB(self),
        ]
        
        self.setup_menu()

        # self.settingsAboutToBePacked.connect(self.prepare_special_settings)

        self.markings_integral = []

        self._update_integration_type()

        self.resize(900, 700)
        # VisualSettingsDialog(self, self.curveplot.parameter_setter.initial_settings)

    
    def setup_curveplot(self):
        self.tab_widget = QtWidgets.QTabWidget()

        self.curveplot = CurvePlot(self, select=SELECTNONE)
        self.tableview = TableView(self)

        setBackgroundColour(self, self.curveplot)
        setBackgroundColour(self, self.tableview)

        self.tab_widget.addTab(self.curveplot, "Spectra")
        self.tab_widget.addTab(self.tableview, "Table")

        # self.curveplot.new_sampling.connect(self._showing_sample_info)
        self.curveplot.plot.vb.x_padding = 0.005  # pad view so that lines are not hidden
        # self.curveplot.locked_axes_changed.connect(
        #     lambda locked: self.Information.view_locked(shown=locked))

        self.mainArea.layout().addWidget(self.tab_widget)


    def setup_menu(self):
        dbox = gui.widgetBox(self.controlArea, "Image values")

        rbox = gui.radioButtons(
            dbox, self, "value_type", callback=self._change_integration)
        
        for cls in self.integration_types:
            cls.add_radio(rbox)

        gui.rubber(self.controlArea)


    def init_attr_values(self, data):
        for cls in self.integration_types:
            cls.init_values(data)
        self.redraw_data()


    def image_values(self):
        return self.integration_types[self.value_type].image_values()
        
    
    def image_values_fixed_levels(self):
        return self.integration_types[self.value_type].image_values_fixed_levels()
    

    def lut_colours(self):
        return self.integration_types[self.value_type].lut_colours()


    def redraw_data(self):
        self.redraw_integral_info()
        self.updated.emit()


    def _update_integration_type(self):
        for i, cls in enumerate(self.integration_types):
            if i == self.value_type:
                cls.setDisabled(False)

            else:
                cls.setDisabled(True)

        # ImagePlot menu levels visibility
        rgb = self.value_type == 1 # 2
        # self.imageplot.rgb_settings_box.setVisible(rgb)
        # self.imageplot.color_settings_box.setVisible(not rgb)
        QTest.qWait(1)  # first update the interface


    def _change_integration(self):
        self._update_integration_type()
        self.redraw_data()


    def set_data(self, data):
        # self.closeContext()
        # self._showing_sample_info(None)
        # self.Warning.no_x.clear()
        # self.openContext(data)

        self.tableview.set_data(data)
        self.curveplot.set_data(data, auto_update=True)
        self.init_interface_data(data)

        enabled = -1

        for i, it in enumerate(self.integration_types):
            valid = it.validData(data)
            it.setAllowed(valid)

            if valid and (enabled == -1 or i == self.value_type):
                enabled = i

        if enabled == -1:
            raise Exception("No integration types are valid with the given data.")
        
        self.value_type = enabled
        self.integration_types[enabled].radio.setChecked(True)


        if data is not None:
            n = len(self.curveplot.data_x)

            if n == 0:
                self.Warning.no_x()
            
            elif n == 1:
                self.tab_widget.setCurrentIndex(1)
            
            else:
                self.tab_widget.setCurrentIndex(0)

        self.update_view()

    
    def update_view(self):
        self.handleNewSignals()


    # def set_visual_settings(self, key, value):
    #     self.curveplot.parameter_setter.set_parameter(key, value)
    #     self.visual_settings[key] = value


    def handleNewSignals(self):
        self.curveplot.update_view()
        self.tableview.handleNewSignals()


    # def _showing_sample_info(self, num):
    #     if num is not None and self.curveplot.data and num != len(self.curveplot.data):
    #         self.Information.showing_sample(num, len(self.curveplot.data))
    #     else:
    #         self.Information.showing_sample.clear()


    def prepare_special_settings(self):
        self.curveplot.save_peak_labels()


    def onDeleteWidget(self):
        self.curveplot.shutdown()
        super().onDeleteWidget()


    def redraw_integral_info(self):
        di = {}
        self.refresh_markings(di)


    def refresh_markings(self, di):
        refresh_integral_markings([{"draw": di}], self.markings_integral, self.curveplot)


    def changed_integral_range(self):
        self.redraw_integral_info()


    def init_interface_data(self, data):
        self.init_attr_values(data)




if __name__ == "__main__":  # pragma: no cover
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    data = None
    domain = Orange.data.Domain([data.domain.attributes[0]], data.domain.class_vars, data.domain.metas)
    table = Orange.data.Table.from_numpy(domain, data.X[:, 0][:, np.newaxis], data.Y, data.metas)

    WidgetPreview(HyperEditor).run(set_data=table)