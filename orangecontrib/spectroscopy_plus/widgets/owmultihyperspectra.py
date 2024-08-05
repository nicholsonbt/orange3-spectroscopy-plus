import numpy as np

from typing import List

from AnyQt import QtCore, QtGui, QtWidgets

import pyqtgraph as pg

import Orange.data
from Orange.widgets.settings import DomainContextHandler
from Orange.widgets import widget, gui, settings

from orangecontrib.spectroscopy_plus.utils.plots import setBackgroundColour, collective_domain, CompositionTypes, EnumController
from orangecontrib.spectroscopy_plus.widgets.components.imageplot import MultiPlotLayout
from orangecontrib.spectroscopy_plus.widgets.components.editors import HyperEditor

from orangecontrib.spectroscopy.widgets.owspectra import MenuFocus

from Orange.widgets.utils.itemmodels import DomainModel



from Orange.data.util import get_unique_names

from Orange.widgets.utils import saveplot

from Orange.widgets.utils.concurrent import ThreadExecutor, FutureWatcher




class Task:
    future = None
    watcher = None
    cancelled = False

    def __init__(self, future, watcher):
        self.future = future
        self.watcher = watcher

    def cancel(self):
        self.cancelled = True
        self.future.cancel()


class Status:
    RUNNING = 0
    FINISHED = 1


def getColumn(table, attr):
    if isinstance(attr, str):
        return getColumn(table, table.domain[attr])
    
    return table.get_column(attr)


def getCoords(table, attr_x, attr_y):
    return np.vstack([
        getColumn(table, attr_x),
        getColumn(table, attr_y),
    ]).T



def newAction(title, parent, checked=None, callback=None, shortcuts=None):
    action = QtWidgets.QAction(title, parent)

    if checked is not None:
        action.setCheckable(True)
        action.setChecked(checked)

    if callback is not None:
        action.triggered.connect(callback)

        if checked is not None:
            QtCore.QTimer.singleShot(0, lambda: callback(checked))

    if shortcuts is not None:
        action.setShortcuts(shortcuts)
        action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

    return action


