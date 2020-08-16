Welcome to ENIGMA HALFpipe!
===========================

[![https://www.singularity-hub.org/static/img/hosted-singularity--hub-%23e32929.svg](https://www.singularity-hub.org/static/img/hosted-singularity--hub-%23e32929.svg)](https://singularity-hub.org/collections/4508) [![https://img.shields.io/docker/cloud/build/mindandbrain/halfpipe](https://img.shields.io/docker/cloud/build/mindandbrain/halfpipe)](https://hub.docker.com/repository/docker/mindandbrain/halfpipe/tags)

`ENIGMA HALFpipe` is a user-friendly software that facilitates reproducible analysis of fMRI data, including preprocessing, single-subject, and group analysis. It provides state-of-the-art preprocessing using [`fmriprep`](https://fmriprep.readthedocs.io/), but removes the necessity to convert data to the [`BIDS`](https://bids-specification.readthedocs.io/en/stable/) format. Common resting-state and task-based fMRI features can the be calculated on the fly using [`FSL`](http://fsl.fmrib.ox.ac.uk/) and [`nipype`](https://nipype.readthedocs.io/) for statistics.

> **NOTE:** ENIGMA HALFpipe is pre-release software and not yet considered production-ready.
>
> If you would like to beta test and provide feedback, thank you! We recommend starting out with Beta 2, as this has many new features. If you have used Beta 1 before, please carefully read the [changes section](#). If you encounter issues, please see the [troubleshooting](#) section of this document. 
>  
> Beta 1 has proven to work in a variety of environments in the past weeks of beta testing and remains available for comparison.
>
> | Version                   | Installation                                                                                             |
> |---------------------------|----------------------------------------------------------------------------------------------------------|
> | Beta 2 (August 16th 2020) | `singularity pull docker://mindandbrain/halfpipe:1.0.0b2`<br>`docker pull mindandbrain/halfpipe:1.0.0b2` |
> | Beta 1 (June 30th 2020)   | `singularity pull docker://mindandbrain/halfpipe:1.0.0b1`<br>`docker pull mindandbrain/halfpipe:1.0.0b1` |

## Table of Contents

> TODO

## 1. Getting started

HALFpipe is distributed as a container, meaning that all required software comes bundled in a monolithic file, the container. This allows for easy installation on new systems, and makes data analysis more reproducible, because software versions are guaranteed to be the same for all users.

### Container platform

The first step is to install one of the supported container platforms. If you're using a high-performance computing cluster, more often than not[`Singularity`](https://sylabs.io) will already be available.

If not, we recommend using the latest version of[`Singularity`](https://sylabs.io).However, it can be somewhat cumbersome to install, as it needs to be built from source.

The [`NeuroDebian`](https://neuro.debian.net/) package repository provides an older version of [`Singularity`](https://sylabs.io/guides/2.6/user-guide/) for[some](https://neuro.debian.net/pkgs/singularity-container.html) Linux distributions.

In contrast to `Singularity`, `Docker` always requires elevated privileges to run containers. In other words, every user running a `Docker` container automatically has administrator privileges on the computer they're using. Therefore, it is inherently a bad choice for multi-user environments, where the access of individual users should be limited. `Docker` is the only option that is compatible with `Mac OS X`.

| Container platform | Version   | Installation                                                     |
|--------------------|-----------|------------------------------------------------------------------|
| **Singularity**    | **3.5.3** | **See https://sylabs.io/guides/3.5/user-guide/quick_start.html** |
| Singularity        | 2.6.1     | `sudo apt install singularity-container`                         |
| Docker             |           | See https://docs.docker.com/engine/install/                      |

### Download

The second step is to download the HALFpipe to your computer. This requires approximately 5 gigabytes of storage.

| Container platform | Version | Installation                                      |
|--------------------|---------|---------------------------------------------------|
| Singularity        | 3.x     | `singularity pull shub://mindandbrain/halfpipe`   |
| Singularity        | 2.x     | `singularity pull docker://mindandbrain/halfpipe` |
| Docker             |         | `docker pull mindandbrain/halfpipe`               |

`Singularity` version `3.x` creates a container image file called`halfpipe_latest.sif` in the directory where you run the `pull` command. For `Singularity` version `2.x` the file is named`mindandbrain-halfpipe-master-latest.simg`. Whenever you want to use the container, you need pass `Singularity` the path to this file.

> **NOTE:** `Singularity` may store a copy of the container in its cache directory. The cache directory is located by default in your home directory at `~/.singularity`. If you need to save disk space, you can safely delete this directory after downloading, i.e. by running `rm -rf ~/.singularity`. Alternatively, you could move the cache directory somewhere with more free disk space using a symlink. This way, files will automatically be stored there in the future. For example, if you have a lot of free disk space in `/mnt/storage`, then you could first run `mv ~/.singularity /mnt/storage` to move the cache directory, and then `ln -s /mnt/storage/.singularity ~/.singularity` to create the symlonk.

`Docker` will store the container in its storage base directory, so it does not matter from which directory you run the `pull` command.

### Running

The third step is to run the downloaded container.

| Container platform | Command                                                                  |
|--------------------|--------------------------------------------------------------------------|
| Singularity        | `singularity run --no-home --cleanenv --bind /:/ext halfpipe_latest.sif` |
| Docker             | `docker run --interactive --tty --volume /:/ext mindandbrain/halfpipe`   |

You should now see the user interface.

#### Background

Containers are by default isolated from the host computer. This adds security, but also means that the container cannot access the data it needs for analysis. HALFpipe expects all inputs (e.g., image files and spreadsheets) and outputs (the working directory) to be places in the path`/ext` (see also [`--fs-root`](#--fs-root)). Using the option `--bind /:/ext`, we instruct `Singularity` to map all of the host file system (`/`) to that path (`/ext`). You can also run HALFpipe and only map only part of the host file system, but keep in mind that any directories that are not mapped will not be visible later.

`Singularity` passes the host shell environment to the container by default. This means that in some cases, the host computer's configuration can interfere with the software. To avoid this, we need to pass the option `--cleanenv`.`Docker` does not pass the host shell environment by default, so we don't need to pass an option.

## 2. User interface

The user interface asks a series of questions about your data and the analyses you want to run. In each question, you can press `Control+C` to cancel the current question and go back to the previous one. `Control+D` exits the program without saving. Note that these keyboard shortcuts are the same on Mac.

### Files

To run `fmriprep` preprocessing, at least a T1-weighted structural image and a BOLD image file is required. To automatically 

1. `Specify working directory` All intermediate and outputs of HALFpipe will be placed in the working directory. Keep in mind to choose a location with sufficient free disk space, as intermediates can be multiple gigabytes in size for each subject.
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
           1. `Apply a temporal filter to the design matrix?` Whereas the temporal filter of the input image and any confound regressors that may be added to the design matrix is determined by the preprocessing settings that follow in 10, a separate temporal filter can be specified for the events
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
         - `Atlas-based connectivity matrix`
           1. `Specify feature name`
           1. `Specify images to use`
         - `ReHo`
           1. `Specify feature name`
           1. `Specify images to use`
         - `fALFF`
           1. `Specify feature name`
           1. `Specify images to use`
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

> TODO

## 3.	Running on a high-performance computing cluster

> TODO

--n-chunks N_CHUNKS number of subject-level workflow chunks to generate --subject-chunks generate one subject-level workflow per subject --use-cluster generate workflow suitable for running on a cluster

run:

--execgraph-file EXECGRAPH_FILE manually select execgraph file --only-chunk-index ONLY_CHUNK_INDEX select which chunk to run --only-model-chunk

## 4. Outputs

- `reports/index.html`

- `reports/reportvals.txt`\
  `reports/reportpreproc.txt`

- `derivatives/fmriprep`

The following output paths are specified with the same convention as file inputs to HALFpipe. There is one addition. If

### Feature

- For task-based, seed-based connectivity and dual regression features, HALFpipe outputs the statistical maps for the effect, the variance, the degrees of freedom of the variance and the z-statistic. In FSL, the effect and variance are also called `cope` and `varcope`. \
  `derivatives/halfpipe/sub-.../func/sub-{subject}_task-..._feature-..._<contrast|seed|component>-{...}_stat-effect_statmap.nii.gz` \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._<contrast|seed|component>-{...}_stat-variance_statmap.nii.gz` \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._<contrast|seed|component>-{...}_stat-dof_statmap.nii.gz` \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._<contrast|seed|component>-{...}_stat-z_statmap.nii.gz` \
  A json file \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._<contrast|seed|component>-..._stat-effect_statmap.json` \
  The design and contrast matrix used for the final model will be outputted alongside the statistical maps. \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._desc-design_matrix.tsv` \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._desc-contrast_matrix.tsv`

- ReHo and fALFF are not calculated based on a linear model. As such, only one statistical map of the z-scaled values can be calculated. \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._<alff|falff|reho>.nii.gz` \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._<alff|falff|reho>.json`
  
- For every feature, the corresponding brain mask is output beside the statistical maps. This is done for convenience. Masks do not differ between different features calculated for the same input file. \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._mask.nii.gz` 

- Atlas-based connectivity outputs the full \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._atlas-..._timeseries.txt` \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._atlas-..._desc-covariance_matrix.txt` \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._atlas-..._desc-correlation_matrix.txt`

### Preprocessed image

- `derivatives/halfpipe/sub-.../func/sub-..._task-..._setting-..._bold.nii.gz` Masked, preprocessed BOLD image \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._setting-..._bold.json` Metadata for the \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._setting-..._desc-brain_mask.nii.gz` \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._setting-..._desc-confounds_regressors.tsv`

## 5. Troubleshooting



## 6. Command line flags

### Control command line logging `--verbose`

### Automatically remove unneeded files `--keep`

### Adjust nipype `--nipype-<omp-nthreads|memory-gb|n-procs|run-plugin>`

### Lifecycle flags `--<only|skip>-<spec-ui|workflow|run>`

A HALFpipe run is divided internally into four stages, spec-ui, workflow, execgraph and run.
* The `spec-ui` stage is where you specify things in the user interface. It creates the spec.json file. To only run this stage, use the option `--spec-ui-only`. To skip this stage 
* The `workflow` stage is where HALFpipe uses the spec.json data to search for all the files that match what was input in the user interface. It then generates a nipype workflow that is saved to the working directory as a file called `workflow.{uuid}.pickle.xz`. This usually takes a couple of minuted and cannot be parallelized. The uuid is a unique identifier generated from the spec file and the input files. It is re-calculated every time we run this stage. The uuid algorithm produces a different output if there are any changes (such as when new input files for new subjects become available, or the spec.json is changed to add a new analysis). Otherwise, it stays the same. Therefore, if a workflow file with the calculated uuid exists, then we do not need to run this stage. We can simple re-use the workflow from the existing file, and save some time. This stage has the corresponding option `--workflow-only`.
* The execgraph stage is where nipype validates the workflow that was generated in the previous stage and prepares it for execution. This also cannot be parallelized, and may take tens of minutes until around two hours for a thousand subjects. In this stage, we can also decide to split the execution into chunks, for example with the option `--subject-chunks` that creates one chunk per subject plus a group-level chunk.  The result is cached as a file in the working directory called `execgraph.{n_chunks}_chunks.{uuid}.pickle.xz`. The uuid part is used in the same way as before, so that we do not repeat this stage unless necessary.

### Working directory `--workdir`

### Data file system root `--fs-root`

The HALFpipe container, or really most containers, contain the entire base system needed to run

## 7. Changes

### Beta 2 (August 16th 2020)

-	**Slice timing:** Upon user request, HALFpipe now exposes fmriprep’s slice timing option. In fmriprep, this option is set once when starting. As such, it is currently not possible to either a) do slice timing for only part of the images or b) simultaneously output a slice timed and a non-slice timed preprocessed image. For both of these cases we recommend doing multiple runs of HALFpipe, and to repeat quality control for both.
-	**Metadata loading and verification:** A lot of different metadata is required for the correct functioning of HALFpipe. Usually, the way metadata is stored has some user-specific idiosyncrasies and conventions that can be difficult to automate around. For this reason, we have decided to prompt the user to verify and/or enter any and every metadata value. To streamline this process, HALFpipe attempts to load metadata a) from a “sidecar” json file placed next to the target file, or b) from the NIFTI header. If neither is possible, the user is prompted to manually enter the required parameter.
-	**Output multiple preprocessed image files:** The user interface now supports outputting different preprocessed image files with different settings. For these files, we expose the full breadth of settings available in HALFpipe. Specifically, these are:
  1. *Grand mean scaling*
  1. *Spatial smoothing*, implemented using AFNI `3dBlurInMask` 
  1. *Temporal filtering*
    <ol style="list-style-type:lower-alpha">
      <li>
        <i>Gaussian-weighted</i>, using a custom implementation of the algorithm used by FSL <code>fslmaths -bptf</code>. This algorithm is explained in the "Trend Removal" section of <a href="https://doi.org/10.1006/nimg.2000.0628">Marchini & Ripley (2000)</a>.
      </li>
      <li>
        <i>Frequency-based</i>, implemented using AFNI <code>3dTproject</code>
      </li>
    </ol>
  1. *ICA-AROMA*, using a custom implementation of the algorithm used by FSL `fsl_regfilt`
  1. *Confounds regression*, using a custom implementation of the algorithm used by FSL `fsl_regfilt -a`
-	**Simpler use on cluster systems:** We added the command line option `—use-cluster`. When this command line option is added to the end of the command, we automatically a) divide the workflow into one subject chunks and b) instead of running, output a template cluster submit script called “submit.slurm.sh”. This script is made for SLURM clusters, but can easily be adapted to other systems.
-	**Output files now follow the BIDS derivatives naming scheme:** We value interoperability with other software. [HALFpipe outputs](#) can now be automatically be parsed by software that accepts BIDS derivatives.
-	**Additional output files:** For every statistical map, we place a BIDS-conforming JSON file containing a summary of the preprocessing settings, and a list of the raw data files that were used for the analysis (`RawSources`).
  * *Task-based:* Design matrix, contrast matrix
  * *Seed-based connectivity:* Design matrix, contrast matrix, mean tSNR of the seed region (`MeanTSNR`)
  * *Dual regression:* Design matrix, contrast matrix, mean tSNR of the component (`MeanTSNR`)
  * *Atlas-based connectivity matrix:* List of mean tSNR values of the atlas region (`MeanTSNR`)
  * *Group models:* Design matrix, contrast matrix
-	**Improved confounds handling:** [Lindquist et al. (2018)](https://doi.org/10.1101/407676) find that in preprocessing pipelines, "later preprocessing steps can reintroduce artifacts previously removed from the data in prior preprocessing steps". This happens because individual preprocessing steps are not necessarily orthogonal. To circumvent this issue they recommend "sequential orthogonalization of covariates/linear filters performed in series." We have now implemented this strategy in HALFpipe. All preprocessing steps (filters) that are applied to the image file will be equally applied to the 
-	**Recovering from errors:** Even if one subject fails, group statistics will still be run and available. This can be useful when data quality issues make specific preprocessing steps fail.

## 8. Contact

For questions or support, please submit an [issue](https://github.com/mindandbrain/halfpipe/issues/new/choose) or contact us via e-mail.

| Name        | Role            | E-mail address         |
|-------------|-----------------|------------------------|
| Lea Waller  | Developer       | lea.waller@charite.de  |
| Ilya Veer   | Project manager | ilya.veer@charite.de   |
| Susanne Erk | Project manager | susanne.erk@charite.de |
