from os import path as op
import os

import json

qc_result = None

def get_qualitycheck_result(base_directory, target):
    if qc_result is None:
        qc_result_fname = op.join(base_directory, "qcresult.json")
        if op.isfile(qc_result_fname):
            with open(qc_result_fname) as qc_result_file:    
                qc_result = json.load(qc_result_file)
    
    if qc_result is not None:
        pass
    
    return False