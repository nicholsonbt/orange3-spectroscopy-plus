import numpy as np
import pyqtgraph as pg

from AnyQt import QtCore, QtGui, QtWidgets

from orangecontrib.spectroscopy_plus.widgets.components.imageplot.imageitem import ImageItem
from orangecontrib.spectroscopy_plus.widgets.components.imageplot.falsecolorlegend import FCLegend

from orangecontrib.spectroscopy.widgets.owspectra import InteractiveViewBox







class MultiLegend(pg.GraphicsLayout):
    sigIndexChanged = QtCore.pyqtSignal(int, int)

    def __init__(self, parent=None, border=None, **kwargs):
        pg.GraphicsLayout.__init__(self, parent=parent, border=border)

        self.parent = parent

        self._visible_menus = True
        
        self.luts = []
        self.order = []

        self.setOpts(**{
        } | kwargs)

        self.refresh()

    

    def setOpts(self, **kwargs):
        pass
    

    def setData(self, index, values, coords=None, **kwargs):
        # If new index, append instead of changing existing plot.
        if index == len(self.luts):
            # Coords are required if adding new data
            assert(not coords is None)
            self._appendPlot(values, coords, **kwargs)
            self.order.append(index)
            return
        
        # Get the existing lut.
        lut = self.luts[index]

        # Create LUT.
        lut.setData(hist_data=values, **kwargs)

        self.refresh()

    
    def getPositions(self):
        return [self.luts[i].pos().x() for i in self.order]


    
    def insertData(self, index, values, coords, **kwargs):
        # Create a new image and LUT.
        lut = self._initItems(values, coords, **kwargs)

        # Insert plots.
        self.luts.insert(index, lut)
        self.order.insert(index, index)

        self.refresh()


    def removeData(self, index):
        # Remove image and LUT at index.
        self.luts.pop(index)

        # Remove the index from order and reduce all greater by 1.
        self.order.remove(index)
        self.order = [i if i < index else i-1 for i in self.order]

        self.refresh()

    def swapData(self, index_0, index_1):
        # Swap the display order at the two indices specified.
        self.order[index_0], self.order[index_1] = (
            self.order[index_1],
            self.order[index_0],
        )

        self.refresh()

    
    def _appendPlot(self, values, coords, **kwargs):
        # Create a new image and LUT.
        lut = self._initItems(values, coords, **kwargs)

        self.luts.append(lut)

        self.refresh()

    
    def _initItems(self, values, coords, **kwargs):
        lut_kwargs = {} | kwargs | {}

        # Initialise image and LUT.
        lut = FCLegend(hist_data=values, **lut_kwargs)

        lut.sigPaletteChanged.connect(
            lambda palette, lut=lut: self.parent.setLookupTable(
                self.get_index(lut),
                palette
            )
        )

        lut.sigPlotTypeChanged.connect(
            lambda plot_type, lut=lut: self.parent.setPlotType(
                self.get_index(lut),
                plot_type
            )
        )

        lut.sigNormTypeChanged.connect(
            lambda norm_type, lut=lut: self.parent.setNormType(
                self.get_index(lut),
                norm_type
            )
        )

        lut.sigZoomToFit.connect(
            lambda lut=lut: self.parent.zoomToFit(
                self.get_index(lut)
            )
        )

        lut.sigMoving.connect(
            lambda flag: self.lut_moving(
                flag
            )
        )

        lut.set_menu_visible(self._visible_menus)

        return lut
    

    def set_menu_visible(self, visible):
        self._visible_menus = visible

        for lut in self.luts:
            lut.set_menu_visible(visible)
    

    def move_data(self, from_: int, to_: int, source=None):
        if source is None:
            source = self

        if source != self.parent:
            self.parent.move_data(from_, to_, self)

        val = self.order.pop(from_)
        self.order.insert(to_, val)

        self._refresh()

    
    def lut_moving(self, flag):
        def get_moved(arr):
            try:
                a = next(i for i in range(1, len(arr)) if arr[i] < arr[i-1])
            except StopIteration:
                # 1
                return (None, None)
            
            b = next(i for i in range(len(arr)) if arr[i] > arr[a])
            
            return a, b
        
        if not flag:
            a, b = get_moved(self.getPositions())

            if a is not None:
                self.move_data(a, b)
            
            else:
                self._refresh()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sizeChanged()


    def sizeChanged(self):
        if not hasattr(self, "luts"):
            return
        
        x0 = self.pos().x()
        x1 = x0 + self.size().width()
        
        for lut in self.luts:
            lut.setMoveBounds(x0, x1)


    def get_index(self, lut):
        for i, l in enumerate(self.luts):
            if l == lut:
                return i
        
        return -1
    
    
    def refresh(self):
        # Call refresh ASAP.
        QtCore.QTimer.singleShot(0, self._refresh)
        

    def _refresh(self):
        self.clear()

        # Add the images and LUTs in the correct display order.
        for i in self.order:
            lut = self.luts[i]
            self.addItem(lut)

        self.update()

        self.sizeChanged()









