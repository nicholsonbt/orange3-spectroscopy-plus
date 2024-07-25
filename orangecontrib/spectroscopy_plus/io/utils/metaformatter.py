from datetime import datetime




class MetaKeyException(Exception):
    pass


class MetaFormatter:
    class FileFormat:
        NEA_TXT = 0
        NEA = 1


    class Default:
        @staticmethod
        def ERROR(*values):
            # Raise the last caught exception.
            raise

        @staticmethod
        def NONE(*values):
            return None, None
        
        @staticmethod
        def BASIC(*values):
            return None, " ".join(values)
        

    FUNCS = {
        "Scan" : lambda *values: (None, " ".join(values)),

        "Project" : lambda *values: (None, " ".join(values)),

        "Description" : lambda *values: (None, " ".join(values)),

        "Date" : lambda date, time: (None, datetime.strptime(date + " " + time, '%m/%d/%Y %H:%M:%S')),

        "Reference" : lambda *values: (None, " ".join(values)),

        "Scanner Center Position (X, Y)" : lambda units, x="0.0", y="0.0": ("Real Center", {
                "Units" : units[1:-1],
                "X" : MetaFormatter.parse(x, float),
                "Y" : MetaFormatter.parse(y, float),
            }),

        "Rotation" : lambda units, theta="0.0": ("Angle", {
                "Units" : units[1:-1],
                "Theta" : MetaFormatter.parse(theta, float),
            }),

        "Scan Area (X, Y, Z)" : lambda units, x="0.0", y="0.0", z="0.0": ("Real Area", {
                "Units" : units[1:-1],
                "X" : MetaFormatter.parse(x, float),
                "Y" : MetaFormatter.parse(y, float),
                "Z" : MetaFormatter.parse(z, float),
            }),

        "Pixel Area (X, Y, Z)" : lambda units, x="0.0", y="0.0", z="0.0": ("Pixel Area", {
                "Units" : units[1:-1],
                "X" : MetaFormatter.parse(x, float),
                "Y" : MetaFormatter.parse(y, float),
                "Z" : MetaFormatter.parse(z, float),
            }),

        "Interferometer Center/Distance" : lambda units, center="0.0", distance="0.0": (None, {
                "Units" : units[1:-1],
                "Center" : MetaFormatter.parse(center, float),
                "Distance" : MetaFormatter.parse(distance, float),
            }),

        "Averaging" : lambda *values: (None, " ".join(values)),

        "Integration time" : lambda units, time="0.0": (None, {
                "Units" : units[1:-1],
                "Time" : MetaFormatter.parse(time, float),
            }),

        "Wavenumber Scaling" : lambda *values: (None, " ".join(values)),

        "Laser Source" : lambda *values: (None, " ".join(values)),

        "Detector" : lambda *values: (None, " ".join(values)),

        "Target Wavelength" : lambda units, wavelength="0.0": (None, {
                "Units" : units[1:-1],
                "Wavelength" : MetaFormatter.parse(wavelength, float),
            }),

        "Demodulation Mode" : lambda *values: (None, " ".join(values)),

        "Tip Frequency" : lambda units, frequency="0.0": (None, {
                "Units" : units[1:-1],
                "Frequency" : MetaFormatter.parse(frequency, float),
            }),

        "Tip Amplitude" : lambda units, amplitude="0.0": (None, {
                "Units" : units[1:-1],
                "Amplitude" : MetaFormatter.parse(amplitude, float),
            }),

        "Tapping Amplitude" : lambda units, amplitude="0.0": (None, {
                "Units" : units[1:-1],
                "Amplitude" : MetaFormatter.parse(amplitude, float),
            }),

        "Modulation Frequency" : lambda units, frequency="0.0": (None, {
                "Units" : units[1:-1],
                "Frequency" : MetaFormatter.parse(frequency, float),
            }),

        "Modulation Amplitude" : lambda units, amplitude="0.0": (None, {
                "Units" : units[1:-1],
                "Amplitude" : MetaFormatter.parse(amplitude, float),
            }),

        "Modulation Offset" : lambda units, offset="0.0": (None, {
                "Units" : units[1:-1],
                "Offset" : MetaFormatter.parse(offset, float),
            }),

        "Setpoint" : lambda units, setpoint="0.0": (None, {
                "Units" : units[1:-1],
                "Setpoint" : MetaFormatter.parse(setpoint, float),
            }),

        "Regulator (P, I, D)": lambda p="0.0", i="0.0", d="0.0": (None, {
                "P" : MetaFormatter.parse(p, float),
                "I" : MetaFormatter.parse(i, float),
                "D" : MetaFormatter.parse(d, float),
            }),

        "Tip Potential" : lambda units, potential="0.0": (None, {
                "Units" : units[1:-1],
                "Potential" : MetaFormatter.parse(potential, float),
            }),

        "M1A Scaling" : lambda units, scaling="0.0": (None, {
                "Units" : units[1:-1],
                "Scaling" : MetaFormatter.parse(scaling, float),
            }),

        "M1A Cantilever Factor" : lambda *values: (None, " ".join(values)),

        "Version" : lambda *values: (None, " ".join(values)),
    }
    

    @staticmethod
    def format(key, values, file_format, default_func=Default.ERROR):
        try:
            return MetaFormatter._format(key, values, file_format)
        except MetaKeyException as e:
            return default_func(*values)

    
    @staticmethod
    def _format(key, values, file_format):
        try:
            func = MetaFormatter.FUNCS[key]
        except KeyError:
            raise MetaKeyException(f"MetaFormatter has no method to convert '{key}'")

        if isinstance(func, dict):
            try:
                func = func[file_format]
            except KeyError:
                raise MetaKeyException(f"MetaFormatter has no method to convert '{key}'")

        if callable(func):
            print(key, values)
            return func(*values)
        
        raise MetaKeyException(f"MetaFormatter has no method to convert '{key}'")
    

    @staticmethod
    def parse(data, type_):
        if type_ is str:
            return data
        
        if type_ is float:
            return float(data.replace(",", ""))
        