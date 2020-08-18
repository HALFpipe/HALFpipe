Welcome to ENIGMA `HALFpipe`!
===========================

[![https://www.singularity-hub.org/static/img/hosted-singularity--hub-%23e32929.svg](https://www.singularity-hub.org/static/img/hosted-singularity--hub-%23e32929.svg)](https://singularity-hub.org/collections/4508) [![https://img.shields.io/docker/cloud/build/mindandbrain/halfpipe](https://img.shields.io/docker/cloud/build/mindandbrain/halfpipe)](https://hub.docker.com/repository/docker/mindandbrain/halfpipe/tags)

`HALFpipe` is a user-friendly software that facilitates reproducible analysis of fMRI data, including preprocessing, single-subject, and group analysis. It provides state-of-the-art preprocessing using [`fmriprep`](https://fmriprep.readthedocs.io/), but removes the necessity to convert data to the [`BIDS`](https://bids-specification.readthedocs.io/en/stable/) format. Common resting-state and task-based fMRI features can the be calculated on the fly using [`FSL`](http://fsl.fmrib.ox.ac.uk/) and [`nipype`](https://nipype.readthedocs.io/) for statistics.

> **NOTE:** ENIGMA `HALFpipe` is pre-release software and not yet considered production-ready.
>
> If you would like to beta test and provide feedback, thank you! We recommend starting out with Beta 2, as this has many new features. If you have used Beta 1 before, please carefully read the [changes section](#8-changes). If you encounter issues, please see the [troubleshooting](#6-troubleshooting) section of this document. 
>  
> Beta 1 has proven to work in a variety of environments in the past weeks of beta testing and remains available for comparison.
>
> To use a specific version, please use the following command to download HALFpipe.
>
> | Version                   | Installation                                                                                             |
> |---------------------------|----------------------------------------------------------------------------------------------------------|
> | Beta 2 (August 16th 2020) | `singularity pull docker://mindandbrain/halfpipe:1.0.0b2`<br>`docker pull mindandbrain/halfpipe:1.0.0b2` |
> | Beta 1 (June 30th 2020)   | `singularity pull docker://mindandbrain/halfpipe:1.0.0b1`<br>`docker pull mindandbrain/halfpipe:1.0.0b1` |

## Table of Contents

> TODO

## 1. Getting started

`HALFpipe` is distributed as a container, meaning that all required software comes bundled in a monolithic file, the container. This allows for easy installation on new systems, and makes data analysis more reproducible, because software versions are guaranteed to be the same for all users.

### Container platform

The first step is to install one of the supported container platforms. If you're using a high-performance computing cluster, more often than not[`Singularity`](https://sylabs.io) will already be available.

If not, we recommend using the latest version of[`Singularity`](https://sylabs.io). However, it can be somewhat cumbersome to install, as it needs to be built from source.

The [`NeuroDebian`](https://neuro.debian.net/) package repository provides an older version of [`Singularity`](https://sylabs.io/guides/2.6/user-guide/) for [some](https://neuro.debian.net/pkgs/singularity-container.html) Linux distributions.

In contrast to `Singularity`, `Docker` always requires elevated privileges to run containers. In other words, every user running a `Docker` container automatically has administrator privileges on the computer they're using. Therefore, it is inherently a bad choice for multi-user environments, where the access of individual users should be limited. `Docker` is the only option that is compatible with `Mac OS X`.

| Container platform | Version   | Installation                                                     |
|--------------------|-----------|------------------------------------------------------------------|
| **Singularity**    | **3.5.3** | **See https://sylabs.io/guides/3.5/user-guide/quick_start.html** |
| Singularity        | 2.6.1     | `sudo apt install singularity-container`                         |
| Docker             |           | See https://docs.docker.com/engine/install/                      |

### Download

The second step is to download the `HALFpipe` to your computer. This requires approximately 5 gigabytes of storage.

| Container platform | Version | Installation                                      |
|--------------------|---------|---------------------------------------------------|
| Singularity        | 3.x     | `singularity pull shub://mindandbrain/halfpipe`   |
| Singularity        | 2.x     | `singularity pull docker://mindandbrain/halfpipe` |
| Docker             |         | `docker pull mindandbrain/halfpipe`               |

`Singularity` version `3.x` creates a container image file called `halfpipe_latest.sif` in the directory where you run the `pull` command. For `Singularity` version `2.x` the file is named `mindandbrain-halfpipe-master-latest.simg`. Whenever you want to use the container, you need pass `Singularity` the path to this file.

> **NOTE:** `Singularity` may store a copy of the container in its cache directory. The cache directory is located by default in your home directory at `~/.singularity`. If you need to save disk space in your home directory, you can safely delete the cache directory after downloading, i.e. by running `rm -rf ~/.singularity`. Alternatively, you could move the cache directory somewhere with more free disk space using a symlink. This way, files will automatically be stored there in the future. For example, if you have a lot of free disk space in `/mnt/storage`, then you could first run `mv ~/.singularity /mnt/storage` to move the cache directory, and then `ln -s /mnt/storage/.singularity ~/.singularity` to create the symlink.

`Docker` will store the container in its storage base directory, so it does not matter from which directory you run the `pull` command.

### Running

The third step is to run the downloaded container.

| Container platform | Command                                                                  |
|--------------------|--------------------------------------------------------------------------|
| Singularity        | `singularity run --no-home --cleanenv --bind /:/ext halfpipe_latest.sif` |
| Docker             | `docker run --interactive --tty --volume /:/ext mindandbrain/halfpipe`   |

You should now see the user interface.

#### Background

Containers are by default isolated from the host computer. This adds security, but also means that the container cannot access the data it needs for analysis. `HALFpipe` expects all inputs (e.g., image files and spreadsheets) and outputs (the working directory) to be places in the path`/ext` (see also [`--fs-root`](#data-file-system-root---fs-root)). Using the option `--bind /:/ext`, we instruct `Singularity` to map all of the host file system (`/`) to that path (`/ext`). You can also run `HALFpipe` and only map only part of the host file system, but keep in mind that any directories that are not mapped will not be visible later.

`Singularity` passes the host shell environment to the container by default. This means that in some cases, the host computer's configuration can interfere with the software. To avoid this, we need to pass the option `--cleanenv`.`Docker` does not pass the host shell environment by default, so we don't need to pass an option.

## 2. User interface

The user interface asks a series of questions about your data and the analyses you want to run. In each question, you can press `Control+C` to cancel the current question and go back to the previous one. `Control+D` exits the program without saving. Note that these keyboard shortcuts are the same on Mac.

### Files

To run preprocessing, at least a T1-weighted structural image and a BOLD image file is required. Preprocessing and data analysis proceeds automatically. However, to be able to run automatically, data files need to be input in a way suitable for automation. 

For this kind of automation, `HALFpipe` needs to know the relationships between files, such as which files belong to the same subject. However, even though it would be obvious for a human, a program cannot easily assign a file name to a subject, and this will be true as long as there are differences in naming between different researchers or labs. One researcher may name the same file `subject_01_rest.nii.gz` and another `subject_01/scan_rest.nii.gz`. 

In `HALFpipe`, we solve this issue by inputting file names in a specific way. For example, instead of `subject_01/scan_rest.nii.gz`, `HALFpipe` expects you to input `{subject}/scan_rest.nii.gz`. `HALFpipe` can then match all files on disk that match this naming schema, and extract the subject ID `subject_01`. Using the extracted subject ID, other files can now be matched to this image. If all input files are available in BIDS format, then this step can be skipped.

1. `Specify working directory` All intermediate and outputs of `HALFpipe` will be placed in the working directory. Keep in mind to choose a location with sufficient free disk space, as intermediates can be multiple gigabytes in size for each subject.
1. `Is the data available in BIDS format?`
   - `Yes`
        1. `Specify the path of the BIDS directory`
   - `No`
        1. `Specify anatomical/structural data`\
           `Specify the path of the T1-weighted image files`
        1. `Specify functional data`\
           `Specify the path of the BOLD image files`
        1. `Check repetition time values` / `Specify repetition time in seconds`
        1. `Add more BOLD image files?`
             - `Yes` Loop back to 2
             - `No` Continue
1. `Do slice timing?`
    - `Yes`
        1. `Check slice acquisition direction values`
        1. `Check slice timing values`
    - `No` Skip this step
1. `Specify field maps?` If the data was imported from a BIDS directory, this step will be omitted.
    - `Yes`
        1. `Specify the type of the field maps`
            - EPI (blip-up blip-down)
                1. `Specify the path of the blip-up blip-down EPI image files`
            - Phase difference and magnitude (used by Siemens scanners)
                1. `Specify the path of the magnitude image files`
                1. `Specify the path of the phase/phase difference image files`
                1. `Specify echo time difference in seconds`
            - Scanner-computed field map and magnitude (used by GE / Philips scanners)
                1. `Specify the path of the magnitude image files`
                1. `Specify the path of the field map image files`
        1. `Add more field maps?` Loop back to 1
        1. `Specify effective echo spacing for the functional data in seconds`
        1. `Specify phase encoding direction for the functional data`
    - `No` Skip this step

### Features

Features are analyses that are carried out on the preprocessed data, in other words, first-level analyses.

1. `Specify first-level features?`
    - `Yes`
      1. `Specify the feature type`
         - `Task-based`
           1. `Specify feature name`
           1. `Specify images to use`
           1. `Specify the event file type`
             - `SPM multiple conditions` A MATLAB .mat file containing three arrays: `names` (condition), `onsets` and `durations`
             - `FSL 3-column` One text file for each condition. Each file has its corresponding condition in the filename. The first column specifies the event onset, the second the duration. The third column of the files is ignored, so parametric modulation is not supported
             - `BIDS TSV` A tab-separated table with named columns `trial_type` (condition), `onset` and `duration`
           1. `Specify the path of the event files` 
           1. `Select conditions to add to the model`
           1. `Specify contrasts`
              1. `Specify contrast name`
              1. `Specify contrast values`
              1. `Add another contrast?`
                 - `Yes` Loop back to 1
                 - `No` Continue
           1. `Apply a temporal filter to the design matrix?` A separate temporal filter can be specified for the design matrix. In contrast, the temporal filtering of the input image and any confound regressors added to the design matrix is specified in 10. In general, the two settings should match
           1. `Apply smoothing?`
              - `Yes`
                 1. `Specify smoothing FWHM in mm`
              - `No` Continue
           1. `Grand mean scaling will be applied with a mean of 10000.000000`
           1. `Temporal filtering will be applied using a gaussian-weighted filter`\
              `Specify the filter width in seconds`
           1. `Remove confounds?`
         - `Seed-based connectivity`
           1. `Specify feature name`
           1. `Specify images to use`
           1. `Specify binary seed mask file(s)`
              1. `Specify the path of the binary seed mask image files`
              1. `Check space values`
              1. `Add binary seed mask image file`
         - `Dual regression`
           1. `Specify feature name`
           1. `Specify images to use`
           1. TODO
         - `Atlas-based connectivity matrix`
           1. `Specify feature name`
           1. `Specify images to use`
           1. TODO
         - `ReHo`
           1. `Specify feature name`
           1. `Specify images to use`
           1. TODO
         - `fALFF`
           1. `Specify feature name`
           1. `Specify images to use`
           1. TODO
    - `No` Skip this step
1. `Add another first-level feature?`
     - `Yes` Loop back to 1
     - `No` Continue
1. `Output a preprocessed image?`
     - `Yes`
       1. `Specify setting name`
       1. `Specify images to use`
       1. `Apply smoothing?`
          - `Yes`
             1. `Specify smoothing FWHM in mm`
          - `No` Continue
       1. `Do grand mean scaling?`
          - `Yes`
             1. `Specify grand mean`
          - `No` Continue
       1. `Apply a temporal filter?`
          - `Yes`
             1. `Specify the type of temporal filter`
                - `Gaussian-weighted`
                - `Frequency-based`
          - `No` Continue
       1. `Remove confounds?`
     - `No` Continue

### Models

Models are statistical analyses that are carried out on the features.

> TODO

## 3.	Running on a high-performance computing cluster

1. Log in to your cluster's head node

1. Request an interactive job. Refer to your cluster's documentation for how to do this

1. In the interactive job, run the `HALFpipe` user interface, but add the flag `--use-cluster` to the end of the command. \
   For example, `singularity run --no-home --cleanenv --bind /:/ext halfpipe_latest.sif --use-cluster`

1. As soon as you finish specifying all your data, features and models in the user interface, `HALFpipe` will now generate everything needed to run on the cluster. For hundreds of subjects, this can take up to a few hours.

1. When `HALFpipe` exits, edit the generated submit script `submit.slurm.sh` according to your cluster's documentation and then run it. This submit script will calculate everything except group statistics.
     
1. As soon as all processing has been completed, you can run group statistics. This is usually very fast, so you can do this in an interactive session. Run `singularity run --no-home --cleanenv --bind /:/ext halfpipe_latest.sif --only-model-chunk` and then select `Run without modification` in the user interface. 

> A common issue with remote work via secure shell is that the connection may break after a few hours. For batch jobs this is not an issue, but for interactive jobs this can be quite frustrating. When the connection is lost, the node you were connected to will automatically quit all programs you were running.
> To prevent this, you can run interactive jobs within `screen` or `tmux` (whichever is available). These commands allow you to open sessions in the terminal that will continue running in the background even when you close or disconnect. Here's a quick overview of how to use the commands (more in-depth documentation is available for example at http://www.dayid.org/comp/tm.html).
>    1. Open a new screen/tmux session on the head node by running either `screen` or `tmux`
>    1. Request an interactive job from within the session, for example with `srun --pty bash -i`
>    1. Run the command that you want to run
>    1. Detach from the screen/tmux session, meaning disconnecting with the ability to re-connect later \
>       For screen, this is done by first pressing `Control+a`, then letting go, and then pressing `d` on the keyboard. \
>       For tmux, it's `Control+b` instead of `Control+a`. \
>       Note that this is always `Control`, even if you're on a mac.
>    1. Close your connection to the head node with `Control+d`. `screen`/`tmux` will remain running in the background
>    1. Later, connect again to the head node. Run `screen -r` or `tmux attach` to check back on the interactive job. If everything went well and the command you wanted to run finished, close the interactive job with `Control+d` and then the `screen`/`tmux` session with `Control+d` again. \
>    If the command hasn't finished yet, detach as before and come back later

## 4. Quality checks

> TODO

## 5. Outputs

- A visual report page \
  `reports/index.html`

- A table with image quality metrics \
  `reports/reportvals.txt`
  
- A table containing the preprocessing status \
  `reports/reportpreproc.txt`

- The untouched `fmriprep` derivatives. Some files have been omitted to save disk space \
  `fmriprep` is very strict about only processing data that is compliant with the BIDS standard. As such, we may need to format subjects names for compliance. For example, an input subject named `subject_01` will appear as `subject01` in the `fmriprep` derivatives. \
  `derivatives/fmriprep`

### Features

- For task-based, seed-based connectivity and dual regression features, `HALFpipe` outputs the statistical maps for the effect, the variance, the degrees of freedom of the variance and the z-statistic. In FSL, the effect and variance are also called `cope` and `varcope` \
  `derivatives/halfpipe/sub-.../func/..._stat-effect_statmap.nii.gz` \
  `derivatives/halfpipe/sub-.../func/..._stat-variance_statmap.nii.gz` \
  `derivatives/halfpipe/sub-.../func/..._stat-dof_statmap.nii.gz` \
  `derivatives/halfpipe/sub-.../func/..._stat-z_statmap.nii.gz` \
  The design and contrast matrix used for the final model will be outputted alongside the statistical maps \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._desc-design_matrix.tsv` \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._desc-contrast_matrix.tsv`

- ReHo and fALFF are not calculated based on a linear model. As such, only one statistical map of the z-scaled values will be output \
  `derivatives/halfpipe/sub-.../func/..._alff.nii.gz` \
  `derivatives/halfpipe/sub-.../func/..._falff.nii.gz` \
  `derivatives/halfpipe/sub-.../func/..._reho.nii.gz`
  
- For every feature, a JSON file containing a summary of the preprocessing settings, and a list of the raw data files that were used for the analysis (`RawSources`) \
  `derivatives/halfpipe/sub-.../func/....json`
    
- For every feature, the corresponding brain mask is output beside the statistical maps. Masks do not differ between different features calculated, they are only copied out repeatedly for convenience \
  `derivatives/halfpipe/sub-.../func/...desc-brain_mask.nii.gz` 

- Atlas-based connectivity outputs the time series and the full covariance and correlation matrices as text files \
  `derivatives/halfpipe/sub-.../func/..._timeseries.txt` \
  `derivatives/halfpipe/sub-.../func/..._desc-covariance_matrix.txt` \
  `derivatives/halfpipe/sub-.../func/..._desc-correlation_matrix.txt`

### Preprocessed images

- Masked, preprocessed BOLD image \
  `derivatives/halfpipe/sub-.../func/..._bold.nii.gz`
  
- Just like for features \
  `derivatives/halfpipe/sub-.../func/..._bold.json`
  
- Just like for features \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._setting-..._desc-brain_mask.nii.gz` 
  
- Filtered confounds time series, where all filters that are applied to the BOLD image are applied to the regressors as well. Note that this means that when grand mean scaling is active, confounds time series are also scaled, meaning that values such as `framewise displacement` can not be interpreted in terms of their original units anymore. \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._setting-..._desc-confounds_regressors.tsv`

### Models

- `grouplevel/...`

## 6. Troubleshooting

- If an error occurs, this will be output to the command line and simultaneously to the `err.txt` file in the working directory
- If the error occurs while running, usually a text file detailing the error will be placed in the working directory. These are text files and their file names start with `crash`
  - Usually, the last line of these text files contains the error message. Please read this carefully, as may allow you to understand the error
  - For example, consider the following error message: \
    `ValueError: shape (64, 64, 33) for image 1 not compatible with first image shape (64, 64, 34) with axis == None` \
    This error message may seem cryptic at first. However, looking at the message more closely, it suggests that two input images have different, incompatible dimensions. In this case, `HALFpipe` correctly recognized this issue, and there is no need for concern. The images in question will simply be excluded from preprocessing and/or analysis
  - In some cases, the cause of the error can be a bug in the `HALFpipe` code. In this case, please submit an [issue](https://github.com/mindandbrain/halfpipe/issues/new/choose) or contact us via [e-mail](#9-contact).

## 7. Command line flags

### Control command line logging `--verbose`

By default, only errors and warnings will be output to the command line. This makes it easier to see when something goes wrong, because there is less output. However, if you want to be able to inspect what is being run, you can add the `--verbose` flag to the end of the command used to call `HALFpipe`. 

Verbose logs are always written to the `log.txt` file in the working directory, so going back and inspecting this log is always possible, even if the `--verbose` flag was not specified.

### Automatically remove unneeded files `--keep`

`HALFpipe` creates many intermediate files. In environments with limited disk capacity, this can be problematic. On the other hand, keeping intermediate files is useful, because once computed, intermediate files do not need to be re-calculated should `HALFpipe` be run again, for example with different setting. However, to limit disk usage, `HALFpipe` can delete intermediate files as soon as they are not needed anymore. This behavior is controlled with the `--keep` flag.
 
The default option `--keep some` keeps all intermediate files from `fmriprep`. As these take the longest to compute, we believe this is a good tradeoff between disk space and computer time. `--keep all` turns of all deletion of intermediate files. `--keep none` deletes as much as possible.

### Adjust nipype `--nipype-<omp-nthreads|memory-gb|n-procs|run-plugin>`

> TODO

### Lifecycle flags `--<only|skip>-<spec-ui|workflow|run|model-chunk>`

A `HALFpipe` run is divided internally into three stages, spec-ui, workflow, and run.
1. The `spec-ui` stage is where you specify things in the user interface. It creates the `spec.json` file that contains all the information needed to run `HALFpipe`. To only run this stage, use the option `--only-spec-ui`. To skip this stage, use the option `--skip-spec-ui`
1. The `workflow` stage is where `HALFpipe` uses the `spec.json` data to search for all the files that match what was input in the user interface. It then generates a `nipype` workflow for preprocessing, feature extraction and group models. `nipype` then validates the workflow and prepares it for execution. This usually takes a couple of minutes and cannot be parallelized. For hundreds of subjects, this may even take a few hours. This stage has the corresponding option `--only-workflow` and `--skip-workflow`.
  - This stage saves several intermediate files. These are named `workflow.{uuid}.pickle.xz`, `execgraph.{uuid}.pickle.xz` and `execgraph.{n_chunks}_chunks.{uuid}.pickle.xz`. The `uuid` in the file name is a unique identifier generated from the `spec.json` file and the input files. It is re-calculated every time we run this stage. The uuid algorithm produces a different output if there are any changes (such as when new input files for new subjects become available, or the `spec.json` is changed, for example to add a new feature or group model). Otherwise, the `uuid` stays the same. Therefore, if a workflow file with the calculated `uuid` already exists, then we do not need to run this stage. We can simple re-use the workflow from the existing file, and save some time.
  - In this stage, we can also decide to split the execution into chunks. The flag `--subject-chunks` creates one chunk per subject. The flag `--use-cluster` automatically activates `--subject-chunks`. The flag `--n-chunks` allows the user to specify a specific number of chunks. This is useful if the execution should be spread over a set number of computers. In addition to these, a model chunk is generated. 
1. The `run` stage loads the `execgraph.{n_chunks}_chunks.{uuid}.pickle.xz` file generated in the previous step and runs it. This file usually contains two chunks, one for the subject level preprocessing and feature extraction ("subject level chunk"), and one for group statistics ("model chunk"). To run a specific chunk, you can use the flags `--only-chunk-index ...` and `--only-model-chunk`.

### Working directory `--workdir`

> TODO

### Data file system root `--fs-root`

The `HALFpipe` container, or really most containers, contain the entire base system needed to run

## 8. Changes

### Beta 2 (August 16th 2020)

-	**Slice timing:** Upon user request, `HALFpipe` now exposes `fmriprep`’s slice timing option. In `fmriprep`, this option is set once when starting. As such, it is currently not possible to either a) do slice timing for only part of the images or b) simultaneously output a slice timed and a non-slice timed preprocessed image. For both of these cases we recommend doing multiple runs of `HALFpipe`, and to repeat quality control for both
-	**Metadata loading and verification:** A lot of different metadata is required for the correct functioning of `HALFpipe`. Usually, the way metadata is stored has some user-specific idiosyncrasies and conventions that can be difficult to automate around. For this reason, we have decided to prompt the user to verify and/or enter any and every metadata value. To streamline this process, `HALFpipe` attempts to load metadata a) from a "sidecar" JSON file placed next to the target file, or b) from the NIFTI header. If neither is possible, the user is prompted to manually enter the required parameter
-	**Output multiple preprocessed image files:** The user interface now supports outputting different preprocessed image files with different settings. For these files, we expose the full breadth of settings available in `HALFpipe`. Specifically, these are:
    1. *Grand mean scaling*
    1. *Spatial smoothing*, implemented using AFNI `3dBlurInMask` 
    1. *Temporal filtering*
       - *Gaussian-weighted*, using a custom implementation of the algorithm used by FSL `fslmaths -bptf`. This algorithm is explained in the "Trend Removal" section of [Marchini & Ripley (2000)](https://doi.org/10.1006/nimg.2000.0628)
       - *Frequency-based*, implemented using AFNI `3dTproject`
    1. *ICA-AROMA*, using a custom implementation of the algorithm used by FSL `fsl_regfilt`
    1. *Confounds regression*, using a custom implementation of the algorithm used by FSL `fsl_regfilt -a`
-	**Simpler use on cluster systems:** We added the command line option `—-use-cluster`. When this command line option is added to the end of the command, we automatically a) divide the workflow into one subject chunks and b) instead of running, output a template cluster submit script called `submit.slurm.sh`. This script is made for SLURM clusters, but can easily be adapted to other systems
-	**Output files now follow the BIDS derivatives naming scheme:** We value interoperability with other software. [`HALFpipe` outputs](#5-outputs) can now be automatically be parsed by software that accepts BIDS derivatives
-	**Additional output files:** For every statistical map, we place a BIDS-conforming JSON file containing a summary of the preprocessing settings, and a list of the raw data files that were used for the analysis (`RawSources`)
    * *Task-based:* Design matrix, contrast matrix
    * *Seed-based connectivity:* Design matrix, contrast matrix, mean tSNR of the seed region (`MeanTSNR`)
    * *Dual regression:* Design matrix, contrast matrix, mean tSNR of the component (`MeanTSNR`)
    * *Atlas-based connectivity matrix:* List of mean tSNR values of the atlas region (`MeanTSNR`)
    * *Group models:* Design matrix, contrast matrix
-	**Improved confounds handling:** [Lindquist et al. (2018)](https://doi.org/10.1101/407676) find that in preprocessing pipelines, "later preprocessing steps can reintroduce artifacts previously removed from the data in prior preprocessing steps". This happens because individual preprocessing steps are not necessarily orthogonal. To circumvent this issue they recommend "sequential orthogonalization of covariates/linear filters performed in series." We have now implemented this strategy in `HALFpipe`. Note that this means that when grand mean scaling is active, confounds time series are also scaled, meaning that values such as `framewise displacement` can not be interpreted as millimeters anymore.
-	**Recovering from errors:** Even if one subject fails, group statistics will still be run and available. This can be useful when data quality issues make specific preprocessing steps fail

## 9. Contact

For questions or support, please submit an [issue](https://github.com/mindandbrain/halfpipe/issues/new/choose) or contact us via e-mail.

| Name        | Role            | E-mail address         |
|-------------|-----------------|------------------------|
| Lea Waller  | Developer       | lea.waller@charite.de  |
| Ilya Veer   | Project manager | ilya.veer@charite.de   |
| Susanne Erk | Project manager | susanne.erk@charite.de |
