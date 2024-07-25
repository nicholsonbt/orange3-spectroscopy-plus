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






def replaceWidget(layout, old_widget, new_widget):
    if old_widget is not None:
        layout.removeWidget(old_widget)
        old_widget.setParent(None)
    
    if new_widget is not None:
        layout.addWidget(new_widget)







class MenuController(QtCore.QObject):
    sigThresholdLowChanged = QtCore.pyqtSignal(float)
    sigThresholdHighChanged = QtCore.pyqtSignal(float)
    sigLevelLowChanged = QtCore.pyqtSignal(float)
    sigLevelHighChanged = QtCore.pyqtSignal(float)
    sigPaletteIndexChanged = QtCore.pyqtSignal(int)
    sigPaletteChanged = QtCore.pyqtSignal(np.ndarray)

    sigPlotTypeChanged = QtCore.pyqtSignal(int)
    sigNormTypeChanged = QtCore.pyqtSignal(int)


    PLOT_TYPES = {
        "Auto"      : ImageTypes.LINESCAN,
        "Raster"    : ImageTypes.RASTER,
        "Scatter"   : ImageTypes.SCATTER,
    }

    NORMALISATION_TYPES = {
        "Global"    : ChannelNormalisationTypes.GLOBAL,
        "Channel"   : ChannelNormalisationTypes.PER_CHANNEL,
        "None (1)"  : ChannelNormalisationTypes.NONE_1,
        "None (256)": ChannelNormalisationTypes.NONE_256,
    }


    def __init__(self):
        QtCore.QObject.__init__(self)

        self._is_rgb = None
        self.fixed_levels = None  # fixed level settings for categoric data

        self._palettes = _color_palettes

        self.createGlobalWidget()
        self.createMonoWidget()
        self.createRGBWidget()

        self.box = QtWidgets.QWidget()
        self._layout = QtWidgets.QVBoxLayout()
        self._layout.addWidget(self._glob_widget)
        self.box.setLayout(self._layout)

        self.setIsRGB(False)

    
    def createGlobalWidget(self):
        self._glob_widget = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout(
            formAlignment=QtCore.Qt.AlignLeft,
            labelAlignment=QtCore.Qt.AlignLeft,
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow
        )

        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_type_cb = QtWidgets.QComboBox()
        self.plot_type_cb.addItems(MenuController.PLOT_TYPES)
        self.plot_type_cb.activated.connect(lambda i: self.sigPlotTypeChanged.emit(
            list(MenuController.PLOT_TYPES.items())[i][1]
        ))

        layout.addRow("Plot Type:", self.plot_type_cb)

        self._glob_widget.setLayout(layout)




    def createMonoWidget(self):
        self._mono_widget = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout(
            formAlignment=QtCore.Qt.AlignLeft,
            labelAlignment=QtCore.Qt.AlignLeft,
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow
        )

        layout.setContentsMargins(0, 0, 0, 0)

        self.color_cb = QtWidgets.QComboBox()
        self.color_cb.setIconSize(QtCore.QSize(64, 16))
        model = color_palette_model(self._palettes, self.color_cb.iconSize())
        self.color_cb.setModel(model)
        self.color_cb.activated.connect(self.sigPaletteIndexChanged.emit)
        self.color_cb.activated.connect(lambda i: self.sigPaletteChanged.emit(max(self._palettes[i][1].items())[1]))

        layout.addRow("Colour:", self.color_cb)

        self._mono_widget.setLayout(layout)




    def createRGBWidget(self):
        self._rgb_widget = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout(
            formAlignment=QtCore.Qt.AlignLeft,
            labelAlignment=QtCore.Qt.AlignLeft,
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow
        )

        layout.setContentsMargins(0, 0, 0, 0)

        self.norm_cb = QtWidgets.QComboBox()
        self.norm_cb.addItems(MenuController.NORMALISATION_TYPES)

        self.norm_cb.activated.connect(lambda i: self.sigNormTypeChanged.emit(
            list(MenuController.NORMALISATION_TYPES.items())[i][1]
        ))

        layout.addRow("Normalisation:", self.norm_cb)


        self._rgb_widget.setLayout(layout)
        

    def setIsRGB(self, flag):
        if self._is_rgb == flag:
            return

        if self._is_rgb is None:
            old_widget = None
        elif self._is_rgb:
            old_widget = self._rgb_widget
        elif not self._is_rgb:
            old_widget = self._mono_widget
        else:
            raise Exception("ERROR!!!")

        if flag is None:
            new_widget = None
        elif flag:
            new_widget = self._rgb_widget
        elif not flag:
            new_widget = self._mono_widget
        else:
            raise Exception("ERROR!!!")
        
        replaceWidget(self._layout, old_widget, new_widget)

        self._is_rgb = flag


    def settings_box(self):
        return self.box





        # self.color_cb = gui.comboBox(box, self, "palette_index", label="Color:",
        #                              labelWidth=50, orientation=QtCore.Qt.Horizontal)
        # self.color_cb.setIconSize(QtCore.QSize(64, 16))
        # palettes = _color_palettes
        # model = color_palette_model(palettes, self.color_cb.iconSize())
        # model.setParent(self.parent)
        # self.color_cb.setModel(model)
        # self.palette_index = min(self.palette_index, len(palettes) - 1)
        # self.color_cb.activated.connect(self.update_color_schema)

        # # layout.addWidget(self.color_cb)

        # form = QtWidgets.QFormLayout(
        #     formAlignment=QtCore.Qt.AlignLeft,
        #     labelAlignment=QtCore.Qt.AlignLeft,
        #     fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow
        # )

        # def limit_changed():
        #     self.update_levels()
        #     self.reset_thresholds()

        # self._level_low_le = lineEditDecimalOrNone(self.parent, self, "level_low", callback=limit_changed)
        # self._level_low_le.validator().setDefault(0)
        # form.addRow("Low limit:", self._level_low_le)

        # self._level_high_le = lineEditDecimalOrNone(self.parent, self, "level_high", callback=limit_changed)
        # self._level_high_le.validator().setDefault(1)
        # form.addRow("High limit:", self._level_high_le)

        # self._threshold_low_slider = lowslider = gui.hSlider(
        #     box, self.parent, "threshold_low", minValue=0.0, maxValue=1.0,
        #     step=0.05, ticks=True, intOnly=False,
        #     createLabel=False, callback=self.update_levels)
        # self._threshold_high_slider = highslider = gui.hSlider(
        #     box, self.parent, "threshold_high", minValue=0.0, maxValue=1.0,
        #     step=0.05, ticks=True, intOnly=False,
        #     createLabel=False, callback=self.update_levels)

        # form.addRow("Low:", lowslider)
        # form.addRow("High:", highslider)
        # box.layout().addLayout(form)

        # return box


    def update_levels(self):
        print("Update Levels")
        # if not self.data:
        #     return

        # if self.fixed_levels is not None:
        #     levels = list(self.fixed_levels)
        # elif self.img.image is not None and self.img.image.ndim == 2:
        #     levels = get_levels(self.img.image)
        # elif self.img.image is not None and self.img.image.shape[2] == 1:
        #     levels = get_levels(self.img.image[:, :, 0])
        # elif self.img.image is not None and self.img.image.shape[2] == 3:
        #     return
        # else:
        #     levels = [0, 255]

        # prec = pixels_to_decimals((levels[1] - levels[0])/1000)

        # rounded_levels = [float_to_str_decimals(levels[0], prec),
        #                   float_to_str_decimals(levels[1], prec)]

        # self._level_low_le.validator().setDefault(rounded_levels[0])
        # self._level_high_le.validator().setDefault(rounded_levels[1])

        # self._level_low_le.setPlaceholderText(rounded_levels[0])
        # self._level_high_le.setPlaceholderText(rounded_levels[1])

        # enabled_level_settings = self.fixed_levels is None
        # self._level_low_le.setEnabled(enabled_level_settings)
        # self._level_high_le.setEnabled(enabled_level_settings)
        # self._threshold_low_slider.setEnabled(enabled_level_settings)
        # self._threshold_high_slider.setEnabled(enabled_level_settings)

        # if self.fixed_levels is not None:
        #     self.img.setLevels(self.fixed_levels)
        #     return

        # if not self.threshold_low < self.threshold_high:
        #     # TODO this belongs here, not in the parent
        #     self.parent.Warning.threshold_error()
        #     return
        # else:
        #     self.parent.Warning.threshold_error.clear()

        # ll = float(self.level_low) if self.level_low is not None else levels[0]
        # lh = float(self.level_high) if self.level_high is not None else levels[1]

        # ll_threshold = ll + (lh - ll) * self.threshold_low
        # lh_threshold = ll + (lh - ll) * self.threshold_high

        # self.img.setLevels([ll_threshold, lh_threshold])
        # self.legend.set_range(ll_threshold, lh_threshold)


    def reset_thresholds(self):
        self.threshold_low = 0.
        self.threshold_high = 1.