import numpy as np

from AnyQt import QtWidgets, QtCore

import Orange.data

from Orange.widgets import gui, widget, settings

from Orange.widgets.utils.itemmodels import DomainModel

from orangecontrib.spectroscopy_plus.widgets.components.widgets import LineEdit


def improved_binning(values, step_size, k):
    lower = np.min(values) - step_size
    upper = np.max(values) + step_size
    n = int(np.round((upper - lower) / step_size, decimals=0)) + 2

    print(n)

    ls = np.linspace(lower, upper, n)

    sub_step = step_size / k

    min_i_s = []
    min_c = None

    for i in range(k):
        edges = ls + sub_step * i
        digitized = np.digitize(values, edges)
        count = np.unique(digitized).size

        if min_c is None or min_c > count:
            min_c = count
            min_i_s = [i]

        elif min_c == count:
            min_i_s.append(i)

    i = np.median(min_i_s)
    edges = ls + sub_step * i
    digitized = np.digitize(values, edges)

    left = edges[digitized-1]
    right = edges[digitized]

    return (left + right) / 2




def bin_combine(xs, ys, n=10):
    order = np.argsort(xs, axis=1)

    min_step_size = np.median(np.diff(xs[:, order], axis=1)) / 10

    new_xs = np.take_along_axis(xs, order, axis=1)
    new_ys = np.take_along_axis(ys, order, axis=1)
    step_sizes = np.median(np.diff(new_xs, axis=1), axis=1)
    step_size = max(np.median(step_sizes), min_step_size)

    binned = improved_binning(xs.flatten(), step_size / n, n).reshape(xs.shape)

    new_xs, inverse = np.unique(binned, return_inverse=True)
    indices = inverse.reshape(binned.shape)

    new_ys = np.full((xs.shape[0], new_xs.size), fill_value=np.nan)

    new_ys[np.arange(xs.shape[0])[:, np.newaxis], indices] = ys

    return new_xs, new_ys


def get_xys(x, ys, x_off, y_off):
    new_xs, new_ys = bin_combine(
        np.array([x + float(x_off)*i for i in range(ys.shape[0])]),
        np.array([y + float(y_off)*i for i, y in enumerate(ys[::-1,:])])
    )

    return new_xs, new_ys[::-1,:]




class OWTransform(widget.OWWidget):
    name = "Transform"

    class Inputs:
        data = widget.Input("Data", Orange.data.Table, default=True)

    class Outputs:
        data = widget.Output("Data", Orange.data.Table, default=True)

    icon = "icons/shift.svg"
    priority = 20


    offset_x = settings.Setting(0.0)
    offset_y = settings.Setting(0.0)

    autocommit = settings.Setting(True)


    want_main_area = False
    resizing_enabled = False


    class Information(widget.OWWidget.Information):
        no_visible_image = widget.Msg("No visible image found")


    def __init__(self):
        super().__init__()

        self.data = None

        self._setup_transform_data()

        gui.auto_commit(self.controlArea, self, "autocommit", "Send Data")



    def _setup_transform_data(self):
        offset = gui.widgetBox(self.controlArea, "Transform Data")

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



    def get_outdata(self):
        if self.data is None:
            return None
        
        wavenumbers = np.array([float(attr.name) for attr in self.data.domain.attributes])
        order = np.argsort(wavenumbers)

        x = wavenumbers[order]
        ys = self.data.X[:, order]

        x, ys = get_xys(x, ys, self.offset_x, self.offset_y)

        domain = Orange.data.Domain(
            [Orange.data.ContinuousVariable(name=str(w)) for w in x],
            class_vars = self.data.domain.class_vars,
            metas = self.data.domain.metas
        )

        outdata = Orange.data.Table.from_numpy(domain, ys, self.data.Y, self.data.metas)

        # print(xs)



        # if self.offset_x != 0 or self.offset_y != 0:
        #     x_col = new_data.get_column(self.attr_x) - float(self.offset_x)
        #     new_data.set_column(self.attr_x, x_col)

        #     y_col = new_data.get_column(self.attr_y) - float(self.offset_y)
        #     new_data.set_column(self.attr_y, y_col)
            

        return outdata
    

    def setting_changed(self):
        if self.data is not None:
            self.commit.deferred()


    @Inputs.data
    def set_data(self, data):
        self.Information.no_visible_image.clear()
        self.data = data
        self.commit.now()


    @gui.deferred
    def commit(self):
        outdata = self.get_outdata()
        self.Outputs.data.send(outdata)




if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(OWTransform).run()
