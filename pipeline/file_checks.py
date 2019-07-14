import os
import glob
import json
from .utils import transpose


# File checks for when a pipeline.json file is partitioned into different block/single subject processing units #
def file_checks(workdir, json_dir, path_to_pipeline_json):

    # Always check files of first level statistics for the particular json file
    level_1_check(path_to_pipeline_json, workdir)

    # Summary report
    level_2_check(workdir, json_dir)


def level_1_check(path_to_pipeline_json, workdir):

    report_dir = 'reports'
    report_dir = os.path.join(workdir, report_dir)
    os.makedirs(report_dir, exist_ok=True)

    with open(path_to_pipeline_json, "r") as f:
        configuration = json.load(f)

    # Creating report file
    report_name = "report_"+os.path.splitext(os.path.basename(path_to_pipeline_json))[0]+".txt"
    path_to_report = os.path.join(report_dir, report_name)
    report = open(path_to_report, "w+")

    # Getting subject names
    flattened_configuration = transpose(configuration['images'])
    subject_names = list(flattened_configuration)

    report.write("Subjects: " + str(subject_names) + '\n\n')

    # Getting names of paradigms (rest, task, etc) using keys in image section
    paradigm_names_all = list(configuration['images'])
    paradigm_names = paradigm_names_all.copy()
    paradigm_names.remove('T1w')

    report.write("Paradigms: " + str(paradigm_names) + '\n\n')

    list_all = ['preproc.nii.gz', 'confounds_mni.tsv', 'confounds.tsv', 'dof', 'csf_wm_meants.txt', 'gs_meants.txt']

    done = True

    subject_summary = []
    for subject in subject_names:
        subject_done = True

        for paradigm in paradigm_names:
            # Continue if an image was given for a particular subject/paradigm combination
            if subject in configuration['images'][paradigm]:

                my_list = list_all.copy()

                directory = os.path.join(workdir, 'intermediates', subject, paradigm)
                report.write(directory + '\n')

                # Rest paradigm
                suffixes = ['_cope.nii.gz', '_varcope.nii.gz', '_zstat.nii.gz']
                if paradigm == 'rest':

                    field = 'BrainAtlasImage'
                    if field in configuration['metadata'][paradigm]:
                        #print('entered '+field)
                        for key in configuration['metadata'][paradigm][field]:
                            file = 'brainatlas_timeseries_'+key+'.txt'
                            my_list.append(file)
                            file = 'corr_matrix_' + key + '.csv'
                            my_list.append(file)

                    field = 'ConnectivitySeeds'
                    if field in configuration['metadata'][paradigm]:
                        #print('entered '+field)
                        for key in configuration['metadata'][paradigm][field]:
                            for suffix in suffixes:
                                file = key+suffix
                                my_list.append(file)

                    field = 'ICAMaps'
                    if field in configuration['metadata'][paradigm]:
                        #print('entered '+field)
                        name = configuration['metadata'][paradigm][field]
                        name = os.path.splitext(os.path.basename(name))[0]
                        name = os.path.splitext(name)[0]
                        command = "fslnvols " + configuration['metadata'][paradigm][field]
                        #print(configuration['metadata'][paradigm][field])
                        seeds = os.popen(command).read()
                        seeds = int(seeds.rstrip())
                        #print(seeds)
                        #print(range(seeds))

                        for seed in range(seeds):
                            for suffix in suffixes:
                                file = name + '_' + str(seed) + suffix
                                my_list.append(file)

                    suffixes = ['_img.nii.gz', '_zstat.nii.gz']
                    fields = ['reho', 'alff']
                    for field in fields:
                        if field in configuration['metadata'][paradigm] and configuration['metadata'][paradigm][field]:
                            #print('entered '+field)
                            for suffix in suffixes:
                                file = field+suffix
                                my_list.append(file)

                # Paradigms different than rest (Tasks)
                else:

                    field = 'Contrasts'
                    if field in configuration['metadata'][paradigm]:
                        #print('entered '+field)
                        for key in configuration['metadata'][paradigm][field]:
                            for suffix in suffixes:
                                file = key + suffix
                                my_list.append(file)

                # #### REMOVE AFTER TESTING
                #my_list.append('/ext/Users/eliana/Documents/BERLIN-Work/output/')
                #my_list.append('/ext/Users/eliana/Documents/BERLIN-Work/output/pipeline*.json')

                # Writing report
                all_exist = []
                for i in my_list:
                    path = os.path.join(directory, i)
                    # Checking for file existence
                    exist = os.path.exists(path)
                    all_exist.append(exist)
                    report.write(str(exist) + '  ' + path + '\n')

                done_subject_paradigm = all(all_exist)
                subject_done = subject_done and done_subject_paradigm

                report.write(str(done_subject_paradigm) + '\n')
                report.write('\n')

        done = subject_done and done

        # Line per subject
        subject_summary.append(str(subject_done) + '  '+ subject + '\n')

    # Write summary per subject
    report.write('\nSummary per Subject\n')
    for line in subject_summary:
        report.write(line)

    # done is True if all files that should have been generated given the json file were generated
    report.write('\nSummary per json file\n')
    report.write(str(done) + ' ' + report_name)

    report.close()


def level_2_check(workdir, json_dir):

    report_dir = 'reports'
    report_dir = os.path.join(workdir, report_dir)
    reports = glob.glob(os.path.join(report_dir, 'report' + '*.txt'))

    summary_report = os.path.join(report_dir, 'report_summary.txt')
    if summary_report in reports:
        reports.remove(summary_report)

    my_list = []
    if reports:
        done = True

        # Check existing reports
        for report in reports:
            with open(report, 'r') as f:
                lines = f.read().splitlines()
                last_line = lines[-1]
                parts = last_line.split()
                if len(parts) == 2:
                    if parts[1] == os.path.basename(report):
                        my_list.append(last_line + "\n")
                        done = done and parts[0] == 'True'
                    else:
                        my_list.append('Check '+os.path.basename(report)+ "\n")
                else:
                    my_list.append('Check ' + os.path.basename(report)+ "\n")

        # Check if there are reports missing

        not_found = []
        if os.path.exists(json_dir):
            suffix = 'pipeline.json'
            json_files = glob.glob(os.path.join(json_dir,  '*'+suffix))
            for path_to_pipeline_json in json_files:
                #print(path_to_pipeline_json)
                report_name = "report_" + os.path.splitext(os.path.basename(path_to_pipeline_json))[0] + ".txt"
                path_to_report = os.path.join(report_dir, report_name)
                #print(path_to_report)
                #print(str(os.path.exists(path_to_report)))
                if not os.path.exists(path_to_report):
                    not_found.append(report_name + "\n")

            #print(json_files)

        with open(summary_report, 'w+') as f:
            f.write('REPORTS FOUND: \n\n')
            f.writelines(my_list)
            f.write('\n\n')

            f.write('REPORTS NOT FOUND: \n\n')
            if not_found:
                f.writelines(not_found)
                f.write('\n\n')
            else:
                f.write('All reports were found \n\n\n')

            if done and not not_found:
                f.write('DONE. Ready to run group statistics!')
            else:
                f.write('NOT DONE. Group statistics cannot start yet!')

    else:
        print('No reports available')
