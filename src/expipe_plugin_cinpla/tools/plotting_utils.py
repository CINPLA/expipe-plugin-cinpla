# -*- coding: utf-8 -*-
import numpy as np


def spike_track(x, y, t, spike_train, ax, spines=True):
    from scipy.interpolate import interp1d

    ax.plot(x, y, color="grey", alpha=0.5, zorder=0)
    spike_pos_f = interp1d(t, np.stack([x, y], axis=0), kind="linear", fill_value="extrapolate")
    spike_pos = spike_pos_f(spike_train)
    ax.scatter(*spike_pos, color=(0.7, 0.2, 0.2), zorder=1)
    ax.axis("off")
    # re-add spines
    if spines:
        for spine in ax.spines.values():
            spine.set_visible(True)
    # set x and y limits (boundary)
    ax.axis([0, 1, 0, 1])
    return ax
