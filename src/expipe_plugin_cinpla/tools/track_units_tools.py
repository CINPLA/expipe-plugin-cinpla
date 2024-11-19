# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import gridspec
from scipy.optimize import linear_sum_assignment


def compute_dissimilarity(template_0, template_1):
    """
    Returns a value of dissimilarity of the mean between two templates.
    The dissimilarity is computed as the root sum square of the difference
    between the two templates, averaged over channels and normalized by the
    maximum value of the two templates.

    Parameters
    ----------
    template_0 : np.ndarray
        The first template. Dimensions are (n_timepoints, n_channels).
    template_1 : np.ndarray
        The second template. Dimensions are (n_timepoints, n_channels).

    Returns
    -------
    dissimilarity : float
        The dissimilarity between the two templates.
    """

    max_val = np.max([np.max(np.abs(template_0)), np.max(np.abs(template_1))])

    template_0_scaled = template_0 / max_val
    template_1_scaled = template_1 / max_val
    # root sum square, averaged over channels
    weighted = np.sqrt(np.sum((template_0_scaled - template_1_scaled) ** 2, axis=1)).mean()
    return weighted


def make_possible_match(dissimilarity_scores, max_dissimilarity):
    """
    Given an agreement matrix and a max_dissimilarity threhold.
    Return as a dict all possible match for each spiketrain in each side.

    Note : this is symmetric.


    Parameters
    ----------
    dissimilarity_scores: pd.DataFrame

    max_dissimilarity: float


    Returns
    -----------
    best_match_12: pd.Series

    best_match_21: pd.Series

    """
    unit1_ids = np.array(dissimilarity_scores.index)
    unit2_ids = np.array(dissimilarity_scores.columns)

    # threhold the matrix
    scores = dissimilarity_scores.values.copy()
    scores[scores > max_dissimilarity] = np.inf

    possible_match_12 = {}
    for i1, u1 in enumerate(unit1_ids):
        inds_match = np.isfinite(scores[i1, :])
        possible_match_12[u1] = unit2_ids[inds_match]

    possible_match_21 = {}
    for i2, u2 in enumerate(unit2_ids):
        inds_match = np.isfinite(scores[:, i2])
        possible_match_21[u2] = unit1_ids[inds_match]

    return possible_match_12, possible_match_21


def make_best_match(dissimilarity_scores, max_dissimilarity):
    """
    Given an agreement matrix and a max_dissimilarity threhold.
    return a dict a best match for each units independently of others.

    Note : this is symmetric.

    Parameters
    ----------
    dissimilarity_scores: pd.DataFrame

    max_dissimilarity: float


    Returns
    -----------
    best_match_12: pd.Series

    best_match_21: pd.Series


    """
    unit1_ids = np.array(dissimilarity_scores.index)
    unit2_ids = np.array(dissimilarity_scores.columns)

    scores = dissimilarity_scores.values.copy()

    best_match_12 = pd.Series(index=unit1_ids, dtype="int64")
    for i1, u1 in enumerate(unit1_ids):
        ind_min = np.argmin(scores[i1, :])
        if scores[i1, ind_min] <= max_dissimilarity:
            best_match_12[u1] = unit2_ids[ind_min]
        else:
            best_match_12[u1] = -1

    best_match_21 = pd.Series(index=unit2_ids, dtype="int64")
    for i2, u2 in enumerate(unit2_ids):
        ind_min = np.argmin(scores[:, i2])
        if scores[ind_min, i2] <= max_dissimilarity:
            best_match_21[u2] = unit1_ids[ind_min]
        else:
            best_match_21[u2] = -1

    return best_match_12, best_match_21


def make_hungarian_match(dissimilarity_scores, max_dissimilarity):
    """
    Given an agreement matrix and a max_dissimilarity threhold.
    return the "optimal" match with the "hungarian" algo.
    This use internally the scipy.optimze.linear_sum_assignment implementation.

    Parameters
    ----------
    dissimilarity_scores: pd.DataFrame

    max_dissimilarity: float


    Returns
    -----------
    hungarian_match_12: pd.Series

    hungarian_match_21: pd.Series

    """
    unit1_ids = np.array(dissimilarity_scores.index)
    unit2_ids = np.array(dissimilarity_scores.columns)

    # threhold the matrix
    scores = dissimilarity_scores.values.copy()

    [inds1, inds2] = linear_sum_assignment(scores)

    hungarian_match_12 = pd.Series(index=unit1_ids, dtype="int64")
    hungarian_match_12[:] = -1
    hungarian_match_21 = pd.Series(index=unit2_ids, dtype="int64")
    hungarian_match_21[:] = -1

    for i1, i2 in zip(inds1, inds2, strict=False):
        u1 = unit1_ids[i1]
        u2 = unit2_ids[i2]
        if dissimilarity_scores.at[u1, u2] < max_dissimilarity:
            hungarian_match_12[u1] = u2
            hungarian_match_21[u2] = u1

    return hungarian_match_12, hungarian_match_21


def plot_template(template, fig, gs, axs=None, **kwargs):
    """
    Plot a template on a figure.

    Parameters
    ----------
    template: np.ndarray
        The template to plot. The first dimension is the number of timepoints
        and the second dimension is the number of channels.
    fig: matplotlib.figure.Figure
        The figure to plot on.
    gs: matplotlib.gridspec.GridSpec
        The gridspec to plot on.
    axs: list of matplotlib.axes.Axes
        The axes to plot on. If None, new axes are created.
    kwargs: dict
        Keyword arguments to pass to the plot function.
    """
    nrc = template.shape[1]
    if axs is None:
        gs0 = gridspec.GridSpecFromSubplotSpec(1, nrc, subplot_spec=gs)
        axs = [fig.add_subplot(gs0[0])]
        axs.extend([fig.add_subplot(gs0[i], sharey=axs[0], sharex=axs[0]) for i in range(1, nrc)])
    for c in range(nrc):
        axs[c].plot(template[:, c], **kwargs)
        if c > 0:
            plt.setp(axs[c].get_yticklabels(), visible=False)
    return axs
