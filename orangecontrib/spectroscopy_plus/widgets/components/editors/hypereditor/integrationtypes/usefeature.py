from Orange.preprocess import transformation

from Orange.widgets import settings, gui

import Orange.data
from Orange.widgets.utils import itemmodels

from orangecontrib.spectroscopy_plus.widgets.components.editors.hypereditor.integrationtypes.base import Base


class UseFeature(Base):
    attr_value = settings.ContextSetting(None)


    def __init__(self, parent):
        Base.__init__(self, parent)

        self.feature_value_model = itemmodels.DomainModel(
            itemmodels.DomainModel.SEPARATED,
            valid_types=itemmodels.DomainModel.PRIMITIVE
        )

        self.box_values_feature = None
        self.feature_value = None


    def add_radio(self, box):
        self.createRadio(box, "Use Feature")

        self.box_values_feature = gui.indentedBox(box)

        self.feature_value = gui.comboBox(
            self.box_values_feature, self, "attr_value",
            contentsLength=12, searchable=True,
            callback=self.update_feature_value, model=self.feature_value_model)
        

    def init_values(self, data):
        domain = data.domain if data is not None else None
        self.feature_value_model.set_domain(domain)

        self.attr_value = self.feature_value_model[0] if self.feature_value_model else None

    
    def lut_colours(self):
        print(self.attr_value, type(self.attr_value))
        if isinstance(self.attr_value, Orange.data.DiscreteVariable):
            return self.attr_value.colors

        return super().lut_colours()

    
    def image_values(self):
        return lambda data, attr=self.attr_value: data.transform(Orange.data.Domain([data.domain[attr]]))
    

    def image_values_fixed_levels(self):
        if isinstance(self.attr_value, Orange.data.DiscreteVariable):
            return 0, len(self.attr_value.values) - 1
        return None
    

    def update_feature_value(self):
        self.redraw_data()

    
    def setDisabled(self, flag):
        Base.setDisabled(self, flag)
        self.box_values_feature.setDisabled(flag)
