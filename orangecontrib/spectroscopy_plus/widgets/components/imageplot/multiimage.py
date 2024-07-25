import numpy as np
import pyqtgraph as pg

from AnyQt import QtCore, QtGui, QtWidgets

from orangecontrib.spectroscopy_plus.widgets.components.imageplot.imageitem import ImageItem
from orangecontrib.spectroscopy_plus.widgets.components.imageplot.falsecolorlegend import FCLegend

from orangecontrib.spectroscopy.widgets.owspectra import InteractiveViewBox





class MultiImage(pg.GraphicsLayout):
    def __init__(self, parent=None, border=None, **kwargs):
        pg.GraphicsLayout.__init__(self, parent=parent, border=border)

        self.parent = parent

        self.plot = pg.PlotItem(viewBox=InteractiveViewBox(self))
        self.plot.buttonsHidden = True

        self.plots = []
        self.order = []

        self.setOpts(**{
            "aspect_locked"     : True,
            "invert_x"          : False,
            "invert_y"          : False,
            "auto_range"        : True,
            "show_grid"         : (False, False, 1.0),
            "composition_mode"  : QtGui.QPainter.CompositionMode_SourceOver,
        } | kwargs)

        self.refresh()

    

    def setOpts(self, **kwargs):
        def auto_range_func(flag):
            self.plot.vb.state['autoRange'] = [flag, flag]

            if flag:
                self.plot.vb.update()


        options = {
            "aspect_locked"     : self.plot.vb.setAspectLocked,
            "invert_x"          : self.plot.vb.invertX,
            "invert_y"          : self.plot.vb.invertY,
            "auto_range"        : auto_range_func,
            "show_grid"         : lambda args: self.plot.showGrid(*args),
            "composition_mode"  : self.setCompositionMode,
        }

        for k, v in options.items():
            if k in kwargs:
                v(kwargs.get(k))

        self.update()

    
    def setCompositionMode(self, composition_mode, update=True):
        self._composition_mode = composition_mode

        for img in self.plots:
            img.setOpts(composition_mode=composition_mode)



    def setData(self, index, values, coords=None, **kwargs):
        # If new index, append instead of changing existing plot.
        if index == len(self.plots):
            # Coords are required if adding new data
            assert(not coords is None)
            self._appendPlot(values, coords, **kwargs)
            self.order.append(index)
            return
        
        # Get the existing plot.
        img = self.plots[index]

        # If new coords, set coords.
        if not coords is None:
            img.setCoords(coords)

        # Set pixel values and options.
        img.setColours(values)
        img.setOpts(**kwargs)

        self.refresh()


    
    def insertData(self, index, values, coords, **kwargs):
        # Create a new image and LUT.
        img = self._initItems(values, coords, **kwargs)

        # Insert plots.
        self.plots.insert(index, img)
        self.order.insert(index, index)

        self.refresh()


    def removeData(self, index):
        # Remove image and LUT at index.
        self.plots.pop(index)

        # Remove the index from order and reduce all greater by 1.
        self.order.remove(index)
        self.order = [i if i < index else i-1 for i in self.order]

        self.refresh()

    
    def _appendPlot(self, values, coords, **kwargs):
        # Create a new image and LUT.
        img = self._initItems(values, coords, **kwargs)

        self.plots.append(img)

        self.refresh()

    
    def _initItems(self, values, coords, **kwargs):
        img_kwargs = {
            "composition_mode"  : self._composition_mode,
        } | kwargs

        # Initialise image and LUT.
        img = ImageItem(coords, values, **img_kwargs)

        return img
    

    def getBounds(self):
        x0 = x1 = y0 = y1 = None

        for img in self.plots:
            xi0, yi0, wi, hi = img.boundingRect().getRect()
            xi1 = xi0 + wi
            yi1 = yi0 + hi

            if x0 is None or x0 > xi0:
                x0 = xi0

            if y0 is None or y0 > yi0:
                y0 = yi0
            
            if x1 is None or x1 < xi1:
                x1 = xi1

            if y1 is None or y1 < yi1:
                y1 = yi1

        w = x1 - x0
        h = y1 - y0

        return QtCore.QRectF(x0, y0, w, h)

    

    def zoomToFit(self, rect=None):
        if rect is None:
            rect = self.getBounds()

        elif isinstance(rect, int):
            index = self.order[rect]
            rect = self.plots[index].boundingRect()

        self.plot.vb.setRange(rect)


    def move_data(self, from_: int, to_: int, source):
        # Swap the display order at the two indices specified.
        val = self.order.pop(from_)
        self.order.insert(to_, val)

        self.refresh()

    
    
    def refresh(self):
        # Call refresh ASAP.
        QtCore.QTimer.singleShot(0, self._refresh)
        

    def _refresh(self):
        # Clear the plots.
        self.plot.clear()
        self.clear()

        # Add the image plot back in.
        self.addItem(self.plot)

        # Add the images in the correct display order.
        for i in self.order:
            img = self.plots[i]
            self.plot.addItem(img)

            
    def setLookupTable(self, index, palette):
        img = self.plots[index]
        img.setLookupTable(palette)


    def setPlotType(self, index, plot_type):
        img = self.plots[index]
        img.setOpts(image_type=plot_type)


    def setNormType(self, index, norm_type):
        img = self.plots[index]
        img.setOpts(norm_type=norm_type)








