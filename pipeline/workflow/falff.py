import os
from pathlib import Path

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces import fsl
from nipype.interfaces.afni import TStat, Calc, Bandpass
import nipype.interfaces.io as nio

from .reho import get_opt_string
from ..utils import create_directory


def create_falff(use_mov_pars, use_csf, use_white_matter, use_global_signal, subject, output_dir,
                 name='falff_workflow'):
    """
    See Documentation in alff workflow
    """

    wf = pe.Workflow(name=name)

    # create directory for design files
    # /ext/path/to/working_directory/nipype/subject_name/rest/designs
    nipype_dir = Path(output_dir)
    nipype_dir = str(nipype_dir.parent.joinpath('nipype', f'sub_{subject}', 'task_rest', 'designs'))
    create_directory(nipype_dir)

    inputnode = pe.Node(util.IdentityInterface(
                        fields=["bold_file", "mask_file", 
                                "movpar_file", "csf_wm_label_string"]),
                        name="inputnode"
    )

    inputnode_hp = pe.Node(util.IdentityInterface(fields=['hp']),
                           name='hp_input')
    inputnode_hp.inputs.hp = 0.009

    inputnode_lp = pe.Node(util.IdentityInterface(fields=['lp']),
                           name='lp_input')
    inputnode_lp.inputs.lp = 0.08

    # filtering
    bandpass = pe.Node(interface=Bandpass(),
                       name='bandpass_filtering')
    bandpass.inputs.outputtype = 'NIFTI_GZ'
    bandpass.inputs.out_file = os.path.join(os.path.curdir, 'residual_filtered.nii.gz')

    # Calculates the regression time series for CSF and white matter
    csf_wm_meants = pe.Node(
        interface=fsl.ImageMeants(),
        name="csf_wm_meants",
    )

    # Calculates the regression time series for global signal
    gs_meants = pe.Node(
        interface=fsl.ImageMeants(),
        name="gs_meants",
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

    def create_design(movpar_file, csf_wm_meants_file, gs_meants_file, regressor_names, file_path):
        """Creates a list of design matrices with added regressors to feed into the glm"""
        import pandas as pd  # in-function import necessary for nipype-function
        mov_par_df = pd.read_csv(movpar_file, sep=" ", header=None).dropna(how='all', axis=1)
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
            input_names=["movpar_file", "csf_wm_meants_file", 
                         "gs_meants_file", "regressor_names", "file_path"],
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

    outputnode = pe.Node(util.IdentityInterface(
                         fields=["falff_cope", "falff_zstat"]),
                         name="outputnode"
    )

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

    # datasinks for falff images

    ds_falff = pe.Node(
        nio.DataSink(
            base_directory=output_dir,
            container=subject,
            substitutions=[('ref_image_corrected_brain_mask_maths_trans_calc', 'falff_img')],
            parameterization=False),
        name="ds_falff", run_without_submitting=True)

    # calculate zstats from imgs

    # falff
    # calculate mean
    falff_stats_mean = pe.Node(
        interface=fsl.ImageStats(),
        name="falff_stats_mean",
    )
    falff_stats_mean.inputs.op_string = '-M'

    # calculate std
    falff_stats_std = pe.Node(
        interface=fsl.ImageStats(),
        name="falff_stats_std",
    )
    falff_stats_std.inputs.op_string = '-S'

    # substract mean from img
    # Creates op_string for fslmaths

    # substract mean from img
    # Creates op_string for fslmaths
    def get_sub_op_string(in_file):
        """

        :param in_file: mean value of the img
        :return: op_string for fslmaths
        """
        op_string = '-sub ' + str(in_file)
        return op_string

    fsub_op_string = pe.Node(
        name="fsub_op_string",
        interface=util.Function(input_names=["in_file"],
                                output_names=["op_string"],
                                function=get_sub_op_string),
    )

    # fslmaths cmd
    falff_maths_sub = pe.Node(
        interface=fsl.ImageMaths(),
        name="falff_maths_sub",
    )

    # divide by std
    # Creates op_string for fslmaths
    def get_div_op_string(in_file):
        """

        :param in_file: std value of the img
        :return: op_string for fslmaths
        """
        op_string = '-div ' + str(in_file)
        return op_string

    fdiv_op_string = pe.Node(
        name="fdiv_op_string",
        interface=util.Function(input_names=["in_file"],
                                output_names=["op_string"],
                                function=get_div_op_string),
    )
    falff_maths_div = pe.Node(
        interface=fsl.ImageMaths(),
        name="falff_maths_div",
    )
    
    # save file in intermediates
    ds_falff_zstat = pe.Node(
        nio.DataSink(
            base_directory=output_dir,
            container=subject,
            substitutions=[
                ('ref_image_corrected_brain_mask_maths_trans_calc_maths_maths', 'falff_zstat')
            ],
            parameterization=False),
        name="ds_falff_zstat", run_without_submitting=True)

    wf.connect([
        (inputnode, csf_wm_meants, [
            ("bold_file", "in_file"),
        ]),
        (inputnode, csf_wm_meants, [
            ("csf_wm_label_string", "args"),
        ]),
        (csf_wm_meants, design_node, [
            ("out_file", "csf_wm_meants_file"),
        ]),
        (inputnode, gs_meants, [
            ("bold_file", "in_file")
        ]),
        (inputnode, gs_meants, [
            ("mask_file", "mask")
        ]),
        (gs_meants, design_node, [
            ("out_file", "gs_meants_file")
        ]),
        (inputnode, design_node, [
            ("movpar_file", "movpar_file")
        ]),
        (inputnode, glm, [
            ("bold_file", "in_file"),
        ]),
        (design_node, glm, [
            ("design", "design"),
        ]),
        (glm, bandpass, [
            ("out_res", "in_file"),
        ]),
        (inputnode_hp, bandpass, [
            ("hp", "highpass"),
        ]),
        (inputnode_lp, bandpass, [
            ("lp", "lowpass"),
        ]),
        (inputnode, get_option_string, [
            ("mask_file", "mask"),
        ]),
        (inputnode, stddev_unfltrd, [
            ("bold_file", "in_file"),
        ]),
        (inputnode, falff, [
            ("mask_file", "in_file_a"),
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
        (stddev_fltrd, falff, [
            ("out_file", "in_file_b"),
        ]),
        (stddev_unfltrd, falff, [
            ("out_file", "in_file_c"),
        ]),
        (falff, ds_falff, [
            ("out_file", "rest.@fallf"),
        ]),
        (falff, falff_stats_mean, [
            ("out_file", "in_file"),
        ]),
        (falff_stats_mean, fsub_op_string, [
            ("out_stat", "in_file"),
        ]),
        (falff, falff_maths_sub, [
            ("out_file", "in_file"),
        ]),
        (fsub_op_string, falff_maths_sub, [
            ("op_string", "op_string"),
        ]),
        (falff, falff_stats_std, [
            ("out_file", "in_file"),
        ]),
        (falff_stats_std, fdiv_op_string, [
            ("out_stat", "in_file"),
        ]),
        (falff_maths_sub, falff_maths_div, [
            ("out_file", "in_file"),
        ]),
        (fdiv_op_string, falff_maths_div, [
            ("op_string", "op_string"),
        ]),
        (falff_maths_div, ds_falff_zstat, [
            ("out_file", "rest.@alff_zstat"),
        ]),
        (falff_maths_div, outputnode, [
            ("out_file", "falff_zstat"),
        ]),
        (falff, outputnode, [
            ("out_file", "falff_cope"),
        ]),
    ])

    return wf