### Unlink axis_model.
class OWMultiPlot(widget.OWWidget):
    name = "MultiHyperSpectra"

    description = "Test description."

    icon = "icons/multihyperspectra.svg"

    class Inputs:
        datas = widget.MultiInput("Datas", Orange.data.Table, default=True)

    class Outputs:
        pass


    want_control_area = False

    settingsHandler = DomainContextHandler()

    hypereditor = settings.SettingProvider(HyperEditor)


    attr_x = settings.ContextSetting(None)
    attr_y = settings.ContextSetting(None)

    axis_model = DomainModel(DomainModel.METAS | DomainModel.CLASSES,
                             valid_types=Orange.data.ContinuousVariable)
    

    def __init__(self):
        widget.OWWidget.__init__(self)

        self.__executor = ThreadExecutor(parent=self)

        self.datas = []
        self.tabs = []
        self.status = []
        self.attr_x = None
        self.attr_y = None

        self.multiplot_layout = MultiPlotLayout(self)

        self.plotview = pg.GraphicsView()
        self.plotview.setBackground("w") ### TODO: Background colour should be based on the theme.
        self.plotview.setCentralItem(self.multiplot_layout)

        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setContentsMargins(0, 0, 0, 0)
        # Move tab by dragging it.
        self.tab_widget.setMovable(True)
        self.tab_widget.tabBar().tabMoved.connect(lambda old, new: self.move_data(old, new, self.tab_widget))
        # Rename tab on double click.
        self.tab_widget.tabBar().tabBarDoubleClicked.connect(self.rename_dialog)

        self.setup_menu()

        splitter = QtWidgets.QSplitter(self)
        splitter.setOrientation(QtCore.Qt.Vertical)
        self.mainArea.layout().addWidget(splitter)

        splitter.addWidget(self.plotview)
        splitter.addWidget(self.tab_widget)


    def move_data(self, from_, to_, source=None):
        if source is None:
            source = self

        if source != self.tab_widget:
            self.tab_widget.tabBar().blockSignals(True)
            self.tab_widget.tabBar().moveTab(from_, to_)
            self.tab_widget.tabBar().blockSignals(False)
        
        if source != self.multiplot_layout:
            self.multiplot_layout.move_data(from_, to_, self)



    def rename_dialog(self, index: int) -> None:
        """Rename tab at index

        Opens dialog to rename tab at the given index. The current name
        used as the default text.

        Parameters
        ----------
        index : int
            Index of the tab to be renamed.
        """
        # Open a popup window to lets the user to change the tab name.
        text, ok = QtWidgets.QInputDialog.getText(
            self,                               # parent
            "Rename:",                          # title
            "New Name:",                        # label
            text=self.tab_widget.tabText(index) # default text
        )

        # If ok selected (not cancel) and the text isn't empty, change
        # the name of the tab.
        if ok and len(text) > 0:
            self.tab_widget.setTabText(index, text)


    def setup_menu(self):
        layout = QtWidgets.QGridLayout()
        self.plotview.setLayout(layout)
        self.button = QtWidgets.QPushButton("Menu", self.plotview)
        self.button.setAutoDefault(False)

        layout.setRowStretch(1, 1)
        layout.setColumnStretch(1, 1)
        layout.addWidget(self.button, 0, 0)
        view_menu = MenuFocus(self)
        self.button.setMenu(view_menu)

        actions = []

        choose_xy = QtWidgets.QWidgetAction(self)
        box = gui.vBox(self)

        box.setContentsMargins(10, 0, 10, 0)
        box.setFocusPolicy(QtCore.Qt.TabFocus)
        self.xy_model = DomainModel(DomainModel.METAS | DomainModel.CLASSES,
                                    valid_types=DomainModel.PRIMITIVE)
        self.cb_attr_x = gui.comboBox(
            box, self, "attr_x",
            contentsLength=12, searchable=True,
            callback=self.attrs_changed, model=self.axis_model
        )
        self.cb_attr_y = gui.comboBox(
            box, self, "attr_y",
            contentsLength=12, searchable=True,
            callback=self.attrs_changed, model=self.axis_model
        )

        box.setFocusProxy(self.cb_attr_x)

        choose_xy.setDefaultWidget(box)

        actions.append(choose_xy)


        actions.append(newAction(
            "Zoom to fit",
            view_menu,
            callback=self.zoomToFit,
            shortcuts=[QtCore.Qt.Key_Backspace, QtGui.QKeySequence(QtCore.Qt.ControlModifier | QtCore.Qt.Key_0)]
        ))

        #### Container:
        container = QtWidgets.QWidget()

        layout = QtWidgets.QFormLayout(
            formAlignment=QtCore.Qt.AlignLeft,
            labelAlignment=QtCore.Qt.AlignLeft,
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow
        )

        layout.setContentsMargins(0, 0, 0, 0)

        self.cb_comp_mode = QtWidgets.QComboBox()
        self.cb_comp_mode.addItems(EnumController.names(CompositionTypes, beautify=True))
        self.cb_comp_mode.activated.connect(lambda i: self.comp_mode_changed(
            EnumController.value(CompositionTypes, i)
        ))

        layout.addRow("Composition:", self.cb_comp_mode)

        container.setLayout(layout)

        action = QtWidgets.QWidgetAction(self)

        action.setDefaultWidget(container)
        actions.append(action)

        actions.append(newAction(
            "Save Graph",
            view_menu,
            callback=self.save_graph,
            shortcuts=[QtGui.QKeySequence(QtCore.Qt.ControlModifier | QtCore.Qt.Key_I)]
        ))


        actions.append(newAction(
            "Show Legend Menus",
            view_menu,
            checked=True,
            callback=self.set_lut_menu_visible,
        ))

        actions.append(newAction(
            "Invert X",
            view_menu,
            checked=False,
            callback=self.set_invert_x,
            shortcuts=[QtCore.Qt.Key_X]
        ))

        actions.append(newAction(
            "Invert Y",
            view_menu,
            checked=False,
            callback=self.set_invert_y,
            shortcuts=[QtCore.Qt.Key_Y]
        ))


        for action in actions:
            view_menu.addAction(action)
            self.plotview.addAction(action)


        
        



    def init_models(self):
        domain = collective_domain(*[data.domain for data in self.datas if data is not None])
        self.axis_model.set_domain(domain)

        self.attr_x = self.axis_model[0] if self.axis_model else None
        self.attr_y = self.axis_model[1] if len(self.axis_model) >= 2 \
            else self.attr_x
        

    def zoomToFit(self):
        self.multiplot_layout.zoomToFit()

    
    def save_graph(self):
        saveplot.save_plot(self.plotview, self.graph_writers)


    def set_lut_menu_visible(self, checked):
        self.multiplot_layout.set_lut_menu_visible(checked)

    
    def set_invert_x(self, checked):
        self.multiplot_layout.setOpts(invert_x=checked)

    
    def set_invert_y(self, checked):
        self.multiplot_layout.setOpts(invert_y=checked)


    def comp_mode_changed(self, comp_mode):
        self.multiplot_layout.setCompositionMode(comp_mode)

    
    def attrs_changed(self):
        for i in range(len(self.datas)):
            self.compute(i)


    def compute(self, index):
        future = self.__executor.submit(
            self._compute_coords,
            index,
            self.datas[index],
            self.attr_x,
            self.attr_y,
        )

        watcher = FutureWatcher(future)
        watcher.resultReady.connect(self.__task_complete)
        watcher.exceptionReady.connect(self.__on_exception)
        watcher.done.connect(self.__task_finished)

        self.status[index] = Task(future, watcher)
        self.progressBarInit()



    def __on_exception(self, *args):
        ### TODO: FIXME
        assert QtCore.QThread.currentThread() is self.thread()

        if len(args) == 1:
            idx = None
            ex = args[0]
        elif len(args) == 2:
            idx, ex = args
            assert isinstance(self.status[idx], Task)
        else:
            idx = ex = None

        print("!!!", idx, ex)
        print("ERROR!", idx, ex)


    def __task_complete(self, result):
        assert QtCore.QThread.currentThread() is self.thread()

        index, coords = result
        kwargs = dict()

        assert isinstance(self.status[index], Task)

        self.status[index] = Status.FINISHED

        editor = self.tabs[index]
        data = self.datas[index]

        if data is None:
            return
        
        lut = editor.lut_colours()
        if lut is not None:
            kwargs["lut_colours"] = lut

        colours = editor.image_values()(data)

        if isinstance(colours, Orange.data.Table):
            colours = colours.X

        self.multiplot_layout.setData(index, colours, coords, **kwargs)


    def __task_finished(self):
        assert QtCore.QThread.currentThread() is self.thread()

        self.progressBarFinished()


    def cancel(self):
        for task in self.status:
            if isinstance(task , Task):
                task.cancel()

                task.watcher.resultReady.disconnect(self.__task_complete)
                task.watcher.exceptionReady.disconnect(self.__on_exception)
                task.watcher.done.disconnect(self.__task_finished)

                self.progressBarFinished()
    

    @staticmethod
    def _compute_coords(index, data, attr_x, attr_y):
        if data is None or attr_x is None or attr_y is None:
            return index, None

        return index, getCoords(data, attr_x, attr_y)
    


    def get_names(self) -> List[str]:
        """Get all current tab names.

        _extended_summary_

        Returns
        -------
        List[str]
            _description_
        """
        return [self.tab_widget.tabText(i) for i in range(len(self.tabs))]
    

    def unique_name(self, name):
        return get_unique_names(self.get_names(), name)


    @Inputs.datas
    def set_data(self, index, data):
        self.datas[index] = data
        self.status[index] = Status.FINISHED
        
        self.init_models()
        self.compute(index)

        self.tabs[index].set_data(data)

        if data is None or not hasattr(data, "name"):
            name = "N/A"
        else:
            name = self.unique_name(data.name)

        self.tab_widget.setTabText(index, name)


    @Inputs.datas.insert
    def insert_data(self, index, data):
        self.datas.insert(index, data)
        self.status.insert(index, Status.FINISHED)
        
        # Add curveplot tab.
        tab = HyperEditor(self)
        setBackgroundColour(self, tab)

        tab.updated.connect(lambda index=index: self.integrationTypeUpdated(index))

        self.tabs.append(tab)

        if data is None or not hasattr(data, "name"):
            name = "N/A"
        else:
            name = self.unique_name(data.name)

        self.tab_widget.addTab(tab, name)

        self.init_models()
        self.compute(index)

        self.tabs[index].set_data(data)


    @Inputs.datas.remove
    def remove_data(self, index):
        self.datas.pop(index)
        self.tabs.pop(index)
        task = self.status.pop(index)

        if isinstance(task, Task):
            task.cancel()

        self.tab_widget.removeTab(index)
        self.multiplot_layout.removeData(index)
        
        self.init_models()


    def integrationTypeUpdated(self, index):
        self.updateColours(index)


    def updateColours(self, index):
        if self.status[index] != Status.FINISHED:
            return
        
        kwargs = dict()
        
        editor = self.tabs[index]
        data = self.datas[index]

        colours = editor.image_values()(data)

        lut = editor.lut_colours()
        if lut is not None:
            kwargs["lut_colours"] = lut
            print(lut)


        if isinstance(colours, Orange.data.Table):
            colours = colours.X

        # print(editor.image_values_fixed_levels())

        self.multiplot_layout.setData(index, colours, **kwargs)


    def commit(self):
        pass



