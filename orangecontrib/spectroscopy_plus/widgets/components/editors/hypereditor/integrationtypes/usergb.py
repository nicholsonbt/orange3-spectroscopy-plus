from Orange.preprocess import transformation

from Orange.widgets import settings, gui

import Orange.data
from Orange.widgets.utils import itemmodels


from orangecontrib.spectroscopy_plus.widgets.components.editors.hypereditor.integrationtypes.base import Base



class UseRGB(Base):
    rgb_red_value = settings.ContextSetting(None)
    rgb_green_value = settings.ContextSetting(None)
    rgb_blue_value = settings.ContextSetting(None)


    def __init__(self, parent):
        Base.__init__(self, parent)

        self.rgb_value_model = itemmodels.DomainModel(
            itemmodels.DomainModel.SEPARATED,
            valid_types=(Orange.data.ContinuousVariable,)
        )

        self.feature_value_model = itemmodels.DomainModel(
            itemmodels.DomainModel.SEPARATED,
            valid_types=itemmodels.DomainModel.PRIMITIVE
        )

        self.box_values_RGB_feature = None
        self.red_feature_value = None
        self.green_feature_value = None
        self.blue_feature_value = None


    def add_radio(self, box):
        self.createRadio(box, "RGB")

        self.box_values_RGB_feature = gui.indentedBox(box)

        self.red_feature_value = gui.comboBox(
            self.box_values_RGB_feature, self, "rgb_red_value",
            contentsLength=12, searchable=True,
            callback=self.update_rgb_value, model=self.rgb_value_model)

        self.green_feature_value = gui.comboBox(
            self.box_values_RGB_feature, self, "rgb_green_value",
            contentsLength=12, searchable=True,
            callback=self.update_rgb_value, model=self.rgb_value_model)

        self.blue_feature_value = gui.comboBox(
            self.box_values_RGB_feature, self, "rgb_blue_value",
            contentsLength=12, searchable=True,
            callback=self.update_rgb_value, model=self.rgb_value_model)
        

    def init_values(self, data):
        domain = data.domain if data is not None else None
        self.rgb_value_model.set_domain(domain)
        self.feature_value_model.set_domain(domain)

        if self.rgb_value_model:
            # Filter PyListModel.Separator objects
            rgb_attrs = [a for a in self.feature_value_model if isinstance(a, Orange.data.ContinuousVariable)]
            if len(rgb_attrs) <= 3:
                rgb_attrs = (rgb_attrs + rgb_attrs[-1:]*3)[:3]
            self.rgb_red_value, self.rgb_green_value, self.rgb_blue_value = rgb_attrs[:3]
        else:
            self.rgb_red_value = self.rgb_green_value = self.rgb_blue_value = None

    
    def image_values(self):
        red = Orange.data.ContinuousVariable(
            "red",
            compute_value=transformation.Identity(self.rgb_red_value)
        )

        green = Orange.data.ContinuousVariable(
            "green",
            compute_value=transformation.Identity(self.rgb_green_value)
        )
        
        blue = Orange.data.ContinuousVariable(
            "blue",
            compute_value=transformation.Identity(self.rgb_blue_value)
        )
        
        return lambda data: data.transform(Orange.data.Domain([red, green, blue]))
    

    def update_rgb_value(self):
        self.redraw_data()

    
    def setDisabled(self, flag):
        Base.setDisabled(self, flag)
        self.box_values_RGB_feature.setDisabled(flag)
