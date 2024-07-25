import numpy as np

from Orange.preprocess.preprocess import Preprocess




class ChipTransition(Preprocess):

    def __init__(self, positions=[]):
        self.positions = positions

    def __call__(self, in_data):
        if len(self.positions) == 0:
            return in_data.copy()
        
        wavenumbers = np.array([float(attr.name) for attr in in_data.domain.attributes])
        
        order = np.argsort(wavenumbers)
        rev_order = np.argsort(order)
        
        diffs = np.diff(in_data.X[:, order], axis=1)

        diffs[:, self.positions] = 0

        diffs = np.hstack((diffs, np.zeros((diffs.shape[0], 1))))

        out_data = in_data.copy()
        out_data.X = np.cumsum(diffs, axis=1)[:, rev_order]

        return out_data

    

    @staticmethod
    def calculate_indices(ys, alpha, beta):
        # Calculate the mean value for each column.
        mean_row = np.nanmean(ys, axis=0)

        # Get the moving sum of the differences (such that noise is
        # minimised).
        diff = np.diff(mean_row)
        diff_sum = np.abs(diff[:-1] + diff[1:])

        # Set the fist and last moving diff sum values to 0.
        diff_sum[[0, -1]] = 0

        # Get the standard deviation of the moving diff sum array.
        std = np.std(diff_sum)

        # If a moving diff sum value is less than alpha * std, set it
        # to 0. This aims to remove noise without removing actual chip
        # transitions.
        diff_sum[diff_sum < alpha * std] = 0

        # Calculate the difference of the moving diff sum array.
        diff_sum_2 = np.abs(np.diff(diff_sum))

        noise_mask = np.hstack((True, diff_sum_2 > beta * std))

        diff_sum[noise_mask] = 0

        indices = np.where(diff_sum > 0)

        return indices[0]