def createTable(coords, values):
    domain = Orange.data.Domain(
        [
            Orange.data.ContinuousVariable(name=f"x{i}") for i in range(values.shape[1])
        ],
        metas=[
            Orange.data.ContinuousVariable(name="map_x"),
            Orange.data.ContinuousVariable(name="map_y"),
        ]
    )

    return Orange.data.Table.from_numpy(domain, values, metas=coords)





if __name__ == "__main__":  # pragma: no cover
    # from Orange.widgets.utils.widgetpreview import WidgetPreview
    
    # lss0 = [
    #     (120, 360, 100),
    #     (-40, 60, 100),
    # ]

    # lss1 = [
    #     (0, 50, 20),
    #     (-5, 10, 10),
    # ]

    # lss2 = [
    #     (200, 300, 10),
    #     (1, 1, 1),
    # ]

    # coords0, values0, colours0 = generateData(*lss0, rot=10, radians=False)
    # coords1, values1, colours1 = generateData(*lss1)
    # coords2, values2, colours2 = generateData(*lss2, rot=-30, radians=False)

    # table0 = createTable(coords0, values0[:,:1])
    # table1 = createTable(coords1, values1)
    # table2 = createTable(coords2, values2)

    # WidgetPreview(OWMultiPlot).run(insert_data=[
    #     # (0, data),
    #     (0, table0),
    #     (1, table1),
    #     (2, table2)
    # ])
    pass