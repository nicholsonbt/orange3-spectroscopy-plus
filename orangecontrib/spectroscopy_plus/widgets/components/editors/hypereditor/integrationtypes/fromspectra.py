from Orange.preprocess import transformation

from Orange.widgets import settings, gui

import Orange.data
from Orange.widgets.utils import itemmodels

from orangecontrib.spectroscopy.preprocess import Integrate

from orangecontrib.spectroscopy_plus.widgets.components.editors.hypereditor.integrationtypes.base import Base

from orangecontrib.spectroscopy.widgets.gui import MovableVline


class FromSpectra(Base):
    integration_method = settings.Setting(0)
    integration_methods = Integrate.INTEGRALS

    lowlim = settings.Setting(None)
    highlim = settings.Setting(None)
    choose = settings.Setting(None)
    lowlimb = settings.Setting(None)
    highlimb = settings.Setting(None)


    def __init__(self, parent):
        Base.__init__(self, parent)

        self.box_values_spectra = None

        self.line1 = MovableVline(position=self.lowlim, label="", report=self.parent.curveplot)
        self.line1.sigMoved.connect(lambda v: setattr(self, "lowlim", v))
        self.line2 = MovableVline(position=self.highlim, label="", report=self.parent.curveplot)
        self.line2.sigMoved.connect(lambda v: setattr(self, "highlim", v))
        self.line3 = MovableVline(position=self.choose, label="", report=self.parent.curveplot)
        self.line3.sigMoved.connect(lambda v: setattr(self, "choose", v))
        self.line4 = MovableVline(position=self.choose, label="baseline", report=self.parent.curveplot,
                                  color=(255, 140, 26))
        self.line4.sigMoved.connect(lambda v: setattr(self, "lowlimb", v))
        self.line5 = MovableVline(position=self.choose, label="baseline", report=self.parent.curveplot,
                                  color=(255, 140, 26))
        self.line5.sigMoved.connect(lambda v: setattr(self, "highlimb", v))

        for line in [self.line1, self.line2, self.line3, self.line4, self.line5]:
            line.sigMoveFinished.connect(self.changed_integral_range)
            self.parent.curveplot.add_marking(line)
            line.hide()


        self.disable_integral_range = False


    def add_radio(self, box):
        self.createRadio(box, "From spectra")

        self.box_values_spectra = gui.indentedBox(box)

        gui.comboBox(
            self.box_values_spectra, self, "integration_method",
            items=(a.name for a in self.integration_methods),
            callback=self._change_integral_type)
        

    def init_values(self, data):
        self._init_integral_boundaries()

    
    def image_values(self):
        imethod = self.integration_methods[self.integration_method]

        if imethod == Integrate.Separate:
            return Integrate(methods=imethod,
                                limits=[[self.lowlim, self.highlim,
                                        self.lowlimb, self.highlimb]])
        elif imethod != Integrate.PeakAt:
            return Integrate(methods=imethod,
                                limits=[[self.lowlim, self.highlim]])
        else:
            return Integrate(methods=imethod,
                                limits=[[self.choose, self.choose]])
        
    

    def _change_integration(self):
        # change what to show on the image
        self.parent._update_integration_type()
        self.redraw_data()

    def changed_integral_range(self):
        if self.disable_integral_range:
            return
        self.redraw_data()


    def _change_integral_type(self):
        self._change_integration()
        

    def _init_integral_boundaries(self):
        # requires data in curveplot
        self.disable_integral_range = True
        if self.parent.curveplot.data_x is not None and len(self.parent.curveplot.data_x):
            minx = self.parent.curveplot.data_x[0]
            maxx = self.parent.curveplot.data_x[-1]
        else:
            minx = 0.
            maxx = 1.

        if self.lowlim is None or not minx <= self.lowlim <= maxx:
            self.lowlim = minx
        self.line1.setValue(self.lowlim)

        if self.highlim is None or not minx <= self.highlim <= maxx:
            self.highlim = maxx
        self.line2.setValue(self.highlim)

        if self.choose is None:
            self.choose = (minx + maxx)/2
        elif self.choose < minx:
            self.choose = minx
        elif self.choose > maxx:
            self.choose = maxx
        self.line3.setValue(self.choose)

        if self.lowlimb is None or not minx <= self.lowlimb <= maxx:
            self.lowlimb = minx
        self.line4.setValue(self.lowlimb)

        if self.highlimb is None or not minx <= self.highlimb <= maxx:
            self.highlimb = maxx
        self.line5.setValue(self.highlimb)

        self.disable_integral_range = False


    def validData(self, data):
        if data is not None and data.X.shape[1] == 1:
            return False

        return True

    
    def setDisabled(self, flag):
        Base.setDisabled(self, flag)

        self.line1.hide()
        self.line2.hide()
        self.line3.hide()
        self.line4.hide()
        self.line5.hide()

        self.box_values_spectra.setDisabled(flag)

        if not flag:
            if self.integration_methods[self.integration_method] != Integrate.PeakAt:
                self.line1.show()
                self.line2.show()
            else:
                self.line3.show()
            if self.integration_methods[self.integration_method] == Integrate.Separate:
                self.line4.show()
                self.line5.show()
    
    
