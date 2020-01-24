# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
from os import path as op

from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface,
    File
)
import numpy as np
import nibabel as nb


def f_kendall(timeseries_matrix):
    """
    Calculates the Kendall"s coefficient of concordance for a number of
    time-series in the input matrix

    Parameters
    ----------

    timeseries_matrix : ndarray
        A matrix of ranks of a subset subject"s brain voxels

    Returns
    -------

    kcc : float
        Kendall"s coefficient of concordance on the given input matrix

    """

    nk = timeseries_matrix.shape

    n = nk[0]
    k = nk[1]

    sr = np.sum(timeseries_matrix, 1)
    sr_bar = np.mean(sr)

    s = np.sum(np.power(sr, 2)) - n * np.power(sr_bar, 2)

    kcc = 12 * s / np.power(k, 2) / (np.power(n, 3) - n)

    return kcc


def compute_reho(in_file, mask_file, cluster_size):
    """
    Computes the ReHo Map, by computing tied ranks of the timepoints,
    followed by computing Kendall"s coefficient concordance(KCC) of a
    timeseries with its neighbours

    Parameters
    ----------

    in_file : nifti file
        4D EPI File

    mask_file : nifti file
        Mask of the EPI File(Only Compute ReHo of voxels in the mask)

    cluster_size : integer
        for a brain voxel the number of neighbouring brain voxels to use for
        KCC.


    Returns
    -------

    out_file : nifti file
        ReHo map of the input EPI image

    """

    res_fname = in_file
    res_mask_fname = mask_file
    cutnumber = 10

    if not (cluster_size == 27 or cluster_size == 19 or cluster_size == 7):
        cluster_size = 27

    nvoxel = cluster_size

    res_img = nb.load(res_fname)
    res_mask_img = nb.load(res_mask_fname)

    res_data = res_img.get_data()
    res_mask_data = res_mask_img.get_data()

    (n_x, n_y, n_z, n_t) = res_data.shape

    # "flatten" each volume of the timeseries into one big array instead of
    # x,y,z - produces (timepoints, N voxels) shaped data array
    res_data = np.reshape(res_data, (n_x * n_y * n_z, n_t), order="F").T

    # create a blank array of zeroes of size n_voxels, one for each time point
    Ranks_res_data = np.tile((np.zeros((1, (res_data.shape)[1]))),
                             [(res_data.shape)[0], 1])

    # divide the number of total voxels by the cutnumber (set to 10)
    # ex. end up with a number in the thousands if there are tens of thousands
    # of voxels
    segment_length = np.ceil(float((res_data.shape)[1]) / float(cutnumber))

    for icut in range(0, cutnumber):

        segment = None

        # create a Numpy array of evenly spaced values from the segment
        # starting point up until the segment_length integer
        if not (icut == (cutnumber - 1)):
            segment = np.array(np.arange(icut * segment_length,
                                         (icut + 1) * segment_length))
        else:
            segment = np.array(np.arange(icut * segment_length,
                                         (res_data.shape[1])))

        segment = np.int64(segment[np.newaxis])

        # res_data_piece is a chunk of the original timeseries in_file, but
        # aligned with the current segment index spacing
        res_data_piece = res_data[:, segment[0]]
        nvoxels_piece = res_data_piece.shape[1]

        # run a merge sort across the time axis, re-ordering the flattened
        # volume voxel arrays
        res_data_sorted = np.sort(res_data_piece, 0, kind="mergesort")
        sort_index = np.argsort(res_data_piece, axis=0, kind="mergesort")

        # subtract each volume from each other
        db = np.diff(res_data_sorted, 1, 0)

        # convert any zero voxels into "True" flag
        db = db == 0

        # return an n_voxel (n voxels within the current segment) sized array
        # of values, each value being the sum total of TRUE values in "db"
        sumdb = np.sum(db, 0)

        temp_array = np.array(np.arange(0, n_t))
        temp_array = temp_array[:, np.newaxis]

        sorted_ranks = np.tile(temp_array, [1, nvoxels_piece])

        if np.any(sumdb[:]):

            tie_adjust_index = np.flatnonzero(sumdb)

            for i in range(0, len(tie_adjust_index)):

                ranks = sorted_ranks[:, tie_adjust_index[i]]

                ties = db[:, tie_adjust_index[i]]

                tieloc = np.append(np.flatnonzero(ties), n_t + 2)
                maxties = len(tieloc)
                tiecount = 0

                while (tiecount < maxties - 1):
                    tiestart = tieloc[tiecount]
                    ntied = 2
                    while (tieloc[tiecount + 1] == (tieloc[tiecount] + 1)):
                        tiecount += 1
                        ntied += 1

                    ranks[tiestart:tiestart + ntied] = np.ceil(
                        np.float32(np.sum(ranks[tiestart:tiestart + ntied]))
                        / np.float32(ntied)
                    )
                    tiecount += 1

                sorted_ranks[:, tie_adjust_index[i]] = ranks

        del db, sumdb
        sort_index_base = np.tile(
            np.multiply(np.arange(0, nvoxels_piece), n_t), [n_t, 1]
        )
        sort_index += sort_index_base
        del sort_index_base

        ranks_piece = np.zeros((n_t, nvoxels_piece))

        ranks_piece = ranks_piece.flatten(order="F")
        sort_index = sort_index.flatten(order="F")
        sorted_ranks = sorted_ranks.flatten(order="F")

        ranks_piece[sort_index] = np.array(sorted_ranks)

        ranks_piece = np.reshape(ranks_piece, (n_t, nvoxels_piece), order="F")

        del sort_index, sorted_ranks

        Ranks_res_data[:, segment[0]] = ranks_piece

    Ranks_res_data = np.reshape(
        Ranks_res_data, (n_t, n_x, n_y, n_z), order="F"
    )

    K = np.zeros((n_x, n_y, n_z))

    mask_cluster = np.ones((3, 3, 3))

    if nvoxel == 19:
        mask_cluster[0, 0, 0] = 0
        mask_cluster[0, 2, 0] = 0
        mask_cluster[2, 0, 0] = 0
        mask_cluster[2, 2, 0] = 0
        mask_cluster[0, 0, 2] = 0
        mask_cluster[0, 2, 2] = 0
        mask_cluster[2, 0, 2] = 0
        mask_cluster[2, 2, 2] = 0

    elif nvoxel == 7:

        mask_cluster[0, 0, 0] = 0
        mask_cluster[0, 1, 0] = 0
        mask_cluster[0, 2, 0] = 0
        mask_cluster[0, 0, 1] = 0
        mask_cluster[0, 2, 1] = 0
        mask_cluster[0, 0, 2] = 0
        mask_cluster[0, 1, 2] = 0
        mask_cluster[0, 2, 2] = 0
        mask_cluster[1, 0, 0] = 0
        mask_cluster[1, 2, 0] = 0
        mask_cluster[1, 0, 2] = 0
        mask_cluster[1, 2, 2] = 0
        mask_cluster[2, 0, 0] = 0
        mask_cluster[2, 1, 0] = 0
        mask_cluster[2, 2, 0] = 0
        mask_cluster[2, 0, 1] = 0
        mask_cluster[2, 2, 1] = 0
        mask_cluster[2, 0, 2] = 0
        mask_cluster[2, 1, 2] = 0
        mask_cluster[2, 2, 2] = 0

    for i in range(1, n_x - 1):
        for j in range(1, n_y - 1):
            for k in range(1, n_z - 1):

                block = \
                    Ranks_res_data[:, i - 1:i + 2, j - 1:j + 2, k - 1:k + 2]
                mask_block = \
                    res_mask_data[i - 1:i + 2, j - 1:j + 2, k - 1:k + 2]

                if not (int(mask_block[1, 1, 1]) == 0):

                    if nvoxel == 19 or nvoxel == 7:
                        mask_block = np.multiply(mask_block, mask_cluster)

                    R_block = np.reshape(block, (block.shape[0], 27),
                                         order="F")

                    mask_indices = np.argwhere(
                        np.reshape(mask_block, (1, 27), order="F") > 0
                    )
                    mask_R_block = \
                        R_block[:, mask_indices[:, 1]]

                    K[i, j, k] = f_kendall(mask_R_block)

    img = nb.Nifti1Image(K, header=res_img.get_header(),
                         affine=res_img.get_affine())
    reho_file = op.join(os.getcwd(), "ReHo.nii.gz")
    img.to_filename(reho_file)
    out_file = reho_file

    return out_file


class ReHoInputSpec(TraitedSpec):
    in_file = File(exists=True, desc="input file")
    mask_file = File(exists=True, desc="mask file")
    cluster_size = traits.Int(27, desc="cluster definition")


class ReHoOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="output file")


class ReHo(SimpleInterface):
    """
    Select columns to make a design matrix
    """

    input_spec = ReHoInputSpec
    output_spec = ReHoOutputSpec

    def _run_interface(self, runtime):
        out_file = compute_reho(
            in_file=self.inputs.in_file,
            mask_file=self.inputs.mask_file,
            cluster_size=self.inputs.cluster_size
        )
        self._results["out_file"] = out_file

        return runtime
