# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os

from .info import __version__

from multiprocessing import set_start_method, cpu_count
set_start_method("forkserver", force=True)

EXT_PATH = "/ext"


def main():
    from argparse import ArgumentParser
    from .utils import get_path, transpose, firstval

    from .cli import Cli

    from .conditions import parse_condition_files
    from .patterns import ambiguous_match

    ap = ArgumentParser(description="")
    ap.add_argument("-w", "--workdir")
    ap.add_argument("-p", "--nipype-plugin")
    ap.add_argument("-s", "--setup-only", action="store_true", default=False)
    ap.add_argument("-j", "--json-file")
    ap.add_argument("-b", "--block-size")
    ap.add_argument("-f", "--file-status", action="store_true")
    ap.add_argument("-o", "--only-stats", action="store_true")
    ap.add_argument("-d", "--debug-nipype", action="store_true")
    args = ap.parse_args()

    workdir = None
    if args.workdir is not None:
        workdir = get_path(args.workdir, EXT_PATH)

    #
    # tests
    #

    c = None

    if not (os.path.isdir(EXT_PATH) and len(os.listdir(EXT_PATH)) > 0):
        # FIXME update to singularity syntax
        c.error("Can not access host files at path %s." % EXT_PATH +
                "Did you forget the docker argument \"--mount ...\"?")

    #
    # data structures
    #

    images = dict()
    configuration = dict()
    # field_maps = dict()

    subject_ids = []

    if workdir is None:
        if c is None:
            c = Cli()
            c.info("mindandbrain pipeline %s" % __version__)
            c.info("")

        workdir = get_path(c.read("Specify the working directory"), EXT_PATH)
        c.info("")

    os.makedirs(workdir, exist_ok=True)

    json_dir = os.path.join(workdir, "json_files")
    path_to_pipeline_json = None
    if args.json_file is not None:
        path_to_pipeline_json = os.path.join(json_dir, args.json_file)
    else:
        path_to_pipeline_json = os.path.join(workdir, "pipeline.json")

    #
    # helper functions
    #

    from glob import glob

    def get_file(description):
        path = get_path(
            c.read("Specify the path of the %s file" % description),
            EXT_PATH
        )
        if not os.path.isfile(path):  # does file exist
            return get_file(description)  # repeat if doesn"t exist
        return path

    def get_files(description, runs=False, conditions=False):
        """ Match files by wildcards """
        files = dict()

        c.info("Specify the path of the %s files" % description)

        wildcards = []

        if runs:
            c.info("Put \"?\" in place of run names")
            wildcards += ["?"]

        if conditions:
            c.info("Put \"$\" in place of condition names")
            wildcards += ["$"]

        c.info("Put \"*\" in place of the subject names")

        if description == "T1-weighted image":
            c.info("(e.g: /path/to/your/data/*_t1.nii.gz)")

        path = get_path(c.read(q=None), EXT_PATH)

        wildcards += ["*"]

        wildcard_descriptions = {
            "*": "subject name",
            "$": "condition name",
            "?": "run name"
        }

        glob_path = path
        if runs:
            glob_path = glob_path.replace("?", "*")
        if conditions:
            glob_path = glob_path.replace("$", "*")

        glob_result = glob(glob_path)

        glob_result = [g for g in glob_result if os.path.isfile(g)]

        c.info("Found %i %s files" % (len(glob_result), description))

        contains = {}

        for g in glob_result:
            m = ambiguous_match(g, path, wildcards)

            if len(m) > 1:
                m_ = []

                wildcard_descriptions_ = {
                    k: v
                    for k, v in wildcard_descriptions.items()
                    if k in wildcards
                }

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
                                response0 = c.select(
                                    "Does {} contain {}?".format(
                                        wildcard_descriptions_[k],
                                        " and ".join(y)),
                                    ["Yes", "No"]
                                )
                                if response0 == "Yes":
                                    # contains[field] = n[field]
                                    break
                    if field not in contains:
                        contains[field] = None

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

            if subject not in files:
                files[subject] = dict()
            if run not in files[subject]:
                files[subject][run] = dict()

            files[subject][run][condition] = g

        if len(files) == 0:
            response = c.select("Try again?", ["Yes", "No"])

            if response == "Yes":
                return get_files(description, runs=runs, conditions=conditions)

        return files

    #
    # interface code that asks user questions
    #

    if not os.path.isfile(path_to_pipeline_json):
        if c is None:
            c = Cli()
            c.info("mindandbrain pipeline %s" % __version__)
            c.info("")
        # TODO remove after testing

        #
        # anatomical/structural data
        #

        description = "anatomical/structural data"
        c.info("Please specify %s" % description)

        field_name = "T1w"
        field_description = "T1-weighted image"

        images[field_name] = get_files(field_description)

        subject_ids = list(images[field_name].keys())

        c.info("")

        #
        # functional/rest data
        #

        description = "resting state data"
        field_description = "resting state image"

        response0 = c.select("Is %s available?" % description, ["Yes", "No"])
        # c.info("Please specify %s" % description)
        # response0 = "Yes"

        import nibabel as nib

        def get_scan(scanname):
            configuration[scanname] = dict()
            images[scanname] = get_files(field_description, runs=True)
            configuration[scanname]["RepetitionTime"] = dict()
            for subject in subject_ids:
                # reads the repetion time from the nii.gz file
                configuration[scanname]["RepetitionTime"][subject] = \
                    float(str(nib.load(
                        firstval(transpose(images[scanname]))[subject]
                        # gets the path of the nii.gz file for each subject
                    ).header.get_zooms()[3]))

            ped = c.select("Specify the phase encoding direction",
                           ["AP", "PA", "LR", "RL", "SI", "IS"])
            configuration[scanname]["PhaseEncodingDirection"] = {
                "AP": "j", "PA": "j",
                "LR": "i", "RL": "i",
                "IS": "k", "SI": "k"
            }[ped]

        def get_confounds(scanname):
            response3 = c.select("Add confound regressors to the model?",
                                 ["Yes", "No"])
            configuration[scanname]["UseMovPar"] = False
            configuration[scanname]["CSF"] = False
            configuration[scanname]["Whitematter"] = False
            configuration[scanname]["GlobalSignal"] = False
            if response3 == "Yes":
                response4 = c.select("Add motion parameters (6 dof) to model?",
                                     ["Yes", "No"])
                if response4 == "Yes":
                    configuration[scanname]["UseMovPar"] = True
                response4 = c.select("Add CSF signal to model?", ["Yes", "No"])
                if response4 == "Yes":
                    configuration[scanname]["CSF"] = True
                response4 = c.select("Add white matter signal to model?",
                                     ["Yes", "No"])
                if response4 == "Yes":
                    configuration[scanname]["Whitematter"] = True
                response4 = c.select("Add global signal to model?",
                                     ["Yes", "No"])
                if response4 == "Yes":
                    configuration[scanname]["GlobalSignal"] = True

        if response0 == "Yes":
            get_scan("rest")

            response3 = c.select("Calculate functional connectivity " +
                                 "based on a brain atlas?", ["Yes", "No"])
            if response3 == "Yes":
                configuration["rest"]["BrainAtlasImage"] = {}
                while response3 == "Yes":
                    name = c.read("Specify Atlas name")
                    configuration["rest"]["BrainAtlasImage"][name] = \
                        get_file("brain atlas image")
                    response3 = c.select("Add another Atlas?", ["Yes", "No"])

            response3 = c.select("Calculate seed connectivity?", ["Yes", "No"])
            if response3 == "Yes":
                configuration["rest"]["ConnectivitySeeds"] = {}
                while response3 == "Yes":
                    name = c.read("Specify seed name")
                    configuration["rest"]["ConnectivitySeeds"][name] = \
                        get_file("seed mask image")
                    response3 = c.select("Add another seed?", ["Yes", "No"])

            response3 = c.select("Calculate ICA network templates " +
                                 "via dual regression?", ["Yes", "No"])
            if response3 == "Yes":
                configuration["rest"]["ICAMaps"] = {}

                while response3 == "Yes":
                    name = c.read("Specify an ICA network templates name")
                    configuration["rest"]["ICAMaps"][name] = \
                        get_file("ICA network templates image")
                    response3 = c.select("Use another ICA networ" +
                                         "templates image?", ["Yes", "No"])

            response3 = c.select("Calculate ReHo?", ["Yes", "No"])
            configuration["rest"]["ReHo"] = False
            if response3 == "Yes":
                configuration["rest"]["ReHo"] = True

            response3 = c.select("Calculate ALFF?", ["Yes", "No"])
            configuration["rest"]["ALFF"] = False
            if response3 == "Yes":
                configuration["rest"]["ALFF"] = True

            get_confounds("rest")

        c.info("")

        #
        # functional/task data
        #

        description = "task data"
        field_description = "task image"

        response0 = c.select("Is %s available?" % description, ["Yes", "No"])

        while response0 == "Yes":
            field_name = c.read("Specify the paradigm name")

            get_scan(field_name)

            description2 = "condition/explanatory variable"
            response2 = c.select("Specify the format of the %s files"
                                 % description2,
                                 ["FSL 3-column", "SPM multiple conditions"])

            conditions = None
            if response2 == "SPM multiple conditions":
                conditions = get_files(description2, runs=True)
            elif response2 == "FSL 3-column":
                conditions = get_files(
                    description2, runs=True, conditions=True)

            conditions = parse_condition_files(conditions, form=response2)

            condition = list(firstval(firstval(conditions)))
            condition = sorted(condition)

            c.info("Specify contrasts")

            contrasts = dict()

            response3 = "Yes"
            while response3 == "Yes":
                contrast_name = c.read("Specify the contrast name")
                contrast_values = c.fields("Specify the contrast values",
                                           condition)

                # allow for empty fields
                for i in range(len(contrast_values)):
                    if contrast_values[i] == "":
                        contrast_values[i] = 0

                contrasts[contrast_name] = {
                    k: float(v)
                    for k, v in zip(condition, contrast_values)
                }

                response3 = c.select("Add another contrast?", ["Yes", "No"])

            configuration[field_name]["Conditions"] = conditions
            configuration[field_name]["Contrasts"] = contrasts

            get_confounds(field_name)

            response0 = c.select("Is further %s available?" % description,
                                 ["Yes", "No"])

        c.info("")

        configuration["TemporalFilter"] = float(c.read(
            "Specify the temporal filter width in seconds",
            o=str(125.0)
        ))
        configuration["SmoothingFWHM"] = float(c.read(
            "Specify the smoothing FWHM in mm",
            o=str(5.0)
        ))

        c.info("")

        response0 = c.select("Do you want to exclude subjects " +
                             "based on movement?", ["Yes", "No"])

        motion_cutoff = False
        if response0 == "Yes":
            motion_cutoff = {}
            motion_cutoff["MeanFDCutoff"] = float(c.read(
                "Specify the cutoff mean FramewiseDisplacement",
                o=str(0.5)
            ))
            # c.info("")
            motion_cutoff["ProportionFDGt0_5Cutoff"] = float(c.read(
                "Specify the cutoff proportion of " +
                "frames with (FramewiseDisplacement > 0.5)",
                o=str(0.1)
            ))
        configuration["MotionCutoff"] = motion_cutoff
        c.info("")

        #
        # group design
        #

        response0 = c.select("Specify a group-level design?", ["Yes", "No"])
        if response0 == "Yes":
            group_design = {}
            configuration["GroupDesign"] = group_design
            group_data = {}
            group_design["Data"] = group_data

            spreadsheet_name = "covariates/group data spreadsheet"
            spreadsheet_file = get_file(spreadsheet_name)

            import pandas as pd
            spreadsheet = pd.read_csv(spreadsheet_file)

            # replace not available values by numpy NaN
            import numpy as np
            spreadsheet.replace({
                "NaN": np.nan, "n/a": np.nan, "NA": np.nan
            }, inplace=True)

            columns = spreadsheet.columns.tolist()

            for invalid_column in ["Unnamed: 0"]:
                if invalid_column in columns:
                    columns.remove(invalid_column)

            id_column = c.select("Select the column containing subject names",
                                 columns)
            columns.remove(id_column)

            covariates = spreadsheet.set_index(id_column).to_dict()
            _covariates = spreadsheet.set_index(id_column).to_dict()

            continuous_columns = []
            discrete_columns = []

            response1 = c.select("Specify between-group comparison?",
                                 ["Yes", "No"])
            while response1 == "Yes":
                group_column = c.select("Select the column containing " +
                                        "group names", columns)

                groups = covariates[group_column]

                unique_groups = set(groups.values())
                unique_groups = [str(x) for x in unique_groups]

                # Removing group column from covariates
                del _covariates[group_column]

                group_contrasts = {}
                response3 = "Yes"
                while response3 == "Yes":
                    # for each contrast
                    contrast_name = c.read("Specify the contrast name")
                    contrast_values = c.fields("Specify the contrast values",
                                               unique_groups)
                    group_contrasts[contrast_name] = {
                        k: float(v)
                        for k, v in zip(unique_groups, contrast_values)
                    }
                    response3 = c.select("Add another contrast?",
                                         ["Yes", "No"])

                var = {
                    "SubjectGroups": groups,
                    "Contrasts": group_contrasts
                }
                group_data[group_column] = var
                discrete_columns.append(group_column)

                response1 = c.select("Add another between-group comparison?",
                                     ["Yes", "No"])

            response1 = c.select("Specify continuous covariate?",
                                 ["Yes", "No"])
            while response1 == "Yes":
                if _covariates:
                    k = c.select("Select the column containing " +
                                 "the covariate", list(_covariates))
                    var = {
                        "Covariate": covariates[k],
                        "Contrasts": True
                    }
                    group_data[k] = var
                    continuous_columns.append(k)

                    del _covariates[k]

                    response1 = c.select("Add another continuous " +
                                         "covariate?",
                                         ["Yes", "No"])
                else:
                    c.info("No covariates available in %s" % spreadsheet_name)

            if _covariates:
                c.info("Specify additional covariates of no interest")
                covariates_selected = c.choice(
                    "Any key toggles the selection",
                    [c for c in covariates if c not in discrete_columns]
                )
                for k in covariates_selected:
                    continuous_columns.append(k)
                    group_data[k] = {
                        "Covariate": covariates[k]
                    }

            response2 = c.select("Repeat analysis within sub-groups?",
                                 ["Yes", "No"])
            while response2 == "Yes":
                available = [
                    c for c in covariates
                    if c not in continuous_columns
                ]
                if len(available) == 0:
                    c.info("No further columns " +
                           "available in %s" % spreadsheet_name)
                    break
                subgroup_column = c.select(
                    "Select the column containing " +
                    "sub-group names",
                    available)
                if subgroup_column not in \
                        group_data:
                    group_data[subgroup_column] = {
                        "SubjectGroups": covariates[subgroup_column]
                    }
                if "RepeatWithinSubGroups" not in group_design:
                    group_design["RepeatWithinSubGroups"] = []
                group_design["RepeatWithinSubGroups"].append(
                    subgroup_column)
                del covariates[subgroup_column]
                response2 = c.select("Add another set of sub-groups?",
                                     ["Yes", "No"])
        c.info("")

        import json
        with open(path_to_pipeline_json, "w+") as f:
            json.dump(
                {"images": images, "metadata": configuration},
                f, indent=4)

        c.info("Saved configuration")

        c.info("")
        c.info("")

    # Manual file check: Check file status after first level statistics is done
    if args.file_status:
        from .file_checks import file_checks
        file_checks(workdir, json_dir, path_to_pipeline_json)

    # Run workflow if setup_only flag is not given
    elif not args.setup_only:
        if args.nipype_plugin is None:
            plugin_settings = {
                "plugin": "MultiProc",
                "plugin_args": {
                    "n_procs": cpu_count(),
                    "raise_insufficient": False
                }
            }
        elif args.nipype_plugin == "none":
            plugin_settings = dict()
        else:
            plugin_settings = {
                "plugin": args.nipype_plugin
            }

        from .logging import init_logging
        init_logging(workdir, path_to_pipeline_json)

        import gc
        gc.collect()

        if args.only_stats:
            return
            # workflow = \
            #     init_stat_only_workflow(workdir, path_to_pipeline_json)
            # workflow.run(**plugin_settings)

        if args.debug_nipype:
            # Debug config for stop on first crash
            from nipype import config
            cfg = dict(execution={"stop_on_first_crash": True})
            config.update_config(cfg)

        # import cProfile
        # pr = cProfile.Profile()
        # pr.enable()

        from .workflow import init_workflow
        workflow = init_workflow(workdir, path_to_pipeline_json)

        # pr.disable()
        # pr.print_stats(sort = "time")
        # pr.dump_stats("/ext/Volumes/leassd/init_workflow.txt")

        # pr = cProfile.Profile()
        # pr.enable()

        workflow.run(**plugin_settings)

        # pr.disable()
        # pr.print_stats(sort = "time")
        # pr.dump_stats("/ext/Volumes/leassd/run_workflow.txt")
