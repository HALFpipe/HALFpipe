import os
import sys
import numpy as np

from pathlib import Path

from nipype.interfaces import utility as niu
from nipype.pipeline import engine as pe
from nipype.interfaces import fsl


from ..utils import create_directory


def f_kendall(timeseries_matrix):
    """
    Calculates the Kendall's coefficient of concordance for a number of
    time-series in the input matrix

    Parameters
    ----------

    timeseries_matrix : ndarray
        A matrix of ranks of a subset subject's brain voxels

    Returns
    -------

    kcc : float
        Kendall's coefficient of concordance on the given input matrix

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
    followed by computing Kendall's coefficient concordance(KCC) of a
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

    print(res_data.shape)
    (n_x, n_y, n_z, n_t) = res_data.shape

    # "flatten" each volume of the timeseries into one big array instead of
    # x,y,z - produces (timepoints, N voxels) shaped data array
    res_data = np.reshape(res_data, (n_x * n_y * n_z, n_t), order='F').T

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
        res_data_sorted = np.sort(res_data_piece, 0, kind='mergesort')
        sort_index = np.argsort(res_data_piece, axis=0, kind='mergesort')

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
                        np.float32(np.sum(ranks[tiestart:tiestart + ntied])) / np.float32(ntied))
                    tiecount += 1

                sorted_ranks[:, tie_adjust_index[i]] = ranks

        del db, sumdb
        sort_index_base = np.tile(np.multiply(np.arange(0, nvoxels_piece), n_t), [n_t, 1])
        sort_index += sort_index_base
        del sort_index_base

        ranks_piece = np.zeros((n_t, nvoxels_piece))

        ranks_piece = ranks_piece.flatten(order='F')
        sort_index = sort_index.flatten(order='F')
        sorted_ranks = sorted_ranks.flatten(order='F')

        ranks_piece[sort_index] = np.array(sorted_ranks)

        ranks_piece = np.reshape(ranks_piece, (n_t, nvoxels_piece), order='F')

        del sort_index, sorted_ranks

        Ranks_res_data[:, segment[0]] = ranks_piece

        sys.stdout.write('.')

    Ranks_res_data = np.reshape(Ranks_res_data, (n_t, n_x, n_y, n_z), order='F')

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

                block = Ranks_res_data[:, i - 1:i + 2, j - 1:j + 2, k - 1:k + 2]
                mask_block = res_mask_data[i - 1:i + 2, j - 1:j + 2, k - 1:k + 2]

                if not (int(mask_block[1, 1, 1]) == 0):

                    if nvoxel == 19 or nvoxel == 7:
                        mask_block = np.multiply(mask_block, mask_cluster)

                    R_block = np.reshape(block, (block.shape[0], 27),
                                         order='F')
                    mask_R_block = R_block[:, np.argwhere(np.reshape(mask_block, (1, 27), order='F') > 0)[:, 1]]

                    K[i, j, k] = f_kendall(mask_R_block)

    img = nb.Nifti1Image(K, header=res_img.get_header(),
                         affine=res_img.get_affine())
    reho_file = os.path.join(os.getcwd(), 'ReHo.nii.gz')
    img.to_filename(reho_file)
    out_file = reho_file

    return out_file


def get_opt_string(mask):
    """
    Method to return option string for 3dTstat

    Parameters
    ----------
    mask : string (file)

    Returns
    -------
    opt_str : string

    """
    opt_str = " -stdev -mask %s" % mask
    return opt_str


def get_operand_string(mean, std_dev):
    """
    Generate the Operand String to be used in workflow nodes to supply
    mean and std deviation to alff workflow nodes

    Parameters
    ----------

    mean: string
        mean value in string format

    std_dev : string
        std deviation value in string format


    Returns
    -------

    op_string : string


    """

    str1 = "-sub %f -div %f" % (float(mean), float(std_dev))

    op_string = str1 + " -mas %s"

    return op_string


def init_reho_wf(use_mov_pars, use_csf, use_white_matter, use_global_signal, subject, output_dir, name="firstlevel"):
    """
    create a workflow to do ReHo and ALFF

    """
    workflow = pe.Workflow(name=name)

    # create directory for desing files
    # /ext/path/to/working_directory/nipype/subject_name/rest/designs
    nipype_dir = Path(output_dir)
    nipype_dir = str(nipype_dir.parent.joinpath('nipype', f'sub_{subject}', 'task_rest', 'designs'))
    create_directory(nipype_dir)

    # inputs are the bold file, the mask file and the regression files
    inputnode = pe.Node(niu.IdentityInterface(
        fields=["bold_file", "mask_file", "confounds_file", "csf_wm_meants_file", "gs_meants_file"]),
        name="inputnode"
    )

    # create design matrix with added regressors to the seed column
    regressor_names = []
    if use_mov_pars:
        regressor_names.append("MovPar")
    if use_csf:
        regressor_names.append("CSF")
    if use_white_matter:
        regressor_names.append("WM")
    if use_global_signal:
        regressor_names.append("GS")

    def create_design(mov_par_file, csf_wm_meants_file, gs_meants_file, regressor_names, file_path):
        """Creates a list of design matrices with added regressors to feed into the glm"""
        import pandas as pd  # in-function import necessary for nipype-function
        mov_par_df = pd.read_csv(mov_par_file, sep=" ", header=None).dropna(how='all', axis=1)
        mov_par_df.columns = ['X', 'Y', 'Z', 'RotX', 'RotY', 'RotZ']
        csf_wm_df = pd.read_csv(csf_wm_meants_file, sep=" ", header=None).dropna(how='all', axis=1)
        csf_wm_df.columns = ['CSF', 'GM', 'WM']
        csf_df = pd.DataFrame(csf_wm_df, columns=['CSF'])
        wm_df = pd.DataFrame(csf_wm_df, columns=['WM'])
        gs_df = pd.read_csv(gs_meants_file, sep=" ", header=None).dropna(how='all', axis=1)
        gs_df.columns = ['GS']
        df = pd.concat([mov_par_df, csf_df, wm_df, gs_df], axis=1)
        if 'MovPar' not in regressor_names:
            df.drop(columns=['X', 'Y', 'Z', 'RotX', 'RotY', 'RotZ'], inplace=True)
        if 'CSF' not in regressor_names:
            df.drop(columns=['CSF'], inplace=True)
        if 'WM' not in regressor_names:
            df.drop(columns=['WM'], inplace=True)
        if 'GS' not in regressor_names:
            df.drop(columns=['GS'], inplace=True)

        df.to_csv(file_path, sep="\t", encoding='utf-8', header=False, index=False)
        return file_path

    design_node = pe.Node(
        niu.Function(
            input_names=["mov_par_file", "csf_wm_meants_file", "gs_meants_file", "regressor_names", "file_path"],
            output_names=["design"],
            function=create_design), name="design_node"
    )
    design_node.inputs.regressor_names = regressor_names
    design_node.inputs.file_path = nipype_dir + f"/{subject}_reho_design.txt"

    glm = pe.Node(
        interface=fsl.GLM(),
        name="glm",
    )
    glm.inputs.out_res_name = 'reho_residuals.nii.gz'

    reho_imports = ['import os', 'import sys', 'import nibabel as nb',
                    'import numpy as np',
                    'from pipeline.workflow.reho import f_kendall']
    raw_reho_map = pe.Node(niu.Function(input_names=['in_file', 'mask_file',
                                                     'cluster_size'],
                                        output_names=['out_file'],
                                        function=compute_reho,
                                        imports=reho_imports),
                           name='reho_cope')
    raw_reho_map.inputs.cluster_size = 27

    # outputs are cope, varcope and zstat for each ICA component and a dof_file
    outputnode = pe.Node(niu.IdentityInterface(
        fields=["reho_cope"]),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, design_node, [
            ("confounds_file", "mov_par_file"),
            ("csf_wm_meants_file", "csf_wm_meants_file"),
            ("gs_meants_file", "gs_meants_file"),
        ]),
        (inputnode, glm, [
            ("bold_file", "in_file"),
        ]),
        (design_node, glm, [
            ("design", "design"),
        ]),
        (glm, raw_reho_map, [
            ("out_res", "in_file"),
        ]),
        (inputnode, raw_reho_map, [
            ("mask_file", "mask_file"),
        ]),
        (raw_reho_map, outputnode, [
            ("out_file", "reho_cope"),
        ]),
    ])

    return workflow

