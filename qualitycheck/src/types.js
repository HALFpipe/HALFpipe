// order and renaming
export default [
  {
    tag: "func_preproc_wf.fmap_unwarp_report_wf.ds_report_sdc.sdc_syn",
    type: "EPI distortion correction"
  },
  {
    tag: "func_preproc_wf.bold_reg_wf.ds_report_reg.flt_bbr",
    type: "EPI alignment to T1w reference"
  },
  {
    tag: "T1w.anat_reports_wf.ds_t1_2_mni_report.t1_2_mni",
    type: "T1w spatial normalization"
  },
  {
    tag: "T1w.anat_reports_wf.ds_t1_seg_mask_report.seg_brainmask",
    type: "T1w skull-stripping and segmentation"
  },
  {
    tag: "func_preproc_wf.carpetplot_wf.ds_report_bold_conf.carpetplot",
    type: "EPI Confounds"
  },
  {
    tag: "func_preproc_wf.ica_aroma_wf.ds_report_ica_aroma.ica_aroma",
    type: "EPI ICA-based artifact removal"
  },
  {
    tag: "ds_tsnr.tsnr",
    type: "EPI tSNR"
  }
];
