#!/usr/bin/env python
# -*- coding: utf-8 -*-

def main():
    from multiprocessing import set_start_method, cpu_count
    set_start_method("forkserver", force = True)
    
    from glob import glob
    from os import path as op
    import os

    from argparse import ArgumentParser

    import nibabel as nib

    import re
    import json

    from .cli import cli

    from .conditions import parse_condition_files

    from .info import __version__

    from .workflow import init_workflow

    from .logging import init_logging
    
    from .patterns import ambiguous_match

    EXT_PATH = "/ext"
    
    c = cli()
    
    c.info("mindandbrain pipeline %s" % __version__)
    c.info("")
    
    #
    # tests
    #
    
    if not (op.isdir(EXT_PATH) and len(os.listdir(EXT_PATH)) > 0):
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
    
    subject_ids = []
    
    #
    # working dir
    #
    
    workdir = get_path(c.read("Specify the working directory"))
    
    os.makedirs(workdir, exist_ok = True)
    
    c.info("")
    
    #
    # helper functions
    #
    
    def get_file(description):
        path = get_path(c.read("Specify the path to the %s file" % description))
        if not op.isfile(path):
            return get_file(description)
        return path
        
    def get_files(description, runs = False, conditions = False):
        files = dict()
        
        c.info("Specify the path to the %s files" % description)
        
        wildcards = []
        
        if runs:
            c.info("Put \"?\" in place of run names")
            wildcards += ["?"]
        
        if conditions:
            c.info("Put \"$\" in place of condition names")
            wildcards += ["$"]
        
        path = get_path(c.read("Put \"*\" in place of the subject names"))
        wildcards += ["*"]
        
        wildcard_descriptions = {"*": "subject name", "$": "condition name", "?": "run name"}
        
        glob_path = path.replace("?", "*")
        glob_path = glob_path.replace("$", "*")
        glob_result = glob(glob_path)
        
        c.info("Found %i %s files" % (len(glob_result), description))
        
        contains = {}
        
        for g in glob_result:
            m = ambiguous_match(g, path, wildcards)
            
            if len(m) > 1:
                m_ = []
                
                possibilities = {}
                
                wildcard_descriptions_ = {k: v for k, v in wildcard_descriptions.items() if k in wildcards}
                
                is_good = set()
                for k, v in wildcard_descriptions_.items():
                    field = k + "_contains"
                    for i, w in enumerate(m):
                        if w[field] is not None:
                            if w["*"] in subject_ids:
                                is_good.add(i)
                if len(is_good) == 1:
                    w = m[next(iter(is_good))]
                    for k, v in wildcard_descriptions_.items():
                        field = k + "_contains"
                        contains[field] = w[field]
                
                messagedisplayed = False
                for k, v in wildcard_descriptions_.items():
                    field = k + "_contains"
                    if field not in contains:
                        for w in m:
                            if w[field] is not None:
                                if not messagedisplayed:
                                    c.info("Detected ambiguous filenames!")
                                    messagedisplayed = True
                                y = ["\"" + x + "\"" for x in w[field]]
                                response0 = c.select("Does %s contain %s?" % (wildcard_descriptions_[k], " and ".join(y)), ["Yes", "No"])
                                if response0 == "Yes":
                                    contains[field] = n[field]
                                    break
                    if field not in contains:
                        contains[field] = None
                
                # import pdb; pdb.set_trace()
            
                for n in m:
                    is_good = True
                    for k, v in wildcard_descriptions_.items():
                        field = k + "_contains"
                        if field in contains and field in n:
                            if n[field] != contains[field]:
                                is_good = False
                    if is_good:
                        m_ += [n]
                m = m_
            
            m = m[0]
            
            subject = ""
            if "*" in m:
                subject = m["*"]
            
            run = ""
            if "?" in m:
                run = m["?"]
            
            condition = ""
            if "$" in m:
                condition = m["$"]
                     
            # import pdb; pdb.set_trace()
            
            if subject not in files:
                files[subject] = dict()
            if run not in files[subject]:
                files[subject][run] = dict()
                
            files[subject][run][condition] = g
                
        if len(files) == 0:
            response = c.select("Try again?", ["Yes", "No"])
            
            if response == "Yes":
                return get_files(description)
            
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
        
        # response0 = c.select("Is %s available?" % description, ["Yes", "No"])
        
        c.info("Please specify %s" % description)
        response0 = "Yes"
        
        field_names = ["T1w"]
        field_descriptions = ["T1-weighted image"]
        
        while response0 == "Yes":
            # response1 = c.select("Choose data type to specify", field_names)
            # 
            # if response1 is None:
            #     break
            # 
            # i = field_names.index(response1)
            i = 0
        
            field_name = field_names[i]
            field_description = field_descriptions[i]
        
            images[field_name] = get_files(field_description)
            
            subject_ids = list(images[field_name].keys())
        
            if len(images[field_name]) > 0:
                del field_names[i]
                del field_descriptions[i]
        
            if len(field_names) == 0:
                break
        
            # response0 = c.select("Is further %s available?" % description, ["Yes", "No"])
        
        c.info("")
        
        #
        # functional/rest data
        #
        
        description = "resting state data"
        field_description = "resting state image"
        
        response0 = c.select("Is %s available?" % description, ["Yes", "No"])
        # c.info("Please specify %s" % description)
        # response0 = "Yes"
        
        if response0 == "Yes":
            field_name = c.read("Specify the paradigm name", "rest")
            
            metadata[field_name] = dict()
            images[field_name] = get_files(field_description, runs = True)
            
            image = next(iter(next(iter(images[field_name].values())).values()))[""]
            # metadata[field_name]["RepetitionTime"] = float(c.read("Specify the repetition time", 
            #     o = str(nib.load(image).header.get_zooms()[3])))
            
            metadata[field_name]["RepetitionTime"] = float(str(nib.load(image).header.get_zooms()[3]))
            
            ped = c.select("Specify the phase encoding direction", \
                ["AP", "PA", "LR", "RL", "SI", "IS"])
            metadata[field_name]["PhaseEncodingDirection"] = \
                {"AP": "j", "PA": "j", "LR": "i", "RL": "i", "IS": "k", "SI": "k"}[ped]
            
            response3 = c.select("Calculate connectivity matrix from brain atlas?", ["Yes", "No"])
            if response3 == "Yes":
                metadata[field_name]["BrainAtlasImage"] = get_file("brain atlas image")
            
            response3 = c.select("Calculate seed connectivity?", ["Yes", "No"])
            if response3 == "Yes":
                metadata[field_name]["ConnectivitySeeds"] = {}
                while response3 == "Yes":
                    name = c.read("Specify seed name")
                    metadata[field_name]["ConnectivitySeeds"][name] = get_file("seed mask image")
                    response3 = c.select("Add another seed?", ["Yes", "No"])
                
            response3 = c.select("Calculate ICA component maps via dual regression?", ["Yes", "No"])
            if response3 == "Yes":
                metadata[field_name]["ICAMaps"] = get_file("seed")
            
            # response3 = c.select("Is field map data available?", ["Yes", "No"])
            # 
            # if response3 == "Yes":
            #     response4 = c.select("Specify the format of field map data", ["Yes", "No"])
            
            # response0 = c.select("Is further %s available?" % description, ["Yes", "No"])
        
        c.info("")
        
        #
        # functional/task data
        #
        
        description = "task data"
        field_description = "task image"
        
        response0 = c.select("Is %s available?" % description, ["Yes", "No"])
        # c.info("Please specify %s" % description)
        # response0 = "Yes"
        
        while response0 == "Yes":
            field_name = c.read("Specify the paradigm name")
            
            metadata[field_name] = dict()
            images[field_name] = get_files(field_description, runs = True)
            
            image = next(iter(next(iter(images[field_name].values())).values()))[""]
            # metadata[field_name]["RepetitionTime"] = float(c.read("Specify the repetition time", 
            #     o = str(nib.load(image).header.get_zooms()[3])))
            
            metadata[field_name]["RepetitionTime"] = float(str(nib.load(image).header.get_zooms()[3]))
            
            ped = c.select("Specify the phase encoding direction", \
                ["AP", "PA", "LR", "RL", "SI", "IS"])
            metadata[field_name]["PhaseEncodingDirection"] = \
                {"AP": "j", "PA": "j", "LR": "i", "RL": "i", "IS": "k", "SI": "k"}[ped]
            
            description2 = "condition/explanatory variable"
            response2 = c.select("Specify the format of the %s files" % description2, \
                ["FSL 3-column", "SPM multiple conditions"])
            
            conditions = None
            if response2 == "SPM multiple conditions":
                conditions = get_files(description2, runs = True)
            elif response2 == "FSL 3-column":
                conditions = get_files(description2, runs = True, conditions = True)
            
            conditions = parse_condition_files(conditions, format = response2)
            condition = list(next(iter(next(iter(conditions.values())).values())))

            c.info("Specify contrasts")
            
            contrasts = dict()
            
            response3 = "Yes"
            while response3 == "Yes":
                contrast_name = c.read("Specify the contrast name")
                contrast_values = c.fields("Specify the contrast values", condition)
                
                contrasts[contrast_name] = {k:float(v) for k, v in zip(condition, contrast_values)}
                
                response3 = c.select("Add another contrast?", ["Yes", "No"])
            
            metadata[field_name]["Conditions"] = conditions
            metadata[field_name]["Contrasts"] = contrasts
            
            # response3 = c.select("Is field map data available?", ["Yes", "No"])
            # 
            # if response3 == "Yes":
            #     response4 = c.select("Specify the format of field map data", ["Yes", "No"])
            
            response0 = c.select("Is further %s available?" % description, ["Yes", "No"])
        
        c.info("")
        
        metadata["TemporalFilter"] = float(c.read("Specify the temporal filter width in seconds", 
            o = str(125.0)))
        metadata["SmoothingFWHM"] = float(c.read("Specify the smoothing FWHM in mm", 
            o = str(5.0)))
        
        c.info("")
        
        with open(save, "w+") as f:
            json.dump({"images": images, "metadata": metadata}, f, indent = 4)
            
        c.info("Saved configuration")
        
        c.info("")
    
    c.info("")
    
    workflow = init_workflow(workdir)
    
    plugin_settings = {}
    init_logging(workdir)
    
    plugin_settings = {
        "plugin": "MultiProc",
        "plugin_args": {
            "n_procs": cpu_count(),
            "raise_insufficient": False,
            "maxtasksperchild": 1,
        }
    }
    
    import gc
    gc.collect()
    
    workflow.run(**plugin_settings)
    
