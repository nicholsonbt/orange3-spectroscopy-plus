from Orange.widgets import gui, widget




class Base(widget.OWComponent):
    def __init__(self, parent):
        widget.OWComponent.__init__(self, parent)
        self.parent = parent

        self._allowed = True
        self._enabled = False
        self.radio = None


    def createRadio(self, box, name):
        self.radio = gui.appendRadioButton(box, name)


    def add_radio(self, box):
        raise NotImplementedError()
    

    def init_values(self, data):
        pass
    

    def image_values(self):
        raise NotImplementedError()
    

    def image_values_fixed_levels(self):
        return None
    
    def lut_colours(self):
        return None
    

    def setDisabled(self, flag):
        # If not allowed, but trying to enable, raise an error.
        if not self._allowed and not flag:
            raise Exception("Not allowed to enable.")
    

    def validData(self, data):
        return True
    

    def setAllowed(self, flag):
        self._allowed = flag

        if self._allowed:
            self.radio.setCheckable(True)
            self.radio.setEnabled(True)

        else:
            self.radio.setCheckable(False)
            self.radio.setEnabled(False)
    

    def redraw_data(self):
        self.parent.redraw_data()
