import numpy as np




def transform_row_col(row_col_coords, meta):
    real_center = meta.get("Real Center", {})
    rl_center = np.array([
        real_center.get("X", 0.0),
        real_center.get("Y", 0.0),
    ])

    rotation = meta.get("Angle", {})
    theta = np.radians(rotation.get("Theta", 0.0))

    real_area = meta.get("Real Area", {})
    rl_area = np.array([
        real_area.get("X", 1.0),
        real_area.get("Y", 1.0),
    ])

    pixel_area = meta.get("Pixel Area", {})
    px_area = np.array([
        pixel_area.get("X", 1.0),
        pixel_area.get("Y", 1.0),
    ])

    px_center = px_area / 2.0

    rotation_matrix = np.array([
        [np.cos(theta), -np.sin(theta)],
        [np.sin(theta),  np.cos(theta)]
    ])


    values = rl_area * (row_col_coords - px_center) / px_area
    values = (rotation_matrix @ values.T).T

    return rl_center + values
