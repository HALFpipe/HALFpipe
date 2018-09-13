// order and renaming
export default [
  {
    tag: "T1w.anat_reports_wf.ds_t1_seg_mask_report.seg_brainmask",
    type: "Skull-stripping"
  },
  {
    tag: "T1w.anat_reports_wf.ds_t1_2_mni_report.t1_2_mni",
    type: "Spatial normalization"
  },
  {
    tag: "func_preproc_wf.bold_reg_wf.ds_report_reg.flt_bbr",
    type: "Alignment to T1w reference"
  },
  {
    tag: "func_preproc_wf.fmap_unwarp_report_wf.ds_report_sdc.sdc_syn",
    type: "Distortion correction"
  },
  {
    tag: "func_preproc_wf.bold_confounds_wf.ds_report_bold_rois.rois",
    type: "Segmentation"
  },
  {
    tag: "func_preproc_wf.carpetplot_wf.ds_report_bold_conf.carpetplot",
    type: "Confounds"
  },
  {
    tag: "func_preproc_wf.ica_aroma_wf.ds_report_ica_aroma.ica_aroma",
    type: "ICA-AROMA"
  }
];
