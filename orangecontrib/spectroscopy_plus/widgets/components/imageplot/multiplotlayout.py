import numpy as np
import pyqtgraph as pg

from AnyQt import QtCore, QtGui, QtWidgets

from orangecontrib.spectroscopy_plus.widgets.components.imageplot.multiimage import MultiImage
from orangecontrib.spectroscopy_plus.widgets.components.imageplot.multilegend import MultiLegend


class MultiPlotLayout(pg.GraphicsLayout):
    def __init__(self, parent=None, border=None, **kwargs):
        pg.GraphicsLayout.__init__(self, parent=None, border=border)
        self.parent = parent

        self.multiimage = MultiImage(self)
        self.multilegend = MultiLegend(self)

        self.addItem(self.multiimage, row=0, col=0)
        self.addItem(self.multilegend, row=0, col=1)

        self.setOpts(**{
            "aspect_locked"     : True,
            "invert_x"          : False,
            "invert_y"          : False,
            "auto_range"        : True,
            "show_grid"         : (False, False, 1.0),
            "composition_mode"  : QtGui.QPainter.CompositionMode_SourceOver,
        } | kwargs)

    
    def setOpts(self, **kwargs):
        self.multiimage.setOpts(**kwargs)
        self.multilegend.setOpts(**kwargs)

    
    def setCompositionMode(self, comp_mode, update=True):
        self.multiimage.setCompositionMode(comp_mode, update)


    def move_data(self, from_, to_, source=None):
        if source is None:
            source = self
            
        if source != self.parent:
            self.parent.move_data(from_, to_, self)
        
        if source != self.multiimage:
            self.multiimage.move_data(from_, to_, self)

        if source != self.multilegend:
            self.multilegend.move_data(from_, to_, self)


    def setData(self, index, values, coords=None, **kwargs):
        self.multiimage.setData(index, values, coords, **kwargs)
        self.multilegend.setData(index, values, coords, **kwargs)

    
    def insertData(self, index, values, coords, **kwargs):
        self.multiimage.insertData(index, values, coords, **kwargs)
        self.multilegend.insertData(index, values, coords, **kwargs)


    def removeData(self, index):
        self.multiimage.removeData(index)
        self.multilegend.removeData(index)


    def getBounds(self):
        return self.multiimage.getBounds()
    

    def zoomToFit(self, arg=None):
        # arg is a QRectF or an int (index)
        self.multiimage.zoomToFit(arg)


    def refresh(self):
        self.multiimage.refresh()
        self.multilegend.refresh()


    def setLookupTable(self, index, palette):
        self.multiimage.setLookupTable(index, palette)

    def setPlotType(self, index, plot_type):
        self.multiimage.setPlotType(index, plot_type)

    def setNormType(self, index, norm_type):
        self.multiimage.setNormType(index, norm_type)

    
    def set_lut_menu_visible(self, visibility):
        self.multilegend.set_menu_visible(visibility)

    










