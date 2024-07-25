import numpy as np

from AnyQt import QtGui




class ContrastingColorMethods:
    class Enum:
        INVERSE = 0
        SHIFT = 1
        BLACK = 2
        WHITE = 3
        HSL = 4
    

    METHODS = {
        Enum.INVERSE    : lambda r, g, b: ContrastingColorMethods.inverseFunc(r, g, b),
        Enum.SHIFT      : lambda r, g, b: ContrastingColorMethods.shiftFunc(r, g, b),
        Enum.BLACK      : lambda r, g, b: ContrastingColorMethods.blackFunc(r, g, b),
        Enum.WHITE      : lambda r, g, b: ContrastingColorMethods.whiteFunc(r, g, b),
        Enum.HSL        : lambda r, g, b: ContrastingColorMethods.hslFunc(r, g, b),
    }


    @staticmethod
    def inverseFunc(r, g, b):
        rgb = np.array([r, g, b])
        return 255 - rgb
    

    @staticmethod
    def shiftFunc(r, g, b):
        rgb = np.array([r, g, b])
        return (rgb + 128) % 256
        

    @staticmethod
    def blackFunc(r, g, b):
        return np.array([0, 0, 0])
    

    @staticmethod
    def whiteFunc(r, g, b):
        return np.array([255, 255, 255])
    

    @staticmethod
    def hslFunc(r, g, b):
        hsl = list(QtGui.QColor(int(r), int(g), int(b)).getHsl())
        hsl[0] = (hsl[0] + 180) % 360
        hsl[2] = 255 - hsl[2]
        return np.array(QtGui.QColor.fromHsl(*hsl).getRgb()[:3])
