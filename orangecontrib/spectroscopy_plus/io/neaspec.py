import Orange
import numpy as np
from Orange.data import FileFormat, Table
from scipy.interpolate import interp1d

from orangecontrib.spectroscopy.io.util import SpectralFileFormat

from orangecontrib.spectroscopy_plus.io.utils import MetaFormatter, transform_row_col




class NeaReader(FileFormat, SpectralFileFormat):

    EXTENSIONS = (".nea", ".txt")
    DESCRIPTION = 'NeaSPEC (Improved)'

    def read_v1(self):

        with open(self.filename, "rt") as f:
            next(f)  # skip header
            l = next(f)
            l = l.strip()
            l = l.split("\t")
            ncols = len(l)

            f.seek(0)
            next(f)
            datacols = np.arange(4, ncols)
            data = np.loadtxt(f, dtype="float", usecols=datacols)

            f.seek(0)
            next(f)
            metacols = np.arange(0, 4)
            meta = np.loadtxt(f,
                              dtype={'names': ('row', 'column', 'run', 'channel'),
                                     'formats': (int, int, int, "S10")},
                              usecols=metacols)

            # ASSUMTION: runs start with 0
            runs = np.unique(meta["run"])

            # ASSUMPTION: there is one M channel and multiple O?A and O?P channels,
            # both with the same number, both starting with 0
            channels = np.unique(meta["channel"])
            maxn = -1

            def channel_type(a):
                if a.startswith(b"O") and a.endswith(b"A"):
                    return "OA"
                elif a.startswith(b"O") and a.endswith(b"P"):
                    return "OP"
                else:
                    return "M"

            for a in channels:
                if channel_type(a) in ("OA", "OP"):
                    maxn = max(maxn, int(a[1:-1]))
            numharmonics = maxn+1

            rowcols = np.vstack((meta["row"], meta["column"])).T
            uniquerc = set(map(tuple, rowcols))

            di = {}  # dictionary of indices for each row and column

            min_intp, max_intp = None, None

            for i, (row, col, run, chan) in enumerate(meta):
                if (row, col) not in di:
                    di[(row, col)] = \
                        {"M": np.zeros((len(runs), len(datacols))) * np.nan,
                         "OA": np.zeros((numharmonics, len(runs), len(datacols))) * np.nan,
                         "OP": np.zeros((numharmonics, len(runs), len(datacols))) * np.nan}
                if channel_type(chan) == "M":
                    di[(row, col)][channel_type(chan)][run] = data[i]
                    if min_intp is None:  # we need the limits of common X for all
                        min_intp = np.min(data[i])
                        max_intp = np.max(data[i])
                    else:
                        min_intp = max(min_intp, np.min(data[i]))
                        max_intp = min(max_intp, np.max(data[i]))
                elif channel_type(chan) in ("OA", "OP"):
                    di[(row, col)][channel_type(chan)][int(chan[1:-1]), run] = data[i]

            X = np.linspace(min_intp, max_intp, num=len(datacols))

            final_metas = []
            final_data = []

            for row, col in uniquerc:
                cur = di[(row, col)]
                M, OA, OP = cur["M"], cur["OA"], cur["OP"]

                OAn = np.zeros(OA.shape) * np.nan
                OPn = np.zeros(OA.shape) * np.nan
                for run in range(len(M)):
                    f = interp1d(M[run], OA[:, run])
                    OAn[:, run] = f(X)
                    f = interp1d(M[run], OP[:, run])
                    OPn[:, run] = f(X)

                OAmean = np.mean(OAn, axis=1)
                OPmean = np.mean(OPn, axis=1)
                final_data.append(OAmean)
                final_data.append(OPmean)
                final_metas += [[row, col, "O%dA" % i] for i in range(numharmonics)]
                final_metas += [[row, col, "O%dP" % i] for i in range(numharmonics)]

            final_data = np.vstack(final_data)

            metas = [Orange.data.ContinuousVariable.make("row"),
                     Orange.data.ContinuousVariable.make("column"),
                     Orange.data.StringVariable.make("channel")]

            domain = Orange.data.Domain([], None, metas=metas)
            meta_data = Table.from_numpy(domain, X=np.zeros((len(final_data), 0)),
                                         metas=np.asarray(final_metas, dtype=object))
            return X, final_data, meta_data

    def read_v2(self):
        file_format = MetaFormatter.FileFormat.NEA_TXT

        with open(self.filename, "r", encoding='utf-8') as f:
            count = -1

            meta = {}

            while f:
                count += 1
                line = f.readline()

                if line[0] != '#':
                    break

                if count == 0:
                    assert(line == "# www.neaspec.com\n")
                    continue

                key, value = line.split(":", 1)
                key = key[2:]
                new_key, values = MetaFormatter.format(key,
                                                       value.split(),
                                                       file_format,
                                                       default_func=MetaFormatter.Default.BASIC)
                
                if new_key is not None:
                    key = new_key

                if values is not None:
                    meta[key] = values
                

            file = np.loadtxt(f)  # Slower part

        # Find the Wavenumber column
        headers = line.strip().split('\t')

        if "Wavenumber" in headers:
            return self.read_v2_wavenumbers(headers, file, meta)
        
        return self.read_v2_interferograms(headers, file, meta)
    


    def read_v2_wavenumbers(self, headers, file, meta):
        # Desired headers:
        # map_x  map_y  row  col  channel  [wavenumbers]

        row_i = col_i = ome_i = wav_i = None

        for i, e in enumerate(headers):
            if e == "Row":
                row_i = i

            elif e == "Column":
                col_i = i

            elif e == "Omega":
                ome_i = i

            elif e == 'Wavenumber':
                wav_i = i


        channels = np.array(headers[wav_i + 1:])
        # Extract other data #

        rows = int(np.nanmax(file[:, row_i]) + 1)
        cols = int(np.nanmax(file[:, col_i]) + 1)

        n_cols = int(np.nanmax(file[:, ome_i]) + 1)
        n_rows = rows * cols * channels.size


        # Transform Actual Data
        M = np.full((int(n_rows), int(n_cols)), np.nan, dtype='float')

        meta_data = np.zeros((int(n_rows), 3), dtype='object')


        for j in range(int(rows * cols)):
            lower = j * n_cols
            upper = (j + 1) * n_cols

            row_values = file[lower:upper, row_i]
            assert np.all(row_values == row_values[0])

            col_values = file[lower:upper, col_i]
            assert np.all(col_values == col_values[0])

            meta_data[channels.size * j:channels.size * (j+1), 0] = col_values[0]
            meta_data[channels.size * j:channels.size * (j+1), 1] = row_values[0]
            meta_data[channels.size * j:channels.size * (j+1), 2] = np.arange(channels.size)

            for k in range(channels.size):
                M[k + channels.size * j, :] = file[lower:upper, k + wav_i + 1]


        meta_data[:,[0, 1]] = transform_row_col(meta_data[:,[0, 1]], meta)


        waveN = file[0:int(n_cols), wav_i]
        metas = [Orange.data.ContinuousVariable.make("map_x"),
                 Orange.data.ContinuousVariable.make("map_y"),
                 Orange.data.DiscreteVariable.make("channel", values=channels)]

        domain = Orange.data.Domain([], None, metas=metas)
        meta_data = Table.from_numpy(domain, X=np.zeros((len(M), 0)),
                                     metas=meta_data)
        
        meta_data.attributes = meta

        return waveN, M, meta_data



    def read_v2_interferograms(self, headers, file, meta):
        # Desired headers:
        # map_x  map_y  depth  channel  [run]

        row_i = col_i = run_i = dep_i = None

        for i, e in enumerate(headers):
            if e == "Row":
                row_i = i

            elif e == "Column":
                col_i = i

            elif e == "Run":
                run_i = i

            elif e == "Depth":
                dep_i = i


        # Run is averaging
        # Depth is depth


        channels = np.array(headers[dep_i + 1:])
        # Extract other data #

        rows = int(np.nanmax(file[:, row_i]) + 1)
        cols = int(np.nanmax(file[:, col_i]) + 1)

        n_cols = int(np.nanmax(file[:, dep_i]) + 1)
        n_rows = rows * cols * channels.size


        # Transform Actual Data
        M = np.full((int(n_rows), int(n_cols)), np.nan, dtype='float')

        meta_data = np.zeros((int(n_rows), 4), dtype='object')


        for j in range(int(rows * cols)):
            lower = j * n_cols
            upper = (j + 1) * n_cols

            row_values = file[lower:upper, row_i]
            assert np.all(row_values == row_values[0])

            col_values = file[lower:upper, col_i]
            assert np.all(col_values == col_values[0])

            run_values = file[lower:upper, run_i]

            meta_data[channels.size * j:channels.size * (j+1), 0] = col_values[0]
            meta_data[channels.size * j:channels.size * (j+1), 1] = row_values[0]
            meta_data[channels.size * j:channels.size * (j+1), 2] = run_values[0]
            meta_data[channels.size * j:channels.size * (j+1), 3] = np.arange(channels.size)

            for k in range(channels.size):
                M[k + channels.size * j, :] = file[lower:upper, k + run_i + 1]


        meta_data[:,[0, 1]] = transform_row_col(meta_data[:,[0, 1]], meta)


        waveN = file[0:int(n_cols), dep_i]
        metas = [Orange.data.ContinuousVariable.make("map_x"),
                 Orange.data.ContinuousVariable.make("map_y"),
                 Orange.data.ContinuousVariable.make("run"),
                 Orange.data.DiscreteVariable.make("channel", values=channels)]

        domain = Orange.data.Domain([], None, metas=metas)
        meta_data = Table.from_numpy(domain, X=np.zeros((len(M), 0)),
                                     metas=meta_data)
        
        meta_data.attributes = meta

        return waveN, M, meta_data


    def read_spectra(self):
        version = 1
        with open(self.filename, "rt", encoding='utf-8') as f:
            if f.read(2) == '# ':
                version = 2
        if version == 1:
            return self.read_v1()
        else:
            return self.read_v2()
        

if __name__ == "__main__":
    from Orange.data.table import dataset_dirs
    filename = None
    reader = NeaReader(FileFormat.locate(filename, dataset_dirs))

    d = reader.read()