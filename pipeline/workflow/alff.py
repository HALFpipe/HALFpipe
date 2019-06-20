import os
from pathlib import Path

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces import fsl
from nipype.interfaces.afni import TStat, Calc, Bandpass
import nipype.interfaces.io as nio
from fmriprep.interfaces.bids import DerivativesDataSink


from .reho import get_opt_string
from ..utils import create_directory


def create_alff(use_mov_pars, use_csf, use_white_matter, use_global_signal, subject, output_dir, name='alff_workflow'):
    """
    Calculate Amplitude of low frequency oscillations(ALFF) and fractional ALFF maps

    Returns
    -------
    alff_workflow : workflow object
        ALFF workflow

    Notes
    -----
    `Source <https://github.com/FCP-INDI/C-PAC/blob/master/CPAC/alff/alff.py>`_

    Workflow Inputs::

        hp_input.hp : list (float)
            high pass frequencies

        lp_input.lp : list (float)
            low pass frequencies

        inputspec.rest_res : string (existing nifti file)
            Nuisance signal regressed functional image

        inputspec.rest_mask : string (existing nifti file)
            A mask volume(derived by dilating the motion corrected functional volume) in native space


    Workflow Outputs::

        outputspec.alff_cope : string (nifti file)
            outputs image containing the sum of the amplitudes in the low frequency band

        outputspec.falff_cope : string (nifti file)
            outputs image containing the sum of the amplitudes in the low frequency band divided by the
            amplitude of the total frequency

        outputspec.alff_Z_img : string (nifti file)
            outputs image containing Normalized ALFF Z scores across full brain in native space

        outputspec.falff_Z_img : string (nifti file)
            outputs image containing Normalized fALFF Z scores across full brain in native space


    Order of Commands:

    - Filter the input file rest file( slice-time, motion corrected and nuisance regressed) ::
        3dBandpass -prefix residual_filtered.nii.gz
                    0.009 0.08 residual.nii.gz

    - Calculate ALFF by taking the standard deviation of the filtered file ::
        3dTstat -stdev
                -mask rest_mask.nii.gz
                -prefix residual_filtered_3dT.nii.gz
                residual_filtered.nii.gz

    - Calculate the standard deviation of the unfiltered file ::
        3dTstat -stdev
                -mask rest_mask.nii.gz
                -prefix residual_3dT.nii.gz
                residual.nii.gz

    - Calculate fALFF ::
        3dcalc -a rest_mask.nii.gz
               -b residual_filtered_3dT.nii.gz
               -c residual_3dT.nii.gz
               -expr '(1.0*bool(a))*((1.0*b)/(1.0*c))' -float

    - Normalize ALFF/fALFF to Z-score across full brain ::

        fslstats
        ALFF.nii.gz
        -k rest_mask.nii.gz
        -m > mean_ALFF.txt ; mean=$( cat mean_ALFF.txt )

        fslstats
        ALFF.nii.gz
        -k rest_mask.nii.gz
        -s > std_ALFF.txt ; std=$( cat std_ALFF.txt )

        fslmaths
        ALFF.nii.gz
        -sub ${mean}
        -div ${std}
        -mas rest_mask.nii.gz ALFF_Z.nii.gz

        fslstats
        fALFF.nii.gz
        -k rest_mask.nii.gz
        -m > mean_fALFF.txt ; mean=$( cat mean_fALFF.txt )

        fslstats
        fALFF.nii.gz
        -k rest_mask.nii.gz
        -s > std_fALFF.txt
        std=$( cat std_fALFF.txt )

        fslmaths
        fALFF.nii.gz
        -sub ${mean}
        -div ${std}
        -mas rest_mask.nii.gz
        fALFF_Z.nii.gz

    High Level Workflow Graph:

    .. image:: ../images/alff.dot.png
        :width: 500

    Detailed Workflow Graph:

    .. image:: ../images/alff_detailed.dot.png
        :width: 500


    References
    ----------

    .. [1] Zou, Q.-H., Zhu, C.-Z., Yang, Y., Zuo, X.-N., Long, X.-Y., Cao, Q.-J., Wang, Y.-F., et al. (2008).
    An improved approach to detection of amplitude of low-frequency fluctuation (ALFF) for resting-state fMRI:
    fractional ALFF. Journal of neuroscience methods, 172(1), 137-41. doi:10.10

    Examples
    --------

    # >>> alff_w = create_alff()
    # >>> alff_w.inputs.hp_input.hp = [0.01]
    # >>> alff_w.inputs.lp_input.lp = [0.1]
    # >>> alff_w.get_node('hp_input').iterables = ('hp',[0.01])
    # >>> alff_w.get_node('lp_input').iterables = ('lp',[0.1])
    # >>> alff_w.inputs.inputspec.rest_res = '/home/data/subject/func/rest_bandpassed.nii.gz'
    # >>> alff_w.inputs.inputspec.rest_mask= '/home/data/subject/func/rest_mask.nii.gz'
    # >>> alff_w.run() # doctest: +SKIP


    """

    wf = pe.Workflow(name=name)

    # create directory for design files
    # /ext/path/to/working_directory/nipype/subject_name/rest/designs
    nipype_dir = Path(output_dir)
    nipype_dir = str(nipype_dir.parent.joinpath('nipype', f'sub_{subject}', 'task_rest', 'designs'))
    create_directory(nipype_dir)

    input_node = pe.Node(util.IdentityInterface(
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
        util.Function(
            input_names=["mov_par_file", "csf_wm_meants_file", "gs_meants_file", "regressor_names", "file_path"],
            output_names=["design"],
            function=create_design), name="design_node"
    )
    design_node.inputs.regressor_names = regressor_names
    design_node.inputs.file_path = nipype_dir + f"/{subject}_alff_design.txt"

    glm = pe.Node(
        interface=fsl.GLM(),
        name="glm",
    )
    glm.inputs.out_res_name = 'alff_residuals.nii.gz'

    inputnode_hp = pe.Node(util.IdentityInterface(fields=['hp']),
                           name='hp_input')

    inputnode_lp = pe.Node(util.IdentityInterface(fields=['lp']),
                           name='lp_input')

    outputnode = pe.Node(util.IdentityInterface(fields=['alff_cope',
                                                        'falff_cope']),
                         name='outputnode')

    # filtering
    bandpass = pe.Node(interface=Bandpass(),
                       name='bandpass_filtering')
    bandpass.inputs.outputtype = 'NIFTI_GZ'
    bandpass.inputs.out_file = os.path.join(os.path.curdir, 'residual_filtered.nii.gz')

    get_option_string = pe.Node(util.Function(input_names=['mask'],
                                              output_names=['option_string'],
                                              function=get_opt_string),
                                name='get_option_string')

    # standard deviation over frequency
    stddev_fltrd = pe.Node(interface=TStat(),
                           name='stddev_fltrd')
    stddev_fltrd.inputs.outputtype = 'NIFTI_GZ'
    stddev_fltrd.inputs.out_file = os.path.join(os.path.curdir, 'residual_filtered_3dT.nii.gz')

    # standard deviation of the unfiltered nuisance corrected image
    stddev_unfltrd = pe.Node(interface=TStat(),
                             name='stddev_unfltrd')
    stddev_unfltrd.inputs.outputtype = 'NIFTI_GZ'
    stddev_unfltrd.inputs.out_file = os.path.join(os.path.curdir, 'residual_3dT.nii.gz')

    # falff calculations
    falff = pe.Node(interface=Calc(),
                    name='falff')
    falff.inputs.args = '-float'
    falff.inputs.expr = '(1.0*bool(a))*((1.0*b)/(1.0*c))'
    falff.inputs.outputtype = 'NIFTI_GZ'

    # datasinks for alff/falff images
    ds_alff = pe.Node(
        nio.DataSink(
            base_directory=output_dir,
            container=subject,
            substitutions=[('residual_filtered_3dT', 'alff_img')],
            parameterization=False),
        name="ds_alff", run_without_submitting=True)

    ds_falff = pe.Node(
        nio.DataSink(
            base_directory=output_dir,
            container=subject,
            substitutions=[('ref_image_corrected_brain_mask_maths_trans_calc', 'falff_img')],
            parameterization=False),
        name="ds_falff", run_without_submitting=True)

    wf.connect([
        (input_node, design_node, [
            ("confounds_file", "mov_par_file"),
            ("csf_wm_meants_file", "csf_wm_meants_file"),
            ("gs_meants_file", "gs_meants_file"),
        ]),
        (input_node, glm, [
            ("bold_file", "in_file"),
        ]),
        (design_node, glm, [
            ("design", "design"),
        ]),
        (glm, bandpass, [
            ("out_res", "in_file"),
        ]),
        (input_node, get_option_string, [
            ("mask_file", "mask"),
        ]),
        (glm, stddev_unfltrd, [
            ("out_res", "in_file"),
        ]),
        (input_node, falff, [
            ("mask_file", "in_file_a"),
        ]),
        (inputnode_hp, bandpass, [
            ("hp", "highpass"),
        ]),
        (inputnode_lp, bandpass, [
            ("lp", "lowpass"),
        ]),
        (bandpass, stddev_fltrd, [
            ("out_file", "in_file"),
        ]),
        (get_option_string, stddev_fltrd, [
            ("option_string", "options"),
        ]),
        (get_option_string, stddev_unfltrd, [
            ("option_string", "options"),
        ]),
        (stddev_fltrd, ds_alff, [
            ("out_file", "rest.@alff"),
        ]),
        (stddev_fltrd, outputnode, [
            ("out_file", "alff_cope"),
        ]),
        (stddev_fltrd, falff, [
            ("out_file", "in_file_b"),
        ]),
        (stddev_unfltrd, falff, [
            ("out_file", "in_file_c"),
        ]),
        (falff, ds_falff, [
            ("out_file", "rest.@fallf"),
        ]),
        (falff, outputnode, [
            ("out_file", "falff_cope"),
        ]),
    ])

    return wf
