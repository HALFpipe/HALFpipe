from os import path as op
import os

import json


def get_qualitycheck_exclude(base_directory):
    qc_result = {}
    qc_result_fname = op.join(base_directory, "qcresult.json")
    if op.isfile(qc_result_fname):
        with open(qc_result_fname) as qc_result_file:    
            qc_result = json.load(qc_result_file)
    
    exclude = {}
    for sub, value0 in qc_result.items():
        if sub not in exclude:
            exclude[sub] = {}
        for task, value1 in value0.items():
            if task not in exclude[sub]:
                exclude[sub][task] = False
            for run, value2 in value1.items():
                if task == "T1w":
                    pass
                else:
                    for k, v in value2.items():
                        if v == "bad": 
                            exclude[sub][task] = True
    
    for sub, value0 in qc_result.items():
        if sub not in exclude:
            exclude[sub] = {}
        for task, value1 in value0.items():
            if task not in exclude[sub]:
                exclude[sub][task] = False
            for run, value2 in value1.items():
                if task == "T1w":
                    value = False
                    for k, v in value2.items():
                        if v == "bad": 
                            value = True
                    for k in exclude[sub].keys():
                        exclude[sub][k] |= value
                        
    return exclude