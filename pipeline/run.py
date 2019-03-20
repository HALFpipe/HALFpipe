from multiprocessing import set_start_method, cpu_count

set_start_method("forkserver", force=True)

import os
import pandas as pd
import nibabel as nib
import json
import shutil
from glob import glob
from argparse import ArgumentParser
from .cli import Cli
from .conditions import parse_condition_files
from .info import __version__
from .workflow import init_workflow
from .logging import init_logging
from .patterns import ambiguous_match
from .utils import get_path, transpose

# Debug config for stop on first crash
# from nipype import config
# cfg = dict(execution={'stop_on_first_crash': True})
# config.update_config(cfg)

EXT_PATH = "/ext"


def main():
    ap = ArgumentParser(description="")
    ap.add_argument("-w", "--workdir")
    ap.add_argument("-p", "--nipype-plugin")
    ap.add_argument("-s", "--setup-only", action="store_true", default=False)
    ap.add_argument("-j", "--jsonfile")
    args = ap.parse_args()

    workdir = None
    if args.workdir is not None:
        workdir = get_path(args.workdir, EXT_PATH)

    #
    # tests
    #

    c = None

    if not (os.path.isdir(EXT_PATH) and len(os.listdir(EXT_PATH)) > 0):
        c.error("Can not access host files at path %s. Did you forget the docker argument \"--mount ...\"?" % EXT_PATH)

    #
    # data structures
    #

    images = dict()
    metadata = dict()
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

    json_dir = os.path.join(workdir, 'json_files')
    path_to_pipeline_json = None
    if args.jsonfile is not None:
        path_to_pipeline_json = os.path.join(json_dir, args.jsonfile)
    else:
        path_to_pipeline_json = os.path.join(workdir, "pipeline.json")

    #
    # helper functions
    #

    def get_file(description):
        path = get_path(c.read("Specify the path of the %s file" % description), EXT_PATH)
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

        wildcard_descriptions = {"*": "subject name", "$": "condition name", "?": "run name"}

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
                                response0 = c.select(
                                    "Does %s contain %s?" % (wildcard_descriptions_[k], " and ".join(y)), ["Yes", "No"])
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

        if response0 == "Yes":
            field_name = c.read("Specify the paradigm name", "rest")

            metadata[field_name] = dict()
            images[field_name] = get_files(field_description, runs=True)

            image = next(iter(next(iter(images[field_name].values())).values()))[""]
            metadata[field_name]["RepetitionTime"] = float(c.read("Specify the repetition time",
                                                                  o=str(nib.load(image).header.get_zooms()[3])))

            ped = c.select("Specify the phase encoding direction",
                           ["AP", "PA", "LR", "RL", "SI", "IS"])
            metadata[field_name]["PhaseEncodingDirection"] = \
                {"AP": "j", "PA": "j", "LR": "i", "RL": "i", "IS": "k", "SI": "k"}[ped]

            response3 = c.select("Calculate connectivity matrix from brain atlas?", ["Yes", "No"])
            if response3 == "Yes":
                metadata[field_name]["BrainAtlasImage"] = {}
                while response3 == "Yes":
                    name = c.read("Specify Atlas name")
                    metadata[field_name]["BrainAtlasImage"][name] = get_file("brain atlas image")
                    response3 = c.select("Add another Atlas?", ["Yes", "No"])

            response3 = c.select("Calculate seed connectivity?", ["Yes", "No"])
            if response3 == "Yes":
                metadata[field_name]["ConnectivitySeeds"] = {}
                while response3 == "Yes":
                    name = c.read("Specify seed name")
                    metadata[field_name]["ConnectivitySeeds"][name] = get_file("seed mask image")
                    response3 = c.select("Add another seed?", ["Yes", "No"])

            response3 = c.select("Calculate ICA component maps via dual regression?", ["Yes", "No"])
            if response3 == "Yes":
                metadata[field_name]["ICAMaps"] = get_file("ICA component maps image")

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
            images[field_name] = get_files(field_description, runs=True)

            image = next(iter(next(iter(images[field_name].values())).values()))[""]
            # metadata[field_name]["RepetitionTime"] = float(c.read("Specify the repetition time",
            #     o = str(nib.load(image).header.get_zooms()[3])))

            metadata[field_name]["RepetitionTime"] = float(str(nib.load(image).header.get_zooms()[3]))

            ped = c.select("Specify the phase encoding direction",
                           ["AP", "PA", "LR", "RL", "SI", "IS"])
            metadata[field_name]["PhaseEncodingDirection"] = \
                {"AP": "j", "PA": "j", "LR": "i", "RL": "i", "IS": "k", "SI": "k"}[ped]

            description2 = "condition/explanatory variable"
            response2 = c.select("Specify the format of the %s files" % description2,
                                 ["FSL 3-column", "SPM multiple conditions"])

            conditions = None
            if response2 == "SPM multiple conditions":
                conditions = get_files(description2, runs=True)
            elif response2 == "FSL 3-column":
                conditions = get_files(description2, runs=True, conditions=True)

            conditions = parse_condition_files(conditions, form=response2)

            condition = list(next(iter(next(iter(conditions.values())).values())))
            condition = sorted(condition)

            c.info("Specify contrasts")

            contrasts = dict()

            response3 = "Yes"
            while response3 == "Yes":
                contrast_name = c.read("Specify the contrast name")
                contrast_values = c.fields("Specify the contrast values", condition)

                contrasts[contrast_name] = {k: float(v) for k, v in zip(condition, contrast_values)}

                response3 = c.select("Add another contrast?", ["Yes", "No"])

            metadata[field_name]["Conditions"] = conditions
            metadata[field_name]["Contrasts"] = contrasts

            response3 = c.select("Add motion parameters (6 dof) to model?", ["Yes", "No"])
            metadata[field_name]["UseMovPar"] = response3 == "Yes"
            #
            # if response3 == "Yes":
            #     response4 = c.select("Specify the format of field map data", ["Yes", "No"])

            response0 = c.select("Is further %s available?" % description, ["Yes", "No"])

        c.info("")

        metadata["TemporalFilter"] = float(c.read("Specify the temporal filter width in seconds",
                                                  o=str(125.0)))
        metadata["SmoothingFWHM"] = float(c.read("Specify the smoothing FWHM in mm",
                                                 o=str(5.0)))

        c.info("")

        '''
        spreadsheet_file = get_file("covariates/group data spreadsheet")
        spreadsheet = pd.read_csv(spreadsheet_file)

        id_column = c.select("Specify the column containing subject names", spreadsheet.columns)

        covariates = spreadsheet.set_index(id_column).to_dict()

        response0 = c.select("Specify a group design?", ["Yes", "No"])
        if response0 == "Yes":
            group_column = c.select("Specify the column containing group names", spreadsheet.columns)
            groups = covariates[group_column]
            del covariates[group_column]

            unique_groups = set(groups.values())

            group_contrasts = {}
            response3 = "Yes"
            while response3 == "Yes":
                contrast_name = c.read("Specify the contrast name")
                contrast_values = c.fields("Specify the contrast values", unique_groups)
                group_contrasts[contrast_name] = {k: float(v) for k, v in zip(unique_groups, contrast_values)}
                response3 = c.select("Add another contrast?", ["Yes", "No"])

            metadata["SubjectGroups"] = groups
            metadata["GroupContrasts"] = group_contrasts

        metadata["Covariates"] = covariates

        c.info("")
        '''

        with open(path_to_pipeline_json, "w+") as f:
            json.dump({"images": images, "metadata": metadata}, f, indent=4)

        c.info("Saved configuration")

        c.info("")
        c.info("")

    if not args.setup_only:
        workflow = init_workflow(workdir, path_to_pipeline_json)

        init_logging(workdir, path_to_pipeline_json)

        if args.nipype_plugin is None:
            plugin_settings = {
                "plugin": "MultiProc",
                "plugin_args": {
                    "n_procs": cpu_count(),
                    "raise_insufficient": False,
                    "maxtasksperchild": 1,
                }
            }
        else:
            plugin_settings = {
                "plugin": args.nipype_plugin
            }

        import gc
        gc.collect()

        workflow.run(**plugin_settings)

        # copy confounds.tsv from task to intermediates/subject
        # access pipeline.json to get subjects and tasks for path
        with open(path_to_pipeline_json, "r") as f:
            metadata = json.load(f)

        flattened_metadata = transpose(metadata['images'])

        for subject in flattened_metadata:
            # Check if there is taskdata in metadata as otherwise there is no confounds.tsv
            for key in flattened_metadata[subject]:
                if key not in ["T1w", "T2w", "FLAIR"]:
                    # Taskdata exists
                    task = key
                    # use glob for wildcard as path has truncated subject_id in fmriprep
                    try:
                        source = glob(workdir + '/nipype/sub_' + subject + '/task_' + task + '/func_preproc*' +
                                      '/bold_confounds_wf/concat/confounds.tsv')[0]
                        destination = workdir + '/intermediates/' + subject + '/' + task + '/confounds.tsv'
                        shutil.copyfile(src=source, dst=destination)
                    except IndexError:
                        print(
                            'Warning: confounds.tsv was not found, check intermediate files in nipype/<subject_id>/...')
                else:
                    # Taskdata doesn't exist
                    pass
        # calculate correlation matrix from atlas matrix
        # save correlation matrix as csv
        for subject in flattened_metadata:
            for key in flattened_metadata[subject]:
                if key not in ["T1w", "T2w", "FLAIR"]:
                    task = key
                    try:
                        for idx, atlas_idx in enumerate(
                                ["%04d" % x for x in range(len(metadata['metadata'][task]['BrainAtlasImage']))]):
                            if len(metadata['metadata'][task]['BrainAtlasImage']) >= 2:
                                try:
                                    source = workdir + '/intermediates/' + subject + '/' + task + \
                                             '/brainatlas_matrix' + str(atlas_idx) + '.txt'
                                    destination = workdir + '/intermediates/' + subject + '/' + task + \
                                                  '/corr_matrix_' + \
                                                  list(metadata['metadata'][task]['BrainAtlasImage'].keys())[0] + '.csv'
                                    atlas_matrix = pd.read_csv(source, sep=" ", header=None, skipinitialspace=True)
                                    # drop last column as there is only NaN in there due to delimiting issues
                                    atlas_matrix.drop(atlas_matrix.columns[len(atlas_matrix.columns) - 1], axis=1,
                                                      inplace=True)
                                    corr_matrix = atlas_matrix.corr(method='pearson')
                                    corr_matrix.to_csv(destination, index=False, header=False)
                                    shutil.move(source,
                                                workdir + '/intermediates/' + subject + '/' + task +
                                                '/brainatlas_timeseries_' +
                                                list(metadata['metadata'][task]['BrainAtlasImage'].keys())[0] + '.txt')
                                except OSError as e:
                                    print(
                                        'Warning: atlas_matrix was not found. Correlation matrix could not be computed')
                                    print(e)
                            else:
                                try:
                                    source = workdir + '/intermediates/' + subject + '/' + task + \
                                             '/brainatlas_matrix.txt'
                                    destination = workdir + '/intermediates/' + subject + '/' + task + \
                                                  '/corr_matrix_' + \
                                                  list(metadata['metadata'][task]['BrainAtlasImage'].keys())[0] + '.csv'
                                    atlas_matrix = pd.read_csv(source, sep=" ", header=None, skipinitialspace=True)
                                    # drop last column as there is only NaN in there due to delimiting issues
                                    atlas_matrix.drop(atlas_matrix.columns[len(atlas_matrix.columns) - 1], axis=1,
                                                      inplace=True)
                                    corr_matrix = atlas_matrix.corr(method='pearson')
                                    corr_matrix.to_csv(destination, index=False, header=False)
                                    shutil.move(source,
                                                workdir + '/intermediates/' + subject + '/' + task +
                                                '/brainatlas_timeseries_' +
                                                list(metadata['metadata'][task]['BrainAtlasImage'].keys())[0] + '.txt')
                                except OSError as e:
                                    print(
                                        'Warning: atlas_matrix was not found. Correlation matrix could not be computed')
                                    print(e)

                    except KeyError:
                        pass
    else:
        os.makedirs(json_dir, exist_ok=True)

        with open(path_to_pipeline_json, "r") as f:
            metadata = json.load(f)

        flattened_metadata = transpose(metadata['images'])

        # Selecting metadata to be shared among subjects
        # To remove if group metadata is not initially included
        subject_metadata = dict()
        subject_keys = ["rest", "TemporalFilter", "SmoothingFWHM"]
        for key in subject_keys:
            subject_metadata[key] = metadata['metadata'][key]

        file = open(os.path.join(workdir, "execute.txt"), "w")
        command = "docker run -it -v /:/ext mindandbrain/pipeline --workdir=" + workdir + " --jsonfile="

        # Selecting images info per subject and saving respective json file
        for subject in flattened_metadata:
            file_name = subject + '_pipeline.json'
            path_to_new_pipeline_json = os.path.join(json_dir, file_name)
            subject_images = dict()
            # key is called field_name in run.py (could change name)
            for key in flattened_metadata[subject]:
                key_dict = dict()
                key_dict[subject] = metadata['images'][key][subject]
                subject_images[key] = key_dict
            with open(path_to_new_pipeline_json, "w+") as f:
                json.dump({"images": subject_images, "metadata": subject_metadata}, f, indent=4)

            file.write(command + file_name + '\n')

        file.close()
