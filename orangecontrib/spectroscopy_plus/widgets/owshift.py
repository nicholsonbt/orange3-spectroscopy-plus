
from AnyQt import QtWidgets, QtCore

import Orange.data

from Orange.widgets import gui, widget, settings

from Orange.widgets.utils.itemmodels import DomainModel

from orangecontrib.spectroscopy_plus.widgets.components.widgets import LineEdit




class OWShift(widget.OWWidget):
    name = "Shift"

    class Inputs:
        data = widget.Input("Data", Orange.data.Table, default=True)

    class Outputs:
        data = widget.Output("Data", Orange.data.Table, default=True)

    icon = "icons/shift.svg"
    priority = 20


    attr_x = settings.ContextSetting(None)
    attr_y = settings.ContextSetting(None)

    visimg_offset_x = settings.Setting(0.0)
    visimg_offset_y = settings.Setting(0.0)

    offset_x = settings.Setting(0.0)
    offset_y = settings.Setting(0.0)

    autocommit = settings.Setting(True)

    axis_model = DomainModel(DomainModel.METAS | DomainModel.CLASSES,
                             valid_types=Orange.data.ContinuousVariable)

    want_main_area = False
    resizing_enabled = False


    class Information(widget.OWWidget.Information):
        no_visible_image = widget.Msg("No visible image found")


    def __init__(self):
        super().__init__()

        self.data = None

        self.attr_x = None
        self.attr_y = None

        self._setup_xy_attributes()
        self._setup_shift_data()
        self._setup_shift_visimgs()

        gui.auto_commit(self.controlArea, self, "autocommit", "Send Data")

    
    def _setup_xy_attributes(self):
        attrs = gui.widgetBox(self.controlArea, "XY Attributes")

        self.xy_model = DomainModel(DomainModel.METAS | DomainModel.CLASSES,
                                    valid_types=DomainModel.PRIMITIVE)
        self.cb_attr_x = gui.comboBox(
            attrs, self, "attr_x",
            contentsLength=12, searchable=True,
            callback=self.setting_changed, model=self.axis_model
        )
        self.cb_attr_y = gui.comboBox(
            attrs, self, "attr_y",
            contentsLength=12, searchable=True,
            callback=self.setting_changed, model=self.axis_model
        )


    def _setup_shift_data(self):
        offset = gui.widgetBox(self.controlArea, "Shift Data (All)")

        x_box = QtWidgets.QHBoxLayout()
        x_label = QtWidgets.QLabel("X Offset:")
        x_offset = LineEdit(self, "offset_x", callback=self.setting_changed, callbackOnType=True)
        x_box.addWidget(x_label)
        x_box.addWidget(x_offset)

        y_box = QtWidgets.QHBoxLayout()
        y_label = QtWidgets.QLabel("Y Offset:")
        y_offset = LineEdit(self, "offset_y", callback=self.setting_changed, callbackOnType=True)
        y_box.addWidget(y_label)
        y_box.addWidget(y_offset)

        offset.layout().addLayout(x_box)
        offset.layout().addLayout(y_box)

    
    def _setup_shift_visimgs(self):
        visimg = gui.widgetBox(self.controlArea, "Shift Visible Images")

        x_box = QtWidgets.QHBoxLayout()
        x_label = QtWidgets.QLabel("X Offset:")
        x_offset = LineEdit(self, "visimg_offset_x", callback=self.setting_changed, callbackOnType=True)
        x_box.addWidget(x_label)
        x_box.addWidget(x_offset)

        y_box = QtWidgets.QHBoxLayout()
        y_label = QtWidgets.QLabel("Y Offset:")
        y_offset = LineEdit(self, "visimg_offset_y", callback=self.setting_changed, callbackOnType=True)
        y_box.addWidget(y_label)
        y_box.addWidget(y_offset)

        visimg.layout().addLayout(x_box)
        visimg.layout().addLayout(y_box)


    def init_models(self):
        domain = self.data.domain if self.data is not None else None
        self.axis_model.set_domain(domain)

        self.attr_x = self.axis_model[0] if self.axis_model else None
        self.attr_y = self.axis_model[1] if len(self.axis_model) >= 2 \
            else self.attr_x


    def get_outdata(self):
        if self.data is None:
            return None
        
        if "visible_images" not in self.data.attributes:
            self.Information.no_visible_image()
            return self.data
        
        new_data = self.data.copy()

        if self.offset_x != 0 or self.offset_y != 0:
            x_col = new_data.get_column(self.attr_x) - float(self.offset_x)
            new_data.set_column(self.attr_x, x_col)

            y_col = new_data.get_column(self.attr_y) - float(self.offset_y)
            new_data.set_column(self.attr_y, y_col)
            
        visimg_offset_x = self.visimg_offset_x + self.offset_x
        visimg_offset_y = self.visimg_offset_y + self.offset_y

        if visimg_offset_x != 0 or visimg_offset_y != 0:
            images = new_data.attributes["visible_images"]

            for image in images:
                if isinstance(image, dict):
                    # spectroscopy<=0.6.14
                    image["pos_x"] -= float(visimg_offset_x)
                    image["pos_y"] -= float(visimg_offset_y)
                else:
                    # spectroscopy>=0.6.15
                    image.pos_x -= float(visimg_offset_x)
                    image.pos_y -= float(visimg_offset_y)

        return new_data
    

    def setting_changed(self):
        if self.data is not None:
            self.commit.deferred()


    @Inputs.data
    def set_data(self, data):
        self.Information.no_visible_image.clear()
        self.data = data
        self.init_models()
        self.commit.now()


    @gui.deferred
    def commit(self):
        outdata = self.get_outdata()
        self.Outputs.data.send(outdata)




if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(OWShift).run()
