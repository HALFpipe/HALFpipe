from os import path as op
import os

import gzip
import fasteners
import json

from shutil import copy, copyfileobj

from nipype.interfaces.base import (
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
    def __init__(self, 
            images, 
            fmriprep_reportlets_dir, fmriprep_output_dir, 
            node_id, depends, 
            **inputs):
        super(FakeDerivativesDataSink, self).__init__(**inputs)
        
        self.fmriprep_reportlets_dir = fmriprep_reportlets_dir
        self.fmriprep_output_dir = fmriprep_output_dir
        self.node_id = node_id
        self.depends = depends
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
        
        if base_directory == self.fmriprep_output_dir:
            # don't copy file
            return runtime
        elif base_directory == self.fmriprep_reportlets_dir:
            # write to json
            
            work_dir = op.dirname(base_directory)
            json_data = {"id": "%s.%s" % (self.node_id, self.inputs.suffix), 
                "depends": self.depends, "html": ""}
            for i, fname in enumerate(self.inputs.in_file):
                with open(fname, "r") as f:
                    json_data["html"] += f.read()
            
            with fasteners.InterProcessLock(op.join(work_dir, "qc.lock")):
                json_file = op.join(work_dir, "qc.json")
                    
                with open(json_file, "ab+") as f:
                    f.seek(0, 2)       
                    
                    if f.tell() == 0:
                        f.write(json.dumps([json_data]).encode())
                    else:
                        f.seek(-1, 2)
                        f.truncate()
                        f.write(','.encode())
                        f.write(json.dumps(json_data).encode())
                        f.write(']'.encode())  
        else:
            # copy file to out_path
            
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
