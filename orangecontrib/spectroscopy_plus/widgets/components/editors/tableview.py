from AnyQt.QtWidgets import QWidget, QGraphicsItem, QPushButton, QMenu, \
    QGridLayout, QAction, QVBoxLayout, QApplication, QWidgetAction, \
    QShortcut, QToolTip, QGraphicsRectItem, QGraphicsTextItem
from AnyQt.QtGui import QColor, QPixmapCache, QPen, QKeySequence, QFontDatabase, \
    QPalette
from AnyQt.QtCore import Qt, QRectF, QPointF, QObject
from AnyQt.QtCore import pyqtSignal

from AnyQt import QtCore, QtGui, QtWidgets

import bottleneck
import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.ViewBox import ViewBox
from pyqtgraph import Point, GraphicsObject

from orangewidget.utils.visual_settings_dlg import VisualSettingsDialog

import Orange.data
from Orange.data import DiscreteVariable
from Orange.widgets.widget import OWWidget, Msg, OWComponent, Input, Output
from Orange.widgets import gui
from Orange.widgets.settings import \
    Setting, ContextSetting, DomainContextHandler, SettingProvider
from Orange.widgets.utils.itemmodels import DomainModel
from Orange.widgets.utils.plot import \
    SELECT, PANNING, ZOOMING
from Orange.widgets.utils import saveplot
from Orange.widgets.visualize.owscatterplotgraph import LegendItem
from Orange.widgets.utils.concurrent import TaskState, ConcurrentMixin
from Orange.widgets.visualize.utils.plotutils import HelpEventDelegate, PlotWidget
from Orange.widgets.visualize.utils.customizableplot import CommonParameterSetter

from orangecontrib.spectroscopy.data import getx
from orangecontrib.spectroscopy.utils import apply_columns_numpy
from orangecontrib.spectroscopy.widgets.line_geometry import \
    distance_curves, intersect_curves_chunked
from orangecontrib.spectroscopy.widgets.gui import pixel_decimals, \
    VerticalPeakLine, float_to_str_decimals as strdec
from orangecontrib.spectroscopy.widgets.utils import \
    SelectionGroupMixin, SelectionOutputsMixin
from orangecontrib.spectroscopy.widgets.visual_settings import FloatOrUndefined

from orangecontrib.spectroscopy.widgets.owhyper import QTest, Domain, Identity, refresh_integral_markings, Integrate, MovableVline, ContinuousVariable

from orangecontrib.spectroscopy.widgets.owspectra import CurvePlot, SELECTNONE




import concurrent.futures
from dataclasses import dataclass
from typing import (
    Optional, Union, Sequence, List, TypedDict, Tuple, Any, Container
)

from scipy.sparse import issparse

from AnyQt.QtWidgets import (
    QTableView, QHeaderView, QApplication, QStyle, QStyleOptionHeader,
    QStyleOptionViewItem
)
from AnyQt.QtGui import QColor, QClipboard, QPainter
from AnyQt.QtCore import (
    Qt, QSize, QMetaObject, QItemSelectionModel, QModelIndex, QRect
)
from AnyQt.QtCore import Slot

from orangewidget.gui import OrangeUserRole

import Orange.data
from Orange.data.table import Table
from Orange.data.sql.table import SqlTable

from Orange.widgets import gui
from Orange.widgets.data.utils.models import RichTableModel, TableSliceProxy
from Orange.widgets.settings import Setting
from Orange.widgets.utils.itemdelegates import TableDataDelegate
from Orange.widgets.utils.tableview import table_selection_to_mime_data
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.widget import OWWidget, Input, Output, Msg
from Orange.widgets.utils.annotated_data import (create_annotated_table,
                                                 ANNOTATED_DATA_SIGNAL_NAME)
from Orange.widgets.utils.itemmodels import TableModel
from Orange.widgets.utils.state_summary import format_summary_details
from Orange.widgets.utils import disconnected
from Orange.widgets.utils.headerview import HeaderView
from Orange.widgets.data.utils.tableview import RichTableView
from Orange.widgets.data.utils import tablesummary as tsummary



from Orange.widgets.data.owtable import _Selection, _Sorting, InputData, \
    DataTableView, SubsetTableDataDelegate, TableBarItemDelegate, _TableModel






class TableView(QWidget, OWComponent):

    def __init__(self, parent=None):
        QWidget.__init__(self)
        OWComponent.__init__(self, parent)

        self.parent = parent

        self.data = None
        self.__have_new_data = False

        self.dist_color = QColor(220, 220, 220, 255)

        view = DataTableView()
        view.setItemDelegate(SubsetTableDataDelegate(view))

        self.view = view

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)

        self.setLayout(layout)

    def sizeHint(self):
        return QSize(800, 500)

    def set_data(self, data: Optional[Table]):
        """Set the input dataset."""

        if data is not None:
            summary = tsummary.table_summary(data)
            self.data = InputData(
                table=data,
                summary=summary,
                model=_TableModel(data)
            )
            if isinstance(summary.len, concurrent.futures.Future):
                def update(_):
                    QMetaObject.invokeMethod(
                        self, "_update_info", Qt.QueuedConnection)
                summary.len.add_done_callback(update)

        else:
            self.data = None

        self.__have_new_data = True


    def handleNewSignals(self):
        if self.__have_new_data:
            self._setup_table_view()

        self._setup_view_delegate()

        if self.__have_new_data:
            self.__have_new_data = False


    def _setup_table_view(self):
        """Setup the view with current input data."""
        if self.data is None:
            self.view.setModel(None)
            return

        datamodel = self.data.model

        view = self.view
        data = self.data.table
        rowcount = data.approx_len()
        view.setModel(datamodel)

        vheader = view.verticalHeader()
        option = view.viewOptions()
        size = view.style().sizeFromContents(
            QStyle.CT_ItemViewItem, option,
            QSize(20, 20), view)

        vheader.setDefaultSectionSize(size.height() + 2)
        vheader.setMinimumSectionSize(5)
        vheader.setSectionResizeMode(QHeaderView.Fixed)

        # Limit the number of rows displayed in the QTableView
        # (workaround for QTBUG-18490 / QTBUG-28631)
        maxrows = (2 ** 31 - 1) // (vheader.defaultSectionSize() + 2)
        if rowcount > maxrows:
            sliceproxy = TableSliceProxy(
                parent=view, rowSlice=slice(0, maxrows))
            sliceproxy.setSourceModel(datamodel)
            # First reset the view (without this the header view retains
            # it's state - at this point invalid/broken)
            view.setModel(None)
            view.setModel(sliceproxy)

        assert view.model().rowCount() <= maxrows
        assert vheader.sectionSize(0) > 1 or datamodel.rowCount() == 0

        self._setup_view_delegate()


    def _setup_view_delegate(self):
        if self.data is None:
            return

        delegate = SubsetTableDataDelegate(self.view)
        delegate.subset_opacity = 1.0
        self.view.setItemDelegate(delegate)






if __name__ == "__main__":  # pragma: no cover
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    data = None
    WidgetPreview(TableView).run(set_data=data)