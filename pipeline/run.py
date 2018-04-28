#!/usr/bin/env python
# -*- coding: utf-8 -*-

from glob import glob
from os import path as op
from os import (
    listdir,
    mkdir
)

import nibabel as nib

import re
import json

from .cli import cli

from .conditions import parse_condition_files

from .info import __version__

from .workflow import init_workflow

EXT_PATH = "/ext"

KNOWN_TASKS = {"FACES": ["FACES", "SHAPES"], \
    "MID": ["REWARD", "NEUTRAL"],
    "NBACK": ["2BACK", "0BACK"]}
CONTRASTS = {"FACES": [1, -1], \
    "MID": [1, -1],
    "NBACK": [1, -1]}

def main():
    c = cli()
    
    c.info("mindandbrain pipeline %s" % __version__)
    c.info("")
    
    #
    # tests
    #
    
    import termios
    try:
        import sys, tty
        tty.setraw(sys.stdin)
        tty.setcbreak(sys.stdin)
    except termios.error:
        c.error("Did you forget the docker arguments \"--interactive --tty\"?")
        raise
    
    if not (op.isdir(EXT_PATH) and len(listdir(EXT_PATH)) > 0):
        c.error("Can not access host files at path %s. Did you forget the docker argument \"--mount ...\"?" % EXT_PATH)
        
    def get_path(path):
        path = path.strip()
        
        if path.startswith("/"):
            path = path[1:]
        
        path = op.join(EXT_PATH, path)
        
        return path
    
    #
    # data structures
    #
    
    images = dict()
    metadata = dict()
    field_maps = dict()
    
    #
    # working dir
    #
    
    workdir = get_path(c.read("Specify the working directory"))
    
    if not op.isdir(workdir):
        mkdir(workdir)
    
    c.info("")
    
    #
    # helper functions
    #
        
    def get_files(description, runs = False, conditions = False):
        files = dict()
        
        c.info("Specify the path to the %s files" % description)
        
        if runs:
            c.info("Put \"?\" in place of run numbers")
        
        if conditions:
            c.info("Put \"$\" in place of condition names")
        
        path = get_path(c.read("Put \"*\" in place of the subject names"))
        
        regex0_str = path.replace("?", "(?P=run.+)")
        regex0_str = regex0_str.replace("(?P=run.+)", "(?P<run>.+)", 1)
        regex0_str = regex0_str.replace("*", "(?P=subject.+)")
        regex0_str = regex0_str.replace("(?P=subject.+)", "(?P<subject>.+)", 1)
        regex0_str = regex0_str.replace("$", "(?P=condition.+)")
        regex0_str = regex0_str.replace("(?P=condition.+)", "(?P<condition>.+)", 1)
        regex0 = re.compile(regex0_str)
        
        glob_path = path.replace("?", "*")
        glob_path = glob_path.replace("$", "*")
        glob_result = glob(glob_path)
        
        c.info("Found %i %s files" % (len(glob_result), description))
        
        for g in glob_result:
            m = regex0.match(g)
            
            if m is not None:
                d = m.groupdict()
                
                subject = ""
                if "subject" in d:
                    subject = d["subject"]
                
                run = ""
                if runs and "run" in d:
                    run = str(int(d["run"]))                    
                
                if subject not in files:
                    files[subject] = dict()
                    
                if conditions:
                    condition = ""
                    if "condition" in d:
                        condition = d["condition"]
                    if run not in files[subject]:
                        files[subject][run] = dict()
                    files[subject][run][condition] = g
                elif runs:
                    files[subject][run] = g
                else:
                    files[subject] = g
                
        if len(files) == 0:
            response = c.select("Try again?", ["Yes", "No"])
            
            if response == "Yes":
                return getFiles(description)
            
        return files
    
    #
    #
    #
    
    save = op.join(workdir, "pipeline.json")
    if op.isfile(save):
        c.info("Loading saved configuration")
    else:
        #
        # anatomical/structural data
        #
        
        description = "anatomical/structural data"
        
        response0 = c.select("Is %s available?" % description, ["Yes", "No"])
        
        field_names = ["T1w", "T2w", "FLAIR"]
        field_descriptions = ["T1-weighted image", "T2-weighted image", "FLAIR image"]
        while response0 == "Yes":
            response1 = c.select("Choose data type to specify", field_names)
            
            if response1 is None:
                break
                
            i = field_names.index(response1)
            
            field_name = field_names[i]
            field_description = field_descriptions[i]
            
            images[field_name] = get_files(field_description)
            
            if len(images[field_name]) > 0:
                del field_names[i]
                del field_descriptions[i]
                
            if len(field_names) == 0:
                break
            
            response0 = c.select("Is further %s available?" % description, ["Yes", "No"])
            
        c.info("")
        
        #
        # functional/task data
        #
        
        description = "functional/task data"
        field_names = ["FACES", "MID", "NBACK", "Other"]
        field_descriptions = ["faces task image", "monetary incentive delay task image", "n-back task image", "task image"]
        
        c.info("Please specify %s" % description)
        response0 = "Yes"
        
        while response0 == "Yes":
            response1 = c.select("Choose task to specify", field_names)
            
            if response1 is None:
                break
                
            i = field_names.index(response1)
            
            field_name = field_names[i]
            field_description = field_descriptions[i]
            
            if field_name not in KNOWN_TASKS:
                field_name = c.read("Specify the name of the task")
            
            metadata[field_name] = dict()
            images[field_name] = get_files(field_description, runs = True)
            
            image = next(iter(next(iter(images[field_name].values())).values()))
            metadata[field_name]["RepetitionTime"] = float(c.read("Specify the repetition time", o = \
                str(nib.load(image).header.get_zooms()[3])))
            
            description2 = "condition/explanatory variable"
            response2 = c.select("Specify the format of the %s files" % description2, ["FSL 3-column", "SPM multiple conditions"])
            
            conditions = None
            if response2 == "SPM multiple conditions":
                conditions = get_files(description2, runs = True)
            elif response2 == "FSL 3-column":
                conditions = get_files(description2, runs = True, conditions = True)
            
            conditions = parse_condition_files(conditions, format = response2)
            condition = next(iter(next(iter(conditions.values())).values()))
            
            contrast = None
            if field_name in KNOWN_TASKS:
                known_conditions = KNOWN_TASKS[field_name]
                contrast = dict()
                for i, known_condition in enumerate(known_conditions):
                    match = c.select("Select the specified %s that refers to the %s condition" % (description2, known_condition), list(condition))
                    contrast[match] = CONTRASTS[field_name][i]
            else:
                c.error("Not implemented")
            
            metadata[field_name]["conditions"] = conditions
            metadata[field_name]["contrast"] = contrast
            
            # response3 = c.select("Is field map data available?", ["Yes", "No"])
            # 
            # if response3 == "Yes":
            #     response4 = c.select("Specify the format of field map data", ["Yes", "No"])
                        
            if len(images[field_name]) > 0:
                del field_names[i]
                del field_descriptions[i]
                
            if len(field_names) == 0:
                break
            
            response0 = c.select("Is further %s available?" % description, ["Yes", "No"])
        
        c.info("")
        
        with open(save, "w+") as f:
            json.dump({"images": images, "metadata": metadata}, f)
            
        c.info("Saved configuration")
        
        c.info("")
    
    init_workflow(workdir)
    
    c.info("")

"""

hmc_fsl True
no_sub True


c.readSidecarJSON --> Fake


"""