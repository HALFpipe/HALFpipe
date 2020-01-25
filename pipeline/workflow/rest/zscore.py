# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import nipype.pipeline.engine as pe
import nipype.interfaces.utility as util
from nipype.interfaces import fsl


def init_zscore_wf(name="zscore"):
    """
    Within-volume z score
    Used for ReHo and ALFF
    """
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface=util.IdentityInterface(
            fields=["in_file", "mask_file"]),
        name="inputnode"
    )

    stats = pe.Node(
        interface=fsl.ImageStats(),
        name="stats",
    )
    stats.inputs.op_string = "-k %s -m -s"

    def get_zscore_op_string(list):
        """
        creates op_string for fslmaths
        :param list
        :return: op_string for fslmaths
        """
        return "-sub {:f} -div {:f}".format(*list)

    zscore = pe.Node(
        interface=fsl.ImageMaths(),
        name="zscore",
    )

    outputnode = pe.Node(
        interface=util.IdentityInterface(
            fields=["out_file"]),
        name="outputnode"
    )

    workflow.connect([
        (inputnode, stats, [
            ("in_file", "in_file"),
            ("mask_file", "mask_file")
        ]),
        (inputnode, zscore, [
            ("in_file", "in_file"),
            ("mask_file", "mask_file")
        ]),
        (stats, zscore, [
            (("out_stat", get_zscore_op_string), "op_string")
        ]),
        (zscore, outputnode, [
            ("out_file", "out_file")
        ])
    ])

    return workflow
