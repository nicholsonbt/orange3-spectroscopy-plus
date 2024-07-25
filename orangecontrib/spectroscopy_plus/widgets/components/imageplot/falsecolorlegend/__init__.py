import numpy as np
import pyqtgraph as pg

from scipy import stats
from AnyQt import QtCore, QtGui, QtWidgets

import Orange.data

from Orange.widgets import gui, settings, widget

from Orange.widgets.visualize.utils.plotutils import AxisItem

from orangecontrib.spectroscopy.widgets.owhyper import get_levels, color_palette_model, \
    _color_palettes, color_palette_table, lineEditDecimalOrNone, pixels_to_decimals, \
    float_to_str_decimals


from orangecontrib.spectroscopy_plus.utils.plots import ImageTypes, ChannelNormalisationTypes


from orangecontrib.spectroscopy_plus.widgets.components.imageplot.falsecolorlegend.falsecolorrect import FalseColorRect
from orangecontrib.spectroscopy_plus.widgets.components.imageplot.falsecolorlegend.menucontroller import MenuController





class Dragger:
    def __init__(self, parent):
        self.parent = parent
        self.x = None
        self.bounds = None


    def init(self, x):
        self.x = x

    
    def outsideBounds(self, x):
        if self.bounds is None:
            return False
        
        return x < self.bounds[0] or x > self.bounds[1]

    
    def update(self, new_x):
        if self.outsideBounds(new_x) or self.x is None:
            return
        
        offset = new_x - self.x
        self.x = new_x

        old_pos = self.parent.pos()

        new_pos = QtCore.QPointF(old_pos.x() + offset, old_pos.y())

        self.parent.setPos(new_pos)

    
    def setBounds(self, x0, x1):
        self.bounds = (x0, x1)





class FCLegend(pg.GraphicsWidget):
    sigPaletteChanged = QtCore.pyqtSignal(np.ndarray)
    sigPlotTypeChanged = QtCore.pyqtSignal(int)
    sigNormTypeChanged = QtCore.pyqtSignal(int)
    sigZoomToFit = QtCore.pyqtSignal()

    sigMoving = QtCore.pyqtSignal(bool)


    #region Magic Methods:
    def __init__(self, **kwargs):
        pg.GraphicsWidget.__init__(self)
        self.setFlag(pg.GraphicsWidget.ItemIsMovable, True)

        self.settings = [
            MenuController()
        ]

        self._dragger = Dragger(self)

        self.settings[0].sigPaletteChanged.connect(self.sigPaletteChanged.emit)
        self.settings[0].sigPlotTypeChanged.connect(self.sigPlotTypeChanged.emit)
        self.settings[0].sigNormTypeChanged.connect(self.sigNormTypeChanged.emit)

        self.sigPaletteChanged.connect(self.paletteChanged)
        self.sigNormTypeChanged.connect(self.normalisationTypeChanged)

        self.lut = FalseColorRect(**kwargs)
        self.lut.sigIsRGBChanged.connect(self.settings[0].setIsRGB)

        QtCore.QTimer.singleShot(0, self.init_values)

        self.layout = QtWidgets.QGraphicsGridLayout()

        pushbutton = QtWidgets.QPushButton("MENU")
        self.menu = QtWidgets.QMenu()

        self.addActions(self.menu)

        pushbutton.setMenu(self.menu)

        self.graphics_menu = QtWidgets.QGraphicsProxyWidget()
        self.graphics_menu.setWidget(pushbutton)

        self.layout.addItem(self.graphics_menu, 0, 0)
        self.layout.addItem(self.lut, 1, 0)

        self.setLayout(self.layout)


    def __getattr__(self, attr):
        try:
            return super().__getattribute__(attr)
        except AttributeError:
            return self.lut.__getattribute__(attr)
    #endregion


    def init_values(self):
        self.settings[0].setIsRGB(self.lut.is_rgb)
        self.settings[0].color_cb.activated.emit(0)


    def paletteChanged(self, new_palette):
        cols = color_palette_table(new_palette)
        self.lut.setLUTColours(cols)

    def normalisationTypeChanged(self, norm_type):
        self.lut.setNormalisationType(norm_type)


    #region Menu Actions:
    def addActions(self, menu):
        defaults = {
            "show_hist" : False,
        }

        # Show hist:
        action = QtWidgets.QAction("Show Histogram", menu, checkable=True)
        action.triggered.connect(self.showHistAction)        
        menu.addAction(action)

        action = QtWidgets.QAction("Zoom to fit", menu)
        action.triggered.connect(self.zoomToFit)        
        menu.addAction(action)

        self.showHistAction(False)

        if defaults["show_hist"]:
            action.trigger()

        for setting in self.settings:
            box = setting.settings_box()
            action = QtWidgets.QWidgetAction(menu)
            action.setDefaultWidget(box)
            menu.addAction(action)


    def set_menu_visible(self, visibility):
        self.graphics_menu.setVisible(visibility)


    def showHistAction(self, flag):
        self.lut.setHistogramVisibility(flag)


    def zoomToFit(self, *_):
        self.sigZoomToFit.emit()
    #endregion


    #region Resizing:
    def resizeEvent(self, ev):
        self.adaptToSize()

        
    def adaptToSize(self):
        width = max(55, self.lut.width_bar + 20)
        self.graphics_menu.setMinimumWidth(width)
        self.graphics_menu.setMaximumWidth(width)
    #endregion

    def setData(self, **kwargs):
        self.lut.setData(**kwargs)


    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.sigMoving.emit(True)
            self._dragger.init(event.scenePos().x())


    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.sigMoving.emit(False)
            self._dragger.init(None)


    def mouseMoveEvent(self, event):
        self._dragger.update(event.scenePos().x())


    def setMoveBounds(self, x0, x1):
        self._dragger.setBounds(x0, x1)
