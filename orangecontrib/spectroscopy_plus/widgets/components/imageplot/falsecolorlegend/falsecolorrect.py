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


from orangecontrib.spectroscopy_plus.utils.plots import ContrastingColorMethods, ImageTypes, ChannelNormalisationTypes




class FalseColorRect(pg.GraphicsWidget):
    """
    _extended_summary_

    Methods
    -------
    setData
    setRectColours
    setHistColours
    setHistData
    setHistVisibility
    setRange
    setNormalisationType
    """

    sigIsRGBChanged = QtCore.pyqtSignal(bool)
    # sigThresholdHighChanged = QtCore.pyqtSignal(float)
    # sigLevelLowChanged = QtCore.pyqtSignal(float)
    # sigLevelHighChanged = QtCore.pyqtSignal(float)
    # sigPaletteIndexChanged = QtCore.pyqtSignal(int)
    # sigPaletteChanged = QtCore.pyqtSignal(np.ndarray)

    BASIC_WIDTH = 15
    HIST_WIDTH = 50


    def __init__(self, **kwargs):
        pg.GraphicsWidget.__init__(self)
        self.width_bar = self.BASIC_WIDTH

        self.hist_colours = None
        self.rect_colours = None
        self.bounds = None
        self.kde = None
        self.hist_visible = None
        self.set_range = None
        self.hist_width = None
        self.is_rgb = None
        self.rgb_rel = None
        self._norm_type = None

        self.rect_gradient = QtGui.QLinearGradient()
        self.hist_gradient = QtGui.QLinearGradient()

        self.setMaximumHeight(2**16)
        self.setMinimumWidth(self.width_bar)
        self.setMaximumWidth(self.width_bar)

        self.rect = QtWidgets.QGraphicsRectItem(QtCore.QRectF(0, 0, self.width_bar, 100), self)
        self.line = QtWidgets.QGraphicsPathItem(self)

        self.line_r = QtWidgets.QGraphicsPathItem(self)
        self.line_g = QtWidgets.QGraphicsPathItem(self)
        self.line_b = QtWidgets.QGraphicsPathItem(self)

        self.axis = AxisItem('right', parent=self)
        self.axis.setX(self.width_bar)
        self.axis.geometryChanged.connect(self._updateWidth)
        self.adaptToSize()
        self._initialized = True

        kwargs = {
            "lut_colours"   : np.array([[255, 255, 255], [0, 0, 0]]),
            "line_colours"  : ContrastingColorMethods.Enum.INVERSE,
            "hist_visible"  : False,
            "range"         : None,
            "hist_width"    : 2,
            "rgb_rel"       : False,
            "norm_type"     : ChannelNormalisationTypes.GLOBAL,
        } | kwargs

        self.setData(**kwargs)


    def setData(self, **kwargs):
        if "lut_colours" in kwargs:
            self.setLUTColours(kwargs.get("lut_colours"), update=False)

        if "line_colours" in kwargs:
            self.setHistogramColours(kwargs.get("line_colours"), update=False)

        if "hist_data" in kwargs:
            self.setHistogramData(kwargs.get("hist_data"), update=False)

        if "hist_visible" in kwargs:
            self.setHistogramVisibility(kwargs.get("hist_visible"), update=False)

        if "range" in kwargs:
            self.setRange(kwargs.get("range"), update=False)

        if "hist_width" in kwargs:
            self.setLineWidth(kwargs.get("hist_width"), update=False)

        if "rgb_rel" in kwargs:
            self.setRGBRelativity(kwargs.get("rgb_rel"), update=False)

        if "norm_type" in kwargs:
            self.setNormalisationType(kwargs.get("norm_type"), update=False)

        self.update()

    
    def setRGBRelativity(self, rgb_rel, update=True):
        self.rgb_rel = rgb_rel

        if update:
            self.updateHist()


    def setLUTColours(self, colours, update=True):
        print("LUT", colours)
        self.rect_colours = colours

        self._updateRectGradient(colours, update=update)

        if isinstance(self.hist_colours, int) and (
                self.hist_colours == ContrastingColorMethods.Enum.INVERSE or
                self.hist_colours == ContrastingColorMethods.Enum.SHIFT or 
                self.hist_colours == ContrastingColorMethods.Enum.HSL):
            self.setHistogramColours(self.hist_colours, update=update)


    def setHistogramColours(self, colours, update=True):
        self.hist_colours = colours

        if self.rect_colours is None:
            return

        if isinstance(colours, int):
            func = ContrastingColorMethods.METHODS[colours]
            colours = [[*func(*rgb)] for rgb in self.rect_colours]

        self._updateHistGradient(colours, update=update)


    def _updateRectGradient(self, colours, update=True):
        if not colours is None:
            stops = self._coloursToStops(colours)
            self.rect_gradient.setStops(stops)

        if update:
            self.updateRect()

    
    def _updateHistGradient(self, colours, update=True):
        if not colours is None:
            stops = self._coloursToStops(colours)
            self.hist_gradient.setStops(stops)

        if update:
            self.updateHist()


    def setHistogramData(self, data, update=True):
        def getKDE(data):
            try:
                return stats.gaussian_kde(data)
            except np.linalg.LinAlgError:
                return None
            
        if len(data.shape) == 2 and data.shape[-1] == 3:
            if not self.is_rgb:
                self.sigIsRGBChanged.emit(True)
            self.is_rgb = True
            self.kde = [getKDE(data[:, i]) for i in range(3)]

        else:
            if self.is_rgb:
                self.sigIsRGBChanged.emit(False)
            self.is_rgb = False
            self.kde = getKDE(data.flatten())
        
        self.bounds = (np.nanmin(data), np.nanmax(data))

        if not self.set_range:
            self.axis.setRange(*self.bounds)

        if update:
            self.updateHist()

    
    def setHistogramVisibility(self, visibility, update=True):
        self.hist_visible = visibility

        if update:
            self.updateHist()


    def setRange(self, low=0, high=1, update=True):
        self.set_range = True

        if isinstance(low, tuple):
            low, high = low

        if low == None:
            low, high = (0, 1)
            self.set_range = False

        self.axis.setRange(low, high)

        if update:
            self.update()


    def setLineWidth(self, width, update=True):
        self.hist_width = width

        if update:
            self.updateHist()


    def setNormalisationType(self, norm_type, update=True):
        self._norm_type = norm_type

        if update:
            self.updateHist()


    ######################################################################
    

    def _updateWidth(self):
        aw = self.axis.minimumWidth()
        self.setMinimumWidth(self.width_bar + aw)
        self.setMaximumWidth(self.width_bar + aw)


    def resizeEvent(self, ev):
        if hasattr(self, "_initialized"):
            self.adaptToSize()


    def setBarWidth(self, width):
        self.width_bar = width
        self.axis.setX(self.width_bar)

    
    def update(self):
        self.updateRect()
        self.updateHist()

        
    def adaptToSize(self):
        h = self.height()
        self.resetTransform()
        self.rect.setRect(0, 0, self.width_bar, h)
        self.axis.setHeight(h)
        self.rect_gradient.setStart(QtCore.QPointF(0, h))
        self.rect_gradient.setFinalStop(QtCore.QPointF(0, 0))

        self.hist_gradient.setStart(QtCore.QPointF(0, h))
        self.hist_gradient.setFinalStop(QtCore.QPointF(0, 0))

        self.updateRect()
        self.updateHist()


    def _coloursToStops(self, colours):
        if colours is None:
            return None
        
        colours = np.round(colours).astype(int)
        positions = np.linspace(0, 1, len(colours))
        stops = []

        for p, c in zip(positions, colours):
            stops.append((p, QtGui.QColor(*c)))
        
        return stops


    def updateRect(self):
        if not self.set_range and not self.bounds is None:
            self.axis.setRange(*self.bounds)

        if self.rect_colours is None or self.is_rgb:
            self.rect.setBrush(QtGui.QBrush(QtCore.Qt.white))
        else:
            self.rect.setBrush(QtGui.QBrush(self.rect_gradient))


    def getNormHist(self):
        n = 100

        if self.kde is None:
            return None, None

        # If the range hasn't been set, use min-max as range.
        if self.set_range:
            lower, upper = zip(self.bounds, self.axis.range)
            xs = np.linspace(*self.axis.range, n)

        else:
            lower, upper = zip(self.bounds, self.bounds)
            xs = np.linspace(*self.bounds, n)

        # If is_rgb, find ys for each channel.
        if self.is_rgb:
            ys = np.array([self.kde[i](xs) for i in range(3)])

        else:
            ys = self.kde(xs)

        # If is_rgb and rgb_rel, normalise y of each channel relative
        # to itself. Else, normalise relative to the global min-max.
        if self.is_rgb and self.rgb_rel:
            y_norm = (ys.T / np.nanmax(ys, axis=1)).T

        else:
            y_norm = ys / np.nanmax(ys)

        # Normalise x (between 0 and 1).
        # if self._norm_type == ChannelNormalisationTypes.GLOBAL:

        x_norm = (xs-lower[1]) / (upper[1]-lower[1])

        # lower = abs(self.kde.integrate_box_1d(lower[0], max(lower)))
        # upper = abs(self.kde.integrate_box_1d(upper[0], min(upper)))

        return x_norm, y_norm


    def updateHist(self):
        def clearLines(*lines):
            hist = self.get_hist(None, None)

            for line in lines:
                line.setPath(hist)


        x, y = self.getNormHist()

        if (x is None or self.rect_colours is None or
                self.hist_colours is None or not self.hist_visible):

            clearLines(
                self.line,
                self.line_r,
                self.line_g,
                self.line_b,
            )

            self.setBarWidth(FalseColorRect.BASIC_WIDTH)
            return
    
        self.setBarWidth(FalseColorRect.HIST_WIDTH)

        if self.is_rgb:
            pen_r = QtGui.QPen()
            pen_g = QtGui.QPen()
            pen_b = QtGui.QPen()

            pen_r.setWidth(self.hist_width)
            pen_g.setWidth(self.hist_width)
            pen_b.setWidth(self.hist_width)

            pen_r.setBrush(QtGui.QColor(255, 0, 0))
            pen_g.setBrush(QtGui.QColor(0, 255, 0))
            pen_b.setBrush(QtGui.QColor(0, 0, 255))

            self.line_r.setPen(pen_r)
            self.line_g.setPen(pen_g)
            self.line_b.setPen(pen_b)

            clearLines(self.line)

            self.line_r.setPath(self.get_hist(x, y[0]))
            self.line_g.setPath(self.get_hist(x, y[1]))
            self.line_b.setPath(self.get_hist(x, y[2]))
        
        else:
            pen = QtGui.QPen()

            pen.setWidth(self.hist_width)

            pen.setBrush(self.hist_gradient)

            self.line.setPen(pen)

            self.line.setPath(self.get_hist(x, y))

            clearLines(
                self.line_r,
                self.line_g,
                self.line_b,
            )


    def get_hist(self, x, y):
        def calculate_x_pos(x, max_width, line_width):
            # Calculate the scale as 1/2 the LUT width.
            scale = max_width / 2

            # Multiply x by the scale to get the real x position.
            x_pos = x * scale

            # Add (shift right) the x position by 1/2 the line width
            # and 1 for the border.
            return x_pos + line_width / 2
        
        def calculate_y_pos(y, max_height, line_width):
            # Top left corner is (0, 0) and down is positive.
            inv_y = 1 - y

            # Subtract line width to ensure line doesn't overflow (half
            # at each end). Also subtract 1 due to the border.
            scale = max_height - line_width - 1

            # Multiply inv_y by scale to get the real y position.
            y_pos = inv_y * scale

            # Add (shift down) the y position by 1/2 the line width and
            # 1 for the border.
            return y_pos + line_width / 2 + 1
        
        histogram = QtGui.QPainterPath()

        if x is None:
            return histogram

        map_to_rect = lambda x, y, \
                            mw=self.width_bar, \
                            mh=self.height(), \
                            lw=self.hist_width: QtCore.QPointF(
                                calculate_x_pos(x, mw, lw),
                                calculate_y_pos(y, mh, lw)
                            )
        
        histogram.moveTo(map_to_rect(0, 0))

        for x, y in zip(x, y):
            histogram.lineTo(map_to_rect(y, x))

        return histogram
