import os
import pandas as pd
import nibabel as nib
import json
from multiprocessing import set_start_method, cpu_count
from glob import glob
from argparse import ArgumentParser
from .cli import Cli
from .conditions import parse_condition_files
from .info import __version__
from .workflow import init_workflow
from .logging import init_logging
from .patterns import ambiguous_match
from .utils import get_path

EXT_PATH = "/ext"

set_start_method("forkserver", force=True)


def main():
    ap = ArgumentParser(description="")
    ap.add_argument("-w", "--workdir")
    ap.add_argument("-p", "--nipype-plugin")
    ap.add_argument("-s", "--setup-only", action="store_true", default=False)
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

        if description == "T1-weighted image":
            c.info("/home/marc/mindandbrain/data_marc/*_t1.nii.gz")

        path = get_path(c.read("Put \"*\" in place of the subject names"), EXT_PATH)
        print(description)

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

            """
            response3 = c.select("Calculate connectivity matrix from brain atlas?", ["Yes", "No"])
            if response3 == "Yes":
                metadata[field_name]["BrainAtlasImage"] = get_file("brain atlas image")
            """

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

        with open(path_to_pipeline_json, "w+") as f:
            json.dump({"images": images, "metadata": metadata}, f, indent=4)

        c.info("Saved configuration")

        c.info("")
        c.info("")

    if not args.setup_only:
        workflow = init_workflow(workdir)

        init_logging(workdir)

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
