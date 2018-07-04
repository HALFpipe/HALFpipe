from os import path as op
import os

import gzip

from shutil import copy, copyfileobj

from niworkflows.nipype.interfaces.base import (
    isdefined, 
    SimpleInterface
)

from fmriprep.interfaces.bids import (
    DerivativesDataSink,
    _splitext
)

class FakeBIDSLayout:
    def __init__(self, 
        bold_file, metadata):
        
        self.bold_file = bold_file
        self.metadata = metadata
    
    def get_metadata(self, path):
        if path == self.bold_file:
            return self.metadata
        else:
            return dict()
    
    def get_fieldmap(self, path, return_list = False):
        return []

def _find(target, d):
    for k, v in d.items():
        if isinstance(v, str) and v == target:
            return k
        elif isinstance(v, dict):
            a = _find(target, v)
            if a is not None:
                return k + "/" + a  
    return None

class FakeDerivativesDataSink(DerivativesDataSink):
    def __init__(self, images, fake_output_dir, **inputs):
        super(FakeDerivativesDataSink, self).__init__(**inputs)
        
        self.fake_output_dir = fake_output_dir
        self.images = images

    def _run_interface(self, runtime):
        out_path = _find(self.inputs.source_file, self.images)
        
        if out_path is None:
            for k in self.images.keys():
                if k in self.inputs.in_file[0]:
                    out_path = k
            if "anat" in self.inputs.in_file[0]:
                out_path = out_path + "/" + "T1w"
        
        _, ext = _splitext(self.inputs.in_file[0])
        compress = ext == '.nii'
        if compress:
            ext = '.nii.gz'

        base_directory = runtime.cwd
        if isdefined(self.inputs.base_directory):
            base_directory = op.abspath(self.inputs.base_directory)
        
        if base_directory == self.fake_output_dir:
            return runtime
        
        if out_path is None:
            out_path = ""
            
        out_path = op.join(base_directory, out_path)

        os.makedirs(out_path, exist_ok = True)

        formatstr = '{suffix}{ext}'
        if len(self.inputs.in_file) > 1 and not isdefined(self.inputs.extra_values):
            formatstr = '{suffix}{i:04d}{ext}'

        for i, fname in enumerate(self.inputs.in_file):
            out_file = formatstr.format(
                suffix = self.inputs.suffix,
                i = i,
                ext = ext
            )
            
            if isdefined(self.inputs.extra_values):
                out_file = out_file.format(
                    extra_value = self.inputs.extra_values[i]
                )
                
            out_file = op.join(out_path, out_file)
                
            self._results['out_file'].append(out_file)
            
            if compress:
                with open(fname, 'rb') as f_in:
                    with gzip.open(out_file, 'wb') as f_out:
                        copyfileobj(f_in, f_out)
            else:
                copy(fname, out_file)

        return runtime

class FakeReadSidecarJSON(SimpleInterface):
    def _run_interface(self, runtime):
        pass
