import numpy as np

from Orange.data import FileFormat

from orangecontrib.spectroscopy.io.util import SpectralFileFormat, _spectra_from_image

from orangecontrib.spectroscopy_plus.io.utils import transform_row_col





def reader_gsf(file_path):

    with open(file_path, "rb") as f:
        if not f.readline() == b'Gwyddion Simple Field 1.0\n':
            raise ValueError('Not a correct GSF file, wrong header.')

        meta = {}

        term = False #there are mandatory fileds
        while term != b'\x00':
            l = f.readline().decode('utf-8')
            name, value = l.split("=")
            name = name.strip()
            value = value.strip()
            meta[name] = value
            term = f.read(1)
            f.seek(-1, 1)

        f.read(4 - f.tell() % 4)

        print(meta.keys())

        meta["XRes"] = XR = int(meta["XRes"])
        meta["YRes"] = YR = int(meta["YRes"])
        meta["XReal"] = float(meta.get("XReal", 1))
        meta["YReal"] = float(meta.get("YReal", 1))
        meta["XOffset"] = float(meta.get("XOffset", 0))
        meta["YOffset"] = float(meta.get("YOffset", 0))
        meta["Title"] = meta.get("Title", None)
        meta["XYUnits"] = meta.get("XYUnits", None)
        meta["ZUnits"] = meta.get("ZUnits", None)

        metas = {
            "Real Center" : {
                "X" : float(meta.get("XOffset", 0.0)) + float(meta.get("XReal", 1.0)) / 2,
                "Y" : float(meta.get("YOffset", 0.0)) + float(meta.get("XReal", 1.0)) / 2,
            },

            "Angle" : {
                "Theta" : float(meta.get("Neaspec_Angle", 0.0))
            },

            "Real Area" : {
                "X" : float(meta.get("XReal", 1.0)),
                "Y" : float(meta.get("YReal", 1.0)),
            },

            "Pixel Area" : {
                "X" : float(meta.get("XRes", 1.0)),
                "Y" : float(meta.get("YRes", 1.0)),
            }
        }




        ## Assume XOffset, YOffset is the bottom left corner of the map.

        X = np.fromfile(f, dtype='float32', count=XR*YR).reshape(XR, YR)

        XRr = np.linspace(meta["XOffset"], meta["XOffset"] + meta["XReal"], meta["XRes"])

        #YRr = np.linspace(meta["YOffset"] + meta["YReal"], meta["YOffset"], meta["YRes"])


        XRr = np.arange(XR) #np.tile(np.arange(XR), YR)
        YRr = np.arange(YR)#[::-1] #np.repeat(np.arange(YR), XR)

        # meta_data = np.vstack((rows, cols)).T


        # meta_data = transform_row_col(meta_data, metas)


        #XRr, YRr = meta_data.T

        # print(meta_data)
        # metas = [Orange.data.ContinuousVariable.make("map_x"),
        #          Orange.data.ContinuousVariable.make("map_y"),
        #          Orange.data.DiscreteVariable.make("channel", values=channels)]

        # domain = Orange.data.Domain([], None, metas=metas)
        # meta_data = Table.from_numpy(domain, X=np.zeros((len(M), 0)),
        #                              metas=meta_data)
        
        # meta_data.attributes = meta
        # return waveN, M, meta_data



        #XRr = np.arange(XR)
        #YRr = np.arange(YR-1, -1, -1)  # needed to have the same orientation as in Gwyddion

        X = X.reshape((meta["YRes"], meta["XRes"]) + (1,))


    return X, XRr, YRr, meta


class GWYReader(FileFormat, SpectralFileFormat):

    EXTENSIONS = (".gsf",)
    DESCRIPTION = 'Gwyddion Simple Field (Improved)'

    def read_spectra(self):
        X, XRr, YRr, meta = reader_gsf(self.filename)
        data = _spectra_from_image(X, np.array([1]), XRr, YRr)

        data[2].attributes = meta

        metas = {
            "Real Center" : {
                "X" : float(meta.get("XOffset", 0.0)) + float(meta.get("XReal", 1.0)) / 2,
                "Y" : float(meta.get("YOffset", 0.0)) + float(meta.get("YReal", 1.0)) / 2,
            },

            "Angle" : {
                "Theta" : float(meta.get("Neaspec_Angle", 0.0))
            },

            "Real Area" : {
                "X" : float(meta.get("XReal", 1.0)),
                "Y" : float(meta.get("YReal", 1.0)),
            },

            "Pixel Area" : {
                "X" : float(meta.get("XRes", 1.0)),
                "Y" : float(meta.get("YRes", 1.0)),
            }
        }

        print(metas)
        print(data[2].attributes)

        data[2].metas[:,[0,1]] = transform_row_col(data[2].metas[:,[0,1]], metas)

        return data
    
if __name__ == "__main__":
    from Orange.data.table import dataset_dirs
    filename = None
    reader = GWYReader(FileFormat.locate(filename, dataset_dirs))

    d = reader.read()