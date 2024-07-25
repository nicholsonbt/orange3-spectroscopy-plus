from .contrastingcolormethod import ContrastingColorMethods


import numpy as np

from orangecontrib.spectroscopy.widgets.owhyper import values_to_linspace

import Orange.data

from collections.abc import Iterable
import itertools

from scipy import spatial

from AnyQt.QtGui import QPainter




class ImageTypes:
    RASTER = 0
    SCATTER = 1
    LINESCAN = 2




class ChannelNormalisationTypes:
    GLOBAL = 0
    PER_CHANNEL = 1
    NONE_1 = 2
    NONE_256 = 3




class CompositionTypes:
    Normal              = QPainter.CompositionMode_Source
    Overlay             = QPainter.CompositionMode_Overlay
    Multiply            = QPainter.CompositionMode_Multiply
    Difference          = QPainter.CompositionMode_Difference





class EnumController:
    @staticmethod
    def names(enum, beautify=False):
        attrs = [attr for attr in enum.__dict__ if attr[:2] != "__"]

        if beautify:
            return [attr.replace("_", " ") for attr in attrs]
        
        return attrs
    
    
    @staticmethod
    def values(enum):
        return [getattr(enum, attr) for attr in EnumController.names(enum)]
    

    @staticmethod
    def value(enum, index):
        return EnumController.values(enum)[index]




def getPixelSize(pw, ph):
    w_fin = np.isfinite(pw)
    h_fin = np.isfinite(ph)

    if w_fin and h_fin:
        return pw, ph
    
    if w_fin:
        return pw, pw
    
    if h_fin:
        return ph, ph
    
    return 1, 1


def collective_domain(*domains):
    def split_domain(domain):
        return (
            [(attr.name, type(attr)) for attr in domain.attributes],
            [(attr.name, type(attr)) for attr in domain.metas],
            [(attr.name, type(attr)) for attr in domain.class_vars],
        )
    
    def logical_and(arr0, arr1):
        arr = []

        for x in arr0:
            if x in arr1:
                arr.append(x)

        return arr

    if len(domains) == 0:
        return None
    
    if len(domains) == 1:
        return domains[0]
    
    attrs, metas, c_var = split_domain(domains[0])

    for domain in domains[1:]:
        attrs_i, metas_i, c_var_i = split_domain(domain)

        attrs = logical_and(attrs, attrs_i)
        metas = logical_and(metas, metas_i)
        c_var = logical_and(c_var, c_var_i)

    return Orange.data.Domain(
        [type_(name) for name, type_ in attrs],
        class_vars=[type_(name) for name, type_ in c_var],
        metas=[type_(name) for name, type_ in metas],
    )


def setBackgroundColour(from_, to_):
    background_color = from_.palette().color(from_.backgroundRole())

    to_.setAutoFillBackground(True)
    palette = to_.palette()
    palette.setColor(to_.backgroundRole(), background_color)
    to_.setPalette(palette)






def rotateCoords(coords, rots, origin=None, radians=True):
    # The number of degrees of rotation in n-dimensional space is
    # (n/2)*(n-1).
    n = coords.shape[1]
    assert(len(rots) == n * (n-1) / 2)

    # The point to rotate around.
    if origin is None:
        origin = np.mean(coords, axis=0)

    # If angles are measured in degrees, convert to radians.
    if not radians:
        rots = np.radians(rots)

    # Calculate the rotation matrices.
    matrices = []
    index = 0
    for i in range(n-1):
        for j in range(i + 1, n):
            matrix = np.eye(n)
            matrix[[i, j], [i, j]] = np.cos(rots[index])
            matrix[i, j] = -np.sin(rots[index])
            matrix[j, i] = np.sin(rots[index])
            matrices.append(matrix)
            index += 1

    # Translate the coordinates to center on the origin.
    rotated = coords - origin

    # Rotate the coordinates.
    for rot_matrix in matrices:
        rotated = np.dot(rotated, rot_matrix)

    # Return the rotated coordinates, translated back to their
    # original center position.
    return rotated + origin







def generateData(*lss, channels=3, rot=0, radians=True, colour_stops=3):
    coords = rotateCoords(generateCoords(*lss), [rot], radians=radians)

    lower = 0
    upper = 1000

    means = np.random.randint(lower, upper, channels)
    scales = np.random.randint(lower+1, upper/6, channels)

    values = np.vstack([
        randomNormal(lower, upper, means[i], scales[i], coords.shape[0]) / upper
        for i in range(channels)
    ]).T

    colours = np.random.randint(0, 256, (colour_stops, 3))

    return coords, values, colours





def findRaster(coords : np.array):
    """_summary_

    _extended_summary_

    Parameters
    ----------
    coords : np.array
        An (n, k) numpy array of n coordinates in a k-dimensional
        domain.
    """
    coords = coords.astype(np.float64)

    # Create a cKDTree of coordinates.
    tree = spatial.cKDTree(coords)
    # For each coordinate, find the two nearest-neighbours of said
    # coordinate (the nearest neighbour should be itself).
    _, indices = tree.query(coords, k=2)

    # Get the second closest coordinate (closest other than itself).
    closest = coords[indices[:, 1], :]

    # Find the (absolute) step size between each coordinate and its
    # nearest neighbour.
    steps = np.sort(np.abs(coords - closest), axis=1)

    # Find the median x and y step size.
    step = np.median(steps, axis=0)

    # Given the step size found, calculate the possible gradients,
    # and use these to calculate the possible angles by which the
    # coordinates have been rotated.
    n = len(step) # Don't expect more than 2 dimensions.

    # Calculate all possible (likely) rotations.
    poss_rots = []

    for i in range(n-1):
        for j in range(i+1, n):
            a = -np.arctan2(step[i], step[j])
            b = -np.arctan2(step[j], step[i])

            if np.isclose(a, b):
                poss_rots.append([np.mean([a, b])])
            
            else:
                poss_rots.append([a, b])

    # Get all permutations (important for 3+ dimensions).
    permutations = list(itertools.product(*poss_rots))

    # Find the best rotations and linspaces.
    best_rots = None
    best_lss = None

    for permutation in permutations:
        rots = [*permutation]
        rotated = rotateCoords(coords, rots).T
        lss = [values_to_linspace(col) for col in rotated]
        
        lss = [(x0, x1, 1) if np.isclose(x0, x1) else (x0, x1, n) for x0, x1, n in lss]

        # Check if current linspaces are less than best_linspaces.
        if best_lss is None or np.prod([n for _, _, n in lss]) < np.prod([n for _, _, n in best_lss]):
            best_lss = lss
            best_rots = rots

    return best_lss, np.array(best_rots)
























def generateCoords(*lss):
    # If lss is '[(start, stop, n),]', return coords with shape (n, 1).
    if len(lss) == 1:
        return np.linspace(*lss[0])[:, np.newaxis]
    
    # Swap lss[0] and lss[1].
    # lss = [lss[1], lss[0], *lss[2:]]

    vss = np.meshgrid(*[np.linspace(*ls) for ls in  lss])

    # Swap vs[0] and vs[1] back.
    # vss = [vss[1], vss[0], *vss[2:]]

    # Column stack the flattened values and return.
    return np.column_stack([vs.flatten() for vs in vss])


def randomNormal(lower, upper, mean, scale, count):
    assert(isinstance(count, int))

    values = np.random.normal(mean, scale, count)

    mask = np.logical_or(values < lower, values > upper)

    c = int(np.sum(mask))

    if c > 0:
        values[mask] = randomNormal(lower, upper, mean, scale, c)

    return values



def isarray(obj):
    return isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, bytearray))
