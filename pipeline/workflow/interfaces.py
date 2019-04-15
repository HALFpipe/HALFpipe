# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
from nipype.interfaces.base import BaseInterface, BaseInterfaceInputSpec, File, TraitedSpec
from nipype.utils.filemanip import split_filename

import nibabel as nib
import numpy as np
import os


class ApplyXfmSegmentationInputSpec(BaseInterfaceInputSpec):
    volume = File(exists=True, desc='Segmentation volume to be tranformed', mandatory=True)


class ApplyXfmSegmentationOutputSpec(TraitedSpec):
    transformed_volume = File(exists=True, desc="Transformed segmentation volume")


class ApplyXfmSegmentation(BaseInterface):
    input_spec = ApplyXfmSegmentationInputSpec
    output_spec = ApplyXfmSegmentationOutputSpec

    def _run_interface(self,
                       xfm="/root/src/pipeline/static/templates/icbm_to_mni_2mm.mat",
                       ref="/root/src/pipeline/static/templates/MNI152lin_T1_2mm.nii.gz"):
        seg_image_path = self.inputs.volume
        if not os.path.exists(seg_image_path):
            print('Error: %s not found' % seg_image_path)
            quit()
        seg_img = nib.load(seg_image_path)
        seg_data = seg_img.get_data()

        ref_img = nib.load(ref)
        ref_data = ref_img.get_data()
        out_data = np.zeros_like(ref_data)
        labels = np.unique(seg_data)[1:]
        print("Found %d non-zero labels." % len(labels))
        for label in labels:
            outdata = np.zeros_like(seg_data)
            outdata[seg_data == label] = 1
            tempbasename = ("%d" % np.random.randint(99999)).zfill(5)
            nib.save(nib.Nifti1Image(outdata, affine=seg_img.affine), '%s.nii.gz' % tempbasename)
            os.system("flirt -ref %s -in %s.nii -applyxfm -init %s -out %s_mni.nii.gz" % (ref, tempbasename, xfm,
                                                                                          tempbasename))

            temp_data = nib.load("%s_mni.nii.gz" % tempbasename).get_data()
            out_data = out_data + (np.round(temp_data) * int(label))
            os.system("rm %s_mni.nii.gz %s.nii.gz" % (tempbasename, tempbasename))
            new_img = nib.Nifti1Image(out_data, ref_img.affine, ref_img.header)
            _, base, _ = split_filename(seg_image_path)
            nib.save(new_img, base + '_inMNI_2mm.nii')

    def _list_outputs(self):
        outputs = self._outputs().get()
        fname = self.inputs.volume
        _, base, _ = split_filename(fname)
        outputs["transformed_volume"] = os.path.abspath(base + '_inMNI_2mm.nii')
        return outputs


# means

class GetSegmentationMeanInputSpec(BaseInterfaceInputSpec):
    image_path = File(exists=True, desc='Segmentation volume to be tranformed', mandatory=True)
    seg_image_path = File(exists=True, desc='Segmentation volume to be tranformed', mandatory=True)


class GetSegmentationMeanOutputSpec(TraitedSpec):
    label_means = File(exists=True, desc="Transformed segmentation volume")


class GetSegmentationMean(BaseInterface):
    input_spec = GetSegmentationMeanInputSpec
    output_spec = GetSegmentationMeanOutputSpec

    def _run_interface(self, delimiter=' '):
        image_path = self.inputs.image_path
        seg_image_path = self.inputs.seg_image_path

        if not os.path.exists(image_path):
            raise Exception('Error: %s not found' % image_path)
        if not os.path.exists(seg_image_path):
            raise Exception('Error: %s not found' % seg_image_path)

        seg = nib.load(seg_image_path).get_data()
        mask_index = seg != 0
        base, file_ext = os.path.splitext(image_path)
        if file_ext == '.gz':
            file_ext = os.path.splitext(base)[1]
            if file_ext == '.nii':
                if os.path.getsize(image_path) < 50000000:
                    image = nib.load(image_path)
                    image_data = image.get_data()
                else:
                    tempname = ("%d" % np.random.randint(99999)).zfill(5) + '.nii'
                    os.system("zcat %s > %s" % (image_path, tempname))
                    image = nib.load(tempname)
                    image_data = image.get_data()
                    os.system("rm %s" % tempname)
            else:
                raise Exception('Error: filetype for %s is not supported' % image_path)
        elif file_ext == '.nii':
            image = nib.load(image_path)
            image_data = image.get_data()
        else:
            raise Exception('Error filetype for %s is not supported' % file_ext)
        # Selected index voxels in segmented data,
        image_data = image_data[mask_index]
        seg_data = seg[mask_index]

        output_column = []
        for label in np.unique(seg_data):
            temp = image_data[seg_data == label]
            output_column.append(np.mean(temp[temp.mean(1) != 0], 0))

        _, base, _ = split_filename(image_path)
        output_file = '%s_seg_covars.csv' % base
        if output_file is not None:
            np.savetxt(output_file, np.array(output_column).T, fmt='%1.5f', delimiter=delimiter)

    def _list_outputs(self):
        outputs = self._outputs().get()
        fname = self.inputs.image_path
        _, base, _ = split_filename(fname)
        outputs["label_means"] = os.path.abspath(base + '_seg_covars.csv')
        return outputs
