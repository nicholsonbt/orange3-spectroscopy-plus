from AnyQt import QtCore, QtGui, QtWidgets
from orangewidget.widget import OWBaseWidget
from orangewidget import gui




class OWEditor(QtWidgets.QWidget):
    want_control_area = True
    want_main_area = True

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self)

        self.parent = parent

        ## set_basic_layout without buttons or message_bar.
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(2, 2, 2, 2)

        self._insert_splitter()
        if self.want_control_area:
            self._insert_control_area()
        if self.want_main_area:
            self._insert_main_area()


        


    @property
    def settingsHandler(self):
        return self.parent.settingsHandler
    
    @property
    def contextAboutToBeOpened(self):
        return self.parent.contextAboutToBeOpened
    
    @property
    def connect_control(self):
        return self.parent.connect_control

    
    def _insert_splitter(self):
        self.__splitter = OWBaseWidget._Splitter(QtCore.Qt.Horizontal, self)
        self.layout().addWidget(self.__splitter)


    def _insert_control_area(self):
        self.left_side = gui.vBox(self.__splitter, spacing=0)
        if self.want_main_area:
            self.left_side.setSizePolicy(
                QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

            scroll_area = gui.VerticalScrollArea(self.left_side)
            scroll_area.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                      QtWidgets.QSizePolicy.Preferred)
            self.controlArea = gui.vBox(scroll_area, spacing=6,
                                        sizePolicy=(QtWidgets.QSizePolicy.MinimumExpanding,
                                                    QtWidgets.QSizePolicy.Preferred))
            scroll_area.setWidget(self.controlArea)

            self.left_side.layout().addWidget(scroll_area)

            m = 4, 4, 0, 4
        else:
            self.controlArea = gui.vBox(self.left_side, spacing=6)

            m = 4, 4, 4, 4


        self.controlArea.layout().setContentsMargins(*m)


    def _insert_main_area(self):
        self.mainArea = gui.vBox(
            self.__splitter, spacing=6,
            sizePolicy=QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        )
        self.__splitter.addWidget(self.mainArea)
        self.__splitter.setCollapsible(
            self.__splitter.indexOf(self.mainArea), False)
        if self.want_control_area:
            self.mainArea.layout().setContentsMargins(
                0, 4, 4, 4)
            self.__splitter.setSizes([1, QtWidgets.QWIDGETSIZE_MAX])
        else:
            self.mainArea.layout().setContentsMargins(
                4, 4, 4, 4)
