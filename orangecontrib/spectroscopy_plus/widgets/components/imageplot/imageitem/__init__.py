import numpy as np
import pyqtgraph as pg

from AnyQt import QtCore, QtGui, QtWidgets

from scipy import spatial


from orangecontrib.spectroscopy_plus.utils.plots import ImageTypes, ChannelNormalisationTypes, getPixelSize, findRaster, generateCoords, rotateCoords




class ImageItem(pg.GraphicsObject):
    PIXEL_TOLERANCE = 0.01
    MATCHING_REQUIRED = 0.8


    def __init__(self, coords=None, values=None, **kwargs):
        pg.GraphicsObject.__init__(self)

        self._coords = None
        self._colours = None
        self._qcolours = None
        self._lsx = None
        self._lsy = None
        self._rotation = 0

        self._lut = None

        self._image_type = None
        self._norm_type = None

        # Should be the same across all images.
        self._composition_mode = None

        self._render_required = False

        self._pixel_size = None

        self._poor_lss = False

        self.setCoords(coords)
        self.setColours(values)

        self.setOpts(**{
            "composition_mode"  : QtGui.QPainter.CompositionMode_SourceOver,
            "image_type"        : ImageTypes.LINESCAN,
            "norm_type"         : ChannelNormalisationTypes.GLOBAL,
        } | kwargs)


    def setOpts(self, **kwargs) -> None:
        options = {
            "composition_mode"  : self.setCompositionMode,
            "image_type"        : self.setImageType,
            "norm_type"         : self.setNormalisationType,
        }

        for k, v in options.items():
            if k in kwargs:
                v(kwargs.get(k))
        
        self.update()


    def setCompositionMode(self, composition_mode, update=True):
        self._composition_mode = composition_mode

        if update:
            self.update()

    
    def setImageType(self, image_type, update=True):
        self._image_type = image_type

        if update:
            self.update()


    def setNormalisationType(self, norm_type, update=True):
        self._norm_type = norm_type

        self.updateQColours()

        if update:
            self.update()

    
    def setCoords(self, coords: np.array, **kwargs) -> None:
        self._poor_lss = False

        self._coords = coords

        lss, rot = findRaster(coords)

        self._lsx, self._lsy = lss
        self._rotation = rot

        self._pixel_size = np.array([
            (lsi[1] - lsi[0]) / (lsi[2]-1) if lsi[2] > 1 else np.nan for lsi in lss
        ])

        self.setOpts(**kwargs)

    
    def setColours(self, values: np.array, **kwargs) -> None:
        if values.shape[0] != self._coords.shape[0]:
            raise Exception("Length Mismatch")
        
        self._colours = values

        self.setOpts(**kwargs)
        self.updateQColours()


    def setLookupTable(self, lut, update=True):
        self._lut = lut

        self.updateQColours()
        
        if update:
            self.update()

    
    def updateQColours(self):
        def nonZeroR(r):
            if isinstance(r, np.ndarray):
                r[r==0] = np.inf
            elif r == 0:
                    r = np.inf
            return r
            
        if self._colours.shape[1] == 3:
            if self._norm_type == ChannelNormalisationTypes.GLOBAL or self._norm_type == ChannelNormalisationTypes.PER_CHANNEL:
                if self._norm_type == ChannelNormalisationTypes.GLOBAL:
                    lower = np.nanmin(self._colours)
                    upper = np.nanmax(self._colours)
                
                else:
                    lower = np.nanmin(self._colours, axis=0)
                    upper = np.nanmax(self._colours, axis=0)

                r = nonZeroR(upper - lower)

                rgb_arr = 255 * (self._colours-lower) / r

            elif self._norm_type == ChannelNormalisationTypes.NONE_1:
                rgb_arr = 255 * self._colours

            elif self._norm_type == ChannelNormalisationTypes.NONE_256:
                rgb_arr = self._colours

            elif self._norm_type == None:
                rgb_arr = self._colours
                pass

            else:
                raise Exception("ERROR!!!")

            self._qcolours = [QtGui.QColor(*[int(channel) for channel in rgb]) for rgb in rgb_arr]
        
        elif self._colours.shape[1] == 1:
            lower = np.nanmin(self._colours)
            upper = np.nanmax(self._colours)

            r = nonZeroR(upper - lower)

            norm = (self._colours-lower) / r

            if np.sum(np.isnan(norm)) == len(norm):
                self._qcolours = None

            elif self._lut is None:
                self._qcolours = [QtGui.QColor(*[int(k[0]*255)]*3) for k in norm]

            else:
                self._qcolours = [QtGui.QColor(*[int(c) for c in self._lut[int(k[0]*255), :]]) for k in norm]



    def boundingRect(self) -> QtCore.QRectF:
        if self._lsx is None or self._lsy is None:
            return QtCore.QRectF(0., 0., 0., 0.)
        
        offset = np.array(list(getPixelSize(*self._pixel_size))) / 2

        corners = np.array([
            [self._lsx[0] - offset[0], self._lsy[0] - offset[1]],
            [self._lsx[0] - offset[0], self._lsy[1] + offset[1]],
            [self._lsx[1] + offset[0], self._lsy[0] - offset[1]],
            [self._lsx[1] + offset[0], self._lsy[1] + offset[1]],
        ])

        rotated = rotateCoords(corners, -self._rotation)

        lower = np.min(rotated, axis=0)
        upper = np.max(rotated, axis=0)

        return QtCore.QRectF(*lower, *(upper-lower))
        

    def paint(self, painter, *args):
        profile = pg.debug.Profiler()

        if self._coords is None:
            return
        
        if self._qcolours is None:
            return
        
        if self._render_required:
            self.render()

            if self._unrenderable:
                return
            
            profile("render QData")

        if self._composition_mode is not None:
            painter.setCompositionMode(self._composition_mode)
            profile("set composition mode")

        if self._image_type == ImageTypes.RASTER:
            self._paintRaster(painter)

        elif self._image_type == ImageTypes.SCATTER:
            self._paintScatter(painter)

        elif self._image_type == ImageTypes.LINESCAN:
            if self._lsx[2] == 1 or self._lsy[2] == 1 or self._poor_lss:
                self._paintScatter(painter)
            
            else:
                self._paintRaster(painter)
        
        else:
            raise Exception("ERROR!!!")



    def _paintRaster(self, painter):
        pw, ph = getPixelSize(*self._pixel_size)

        tol = np.array(getPixelSize(*self._pixel_size)) * ImageItem.PIXEL_TOLERANCE

        g_coords = generateCoords(self._lsx, self._lsy)
        r_coords = rotateCoords(g_coords, -self._rotation)
        tree = spatial.cKDTree(r_coords)

        _, indices = tree.query(self._coords, k=1)

        valid = np.logical_and(
            np.isclose(r_coords[indices][:,0], self._coords[:,0], atol=tol[0]),
            np.isclose(r_coords[indices][:,1], self._coords[:,1], atol=tol[1]),
        )

        if self._image_type == ImageTypes.LINESCAN and np.sum(valid) / indices.shape[0] < ImageItem.MATCHING_REQUIRED:
            self._poor_lss = True
            return

        k_coords = g_coords[indices][valid]
        l_coords = np.delete(g_coords, indices, axis=0)

        for i, (x, y) in enumerate(l_coords):
            colour = QtGui.QColor(*[150]*3)

            rect = QtCore.QRectF(x-pw/2, y-ph/2, pw, ph)

            painter.fillRect(rect, colour)

        
        for i, (x, y) in enumerate(g_coords[indices][~valid]):
            colour = QtGui.QColor(255, 0, 0)

            rect = QtCore.QRectF(x-pw/2, y-ph/2, pw, ph)

            painter.fillRect(rect, colour)


        for i, (x, y) in enumerate(k_coords):
            colour = self._qcolours[i]

            rect = QtCore.QRectF(x-pw/2, y-ph/2, pw, ph)

            painter.fillRect(rect, colour)

        

        rot = np.degrees(self._rotation)

        center = np.array([
            (self._lsx[0] + self._lsx[1]) / 2,
            (self._lsy[0] + self._lsy[1]) / 2,
        ])

        transform = QtGui.QTransform()
        transform.translate(*center)
        transform.rotate(*rot)
        transform.translate(*-center)
        self.setTransform(transform)



    def _paintScatter(self, painter):
        def nonZeroMin(values):
            return min([x for x in values if x != 0])
        
        size = nonZeroMin(getPixelSize(*self._pixel_size))

        k = 0.8
        radius = k*size / 2

        for i, (x, y) in enumerate(self._coords):
            colour = self._qcolours[i]

            painter.setPen(pg.mkPen("black"))
            painter.setBrush(colour)

            coord = QtCore.QPointF(x, y)

            painter.drawEllipse(coord, radius, radius)

        self.resetTransform()
