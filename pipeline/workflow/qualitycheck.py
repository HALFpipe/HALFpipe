import os
import json
import pandas as pd


def get_qualitycheck_exclude(base_directory):
    """
    return dictionary of functional scans by subject to exclude from
    higher level analyses based on qualitycheck results

    :param base_directory: working directory where qcresult.json is located

    """

    # load qcresult.json
    qc_result = {}
    qc_result_fname = os.path.join(base_directory, "qualitycheck", "qcresult.json")
    if os.path.isfile(qc_result_fname):
        with open(qc_result_fname) as qc_result_file:
            qc_result = json.load(qc_result_file)

    # if there are issues with the functional preprocessing, then
    # exclude the specific scan
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

    # if there are issues with anatomical/structural preprocessing,
    # then exclude the entire subject
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

    # exclude entire subject based on movement parameters

    # load motion report
    motion_report_fname = os.path.join(base_directory, "qualitycheck", "motion_report.csv")
    if os.path.isfile(motion_report_fname):
        motion_report = pd.read_csv(motion_report_fname, index_col=0, sep='\t')

    # load pipeline.json
    pipeline_fname = os.path.join(base_directory, "pipeline.json")
    if os.path.isfile(pipeline_fname):
        with open(pipeline_fname) as pipeline_file:
            pipeline_json = json.load(pipeline_file)

    if os.path.isfile(motion_report_fname) and os.path.isfile(pipeline_fname):
        avg_framewise_displacement = pipeline_json['metadata']['AVGFramewiseDisplacement']
        movement_percentage = pipeline_json['metadata']['MovementPercentage']

        # get all rows of motion_report where Mean_FD threshold is broken
        mean_fd_excludes = motion_report[motion_report['Mean_FD'] > avg_framewise_displacement]
        # get all rows of motion_report where %volume_lg_0.5 is broken
        movement_percentage_excludes = motion_report[motion_report['%volume_lg_0.5'] > movement_percentage]

        for subject in mean_fd_excludes['Subject']:
            for k in exclude[subject].keys():
                exclude[subject][k] = True

        for subject in movement_percentage_excludes['Subject']:
            for k in exclude[subject].keys():
                exclude[subject][k] = True

    return exclude
