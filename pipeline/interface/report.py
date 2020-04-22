# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from os import path as op
import pkg_resources
from uuid import uuid4

import numpy as np
import nibabel as nib
from matplotlib import pyplot as plt
from svgutils.transform import fromstring
from seaborn import color_palette


from nipype.interfaces.base import (
    traits,
    TraitedSpec,
    SimpleInterface,
    File,
    isdefined,
)

from niworkflows.interfaces.report_base import ReportingInterface, _SVGReportCapableInputSpec
from niworkflows.viz.utils import compose_view, extract_svg, cuts_from_bbox
from nilearn.plotting import plot_epi, plot_anat

from ..io import img_to_signals, load_spreadsheet
from ..utils import nvol


report_metadata_fields = ["mean_fd", "fd_gt_0_5", "aroma_noise_frac", "mean_gm_tsnr"]


class BoldFileReportMetadataInputSpec(TraitedSpec):
    basedict = traits.Dict(traits.Str(), traits.Any())
    confounds = File(exists=True, mandatory=True)
    tsnr_file = File(exists=True, mandatory=True)
    dseg = File(exists=True, mandatory=True)
    aroma_metadata = traits.Dict(traits.Str(), traits.Any(), exists=True, mandatory=True)


class BoldFileReportMetadataOutputSpec(TraitedSpec):
    outdict = traits.Dict(traits.Str(), traits.Any())


class BoldFileReportMetadata(SimpleInterface):
    input_spec = BoldFileReportMetadataInputSpec
    output_spec = BoldFileReportMetadataOutputSpec

    def _run_interface(self, runtime):
        outdict = dict()

        df_confounds = load_spreadsheet(self.inputs.confounds)
        outdict["mean_fd"] = df_confounds["framewise_displacement"].mean()
        outdict["fd_gt_0_5"] = (df_confounds["framewise_displacement"] > 0.5).mean()

        aroma_metadata = self.inputs.aroma_metadata
        outdict["aroma_noise_frac"] = np.asarray(
            [val["MotionNoise"] is True for val in aroma_metadata.values()]
        ).mean()

        _, outdict["mean_gm_tsnr"], _ = img_to_signals(
            self.inputs.tsnr_file, self.inputs.dseg
        ).ravel()

        if isdefined(self.inputs.basedict):
            outdict.update(self.inputs.basedict)

        self._results["outdict"] = outdict

        return runtime


class PlotInputSpec(_SVGReportCapableInputSpec):
    in_file = File(exists=True, mandatory=True, desc="volume")
    mask_file = File(exists=True, mandatory=True, desc="mask")
    label = traits.Str()


class PlotEpi(ReportingInterface):
    input_spec = PlotInputSpec

    def _generate_report(self):
        in_img = nib.load(self.inputs.in_file)
        assert nvol(in_img) == 1

        mask_img = nib.load(self.inputs.mask_file)
        assert nvol(mask_img) == 1

        label = None
        if isdefined(self.inputs.label):
            label = self.inputs.label

        compress = self.inputs.compress_report

        n_cuts = 7
        cuts = cuts_from_bbox(mask_img, cuts=n_cuts)

        img_vals = in_img.get_fdata()[np.asanyarray(mask_img.dataobj).astype(np.bool)]
        vmin = img_vals.min()
        vmax = img_vals.max()

        outfiles = []
        for dimension in ["z", "y", "x"]:
            display = plot_epi(
                in_img,
                draw_cross=False,
                display_mode=dimension,
                cut_coords=cuts[dimension],
                title=label,
                vmin=vmin,
                vmax=vmax,
                colorbar=(dimension == "z"),
                cmap=plt.cm.gray,
            )
            display.add_contours(mask_img, levels=[0.5], colors="r")
            label = None  # only on first
            svg = extract_svg(display, compress=compress)
            svg = svg.replace("figure_1", str(uuid4()), 1)
            outfiles.append(fromstring(svg))

        self._out_report = op.abspath(self.inputs.out_report)
        compose_view(bg_svgs=outfiles, fg_svgs=None, out_file=self._out_report)


class PlotRegistration(ReportingInterface):
    input_spec = PlotInputSpec

    def _generate_report(self):
        in_img = nib.load(self.inputs.in_file)
        assert nvol(in_img) == 1

        mask_img = nib.load(self.inputs.mask_file)
        assert nvol(mask_img) == 1

        parc_file = pkg_resources.resource_filename("pipeline", "registrationCheckParc.nii.gz")
        parc_img = nib.load(parc_file)

        levels = np.unique(np.asanyarray(parc_img.dataobj).astype(np.int32))
        levels = (levels[levels > 0] - 0.5).tolist()
        colors = color_palette("husl", len(levels))

        label = None
        if isdefined(self.inputs.label):
            label = self.inputs.label

        compress = self.inputs.compress_report

        n_cuts = 7
        cuts = cuts_from_bbox(mask_img, cuts=n_cuts)

        outfiles = []
        for dimension in ["z", "y", "x"]:
            display = plot_anat(
                in_img,
                draw_cross=False,
                display_mode=dimension,
                cut_coords=cuts[dimension],
                title=label,
            )
            display.add_contours(parc_img, levels=levels, colors=colors, linewidths=0.25)
            display.add_contours(mask_img, levels=[0.5], colors="r", linewidths=0.5)
            label = None  # only on first
            svg = extract_svg(display, compress=compress)
            svg = svg.replace("figure_1", str(uuid4()), 1)
            outfiles.append(fromstring(svg))

        self._out_report = op.abspath(self.inputs.out_report)
        compose_view(bg_svgs=outfiles, fg_svgs=None, out_file=self._out_report)
