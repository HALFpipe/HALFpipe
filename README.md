# Welcome to ENIGMA `HALFpipe`

[![https://www.singularity-hub.org/static/img/hosted-singularity--hub-%23e32929.svg](https://www.singularity-hub.org/static/img/hosted-singularity--hub-%23e32929.svg)](https://singularity-hub.org/collections/4508)
[![https://github.com/HALFpipe/HALFpipe/workflows/build/badge.svg](https://github.com/HALFpipe/HALFpipe/workflows/build/badge.svg)](https://github.com/HALFpipe/HALFpipe/actions?query=workflow%3A%22build%22)
[![https://github.com/HALFpipe/HALFpipe/workflows/continuous%20integration/badge.svg](https://github.com/HALFpipe/HALFpipe/workflows/continuous%20integration/badge.svg)](https://github.com/HALFpipe/HALFpipe/actions?query=workflow%3A%22continuous+integration%22)
[![codecov](https://codecov.io/gh/HALFpipe/HALFpipe/branch/master/graph/badge.svg)](https://codecov.io/gh/HALFpipe/HALFpipe)

`HALFpipe` is a user-friendly software that facilitates reproducible analysis of
fMRI data, including preprocessing, single-subject, and group analysis. It
provides state-of-the-art preprocessing using
[`fmriprep`](https://fmriprep.readthedocs.io/), but removes the necessity to
convert data to the
[`BIDS`](https://bids-specification.readthedocs.io/en/stable/) format. Common
resting-state and task-based fMRI features can then be calculated on the fly
using [`FSL`](http://fsl.fmrib.ox.ac.uk/) and
[`nipype`](https://nipype.readthedocs.io/) for statistics.

> If you encounter issues, please see the [troubleshooting](#troubleshooting)
> section of this document.

## Table of Contents

<!-- toc -->

- [Getting started](#getting-started)
  - [Container platform](#container-platform)
  - [Download](#download)
  - [Running](#running)
- [User interface](#user-interface)
  - [Files](#files)
  - [Features](#features)
  - [Models](#models)
- [Running on a high-performance computing cluster](#running-on-a-high-performance-computing-cluster)
- [Quality checks](#quality-checks)
- [Outputs](#outputs)
  - [Subject-level features](#subject-level-features)
  - [Preprocessed images](#preprocessed-images)
  - [Group-level](#group-level)
- [Troubleshooting](#troubleshooting)
- [Command line flags](#command-line-flags)
  - [Control command line logging](#control-command-line-logging)
  - [Automatically remove unneeded files](#automatically-remove-unneeded-files)
  - [Adjust nipype](#adjust-nipype)
  - [Choose which parts to run or to skip](#choose-which-parts-to-run-or-to-skip)
  - [Working directory](#working-directory)
  - [Data file system root](#data-file-system-root)
- [Contact](#contact)

<!-- tocstop -->

## Getting started

`HALFpipe` is distributed as a container, meaning that all required software
comes bundled in a monolithic file, the container. This allows for easy
installation on new systems, and makes data analysis more reproducible, because
software versions are guaranteed to be the same for all users.

### Container platform

The first step is to install one of the supported container platforms. If you're
using a high-performance computing cluster, more often than not
[`Singularity`](https://sylabs.io) will already be available.

If not, we recommend using the latest version
of[`Singularity`](https://sylabs.io). However, it can be somewhat cumbersome to
install, as it needs to be built from source.

The [`NeuroDebian`](https://neuro.debian.net/) package repository provides an
older version of [`Singularity`](https://sylabs.io/guides/2.6/user-guide/) for
[some](https://neuro.debian.net/pkgs/singularity-container.html) Linux
distributions.

In contrast to `Singularity`, `Docker` always requires elevated privileges to
run containers. In other words, every user running a `Docker` container
automatically has administrator privileges on the computer they're using.
Therefore, it is inherently a bad choice for multi-user environments, where the
access of individual users should be limited. `Docker` is the only option that
is compatible with `Mac OS X`.

| Container platform | Version   | Installation                                                       |
| ------------------ | --------- | ------------------------------------------------------------------ |
| **Singularity**    | **3.5.3** | **See <https://sylabs.io/guides/3.5/user-guide/quick_start.html>** |
| Singularity        | 2.6.1     | `sudo apt install singularity-container`                           |
| Docker             |           | See <https://docs.docker.com/engine/install/>                      |

### Download

The second step is to download the `HALFpipe` to your computer. This requires
approximately 5 gigabytes of storage.

| Container platform | Installation                                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------ |
| Singularity        | `singularity pull docker://halfpipe/halfpipe:1.0.1` or `singularity pull docker://ghcr.io/halfpipe/halfpipe:1.0.1` |
| Docker             | `docker pull halfpipe/halfpipe:1.0.1`                                                                              |

`Singularity` version `3.x` creates a container image file called
`HALFpipe_{version}.sif` in the directory where you run the `pull` command. For
`Singularity` version `2.x` the file is named
`halfpipe-halfpipe-master-latest.simg`. Whenever you want to use the container,
you need pass `Singularity` the path to this file.

> **NOTE:** `Singularity` may store a copy of the container in its cache
> directory. The cache directory is located by default in your home directory at
> `~/.singularity`. If you need to save disk space in your home directory, you
> can safely delete the cache directory after downloading, i.e. by running
> `rm -rf ~/.singularity`. Alternatively, you could move the cache directory
> somewhere with more free disk space using a symlink. This way, files will
> automatically be stored there in the future. For example, if you have a lot of
> free disk space in `/mnt/storage`, then you could first run
> `mv ~/.singularity /mnt/storage` to move the cache directory, and then
> `ln -s /mnt/storage/.singularity ~/.singularity` to create the symlink.

`Docker` will store the container in its storage base directory, so it does not
matter from which directory you run the `pull` command.

### Running

The third step is to run the downloaded container. You may need to replace
`halfpipe_1.0.1.sif` with the actual path and filename where `Singularity`
downloaded your container.

| Container platform | Command                                                                 |
| ------------------ | ----------------------------------------------------------------------- |
| Singularity        | `singularity run --no-home --cleanenv --bind /:/ext halfpipe_1.0.1.sif` |
| Docker             | `docker run --interactive --tty --volume /:/ext halfpipe/halfpipe`      |

You should now see the user interface.

#### Background

Containers are by default isolated from the host computer. This adds security,
but also means that the container cannot access the data it needs for analysis.
`HALFpipe` expects all inputs (e.g., image files and spreadsheets) and outputs
(the working directory) to be places in the path`/ext` (see also
[`--fs-root`](#data-file-system-root---fs-root)). Using the option
`--bind /:/ext`, we instruct `Singularity` to map all of the host file system
(`/`) to that path (`/ext`). You can also run `HALFpipe` and only map only part
of the host file system, but keep in mind that any directories that are not
mapped will not be visible later.

`Singularity` passes the host shell environment to the container by default.
This means that in some cases, the host computer's configuration can interfere
with the software. To avoid this, we need to pass the option `--cleanenv`.
`Docker` does not pass the host shell environment by default, so we don't need
to pass an option.

## User interface

The user interface asks a series of questions about your data and the analyses
you want to run. In each question, you can press `Control+C` to cancel the
current question and go back to the previous one. `Control+D` exits the program
without saving. Note that these keyboard shortcuts are the same on Mac.

### Files

To run preprocessing, at least a T1-weighted structural image and a BOLD image
file is required. Preprocessing and data analysis proceeds automatically.
However, to be able to run automatically, data files need to be input in a way
suitable for automation.

For this kind of automation, `HALFpipe` needs to know the relationships between
files, such as which files belong to the same subject. However, even though it
would be obvious for a human, a program cannot easily assign a file name to a
subject, and this will be true as long as there are differences in naming
between different researchers or labs. One researcher may name the same file
`subject_01_rest.nii.gz` and another `subject_01/scan_rest.nii.gz`.

In `HALFpipe`, we solve this issue by inputting file names in a specific way.
For example, instead of `subject_01/scan_rest.nii.gz`, `HALFpipe` expects you to
input `{subject}/scan_rest.nii.gz`. `HALFpipe` can then match all files on disk
that match this naming schema, and extract the subject ID `subject_01`. Using
the extracted subject ID, other files can now be matched to this image. If all
input files are available in BIDS format, then this step can be skipped.

1. `Specify working directory` All intermediate and outputs of `HALFpipe` will
   be placed in the working directory. Keep in mind to choose a location with
   sufficient free disk space, as intermediates can be multiple gigabytes in
   size for each subject.
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
1. `Specify field maps?` If the data was imported from a BIDS directory, this
   step will be omitted.
   - `Yes`
     1. `Specify the type of the field maps`
        - EPI (blip-up blip-down)
          1. `Specify the path of the blip-up blip-down EPI image files`
        - Phase difference and magnitude (used by Siemens scanners)
          1. `Specify the path of the magnitude image files`
          1. `Specify the path of the phase/phase difference image files`
          1. `Specify echo time difference in seconds`
        - Scanner-computed field map and magnitude (used by GE / Philips
          scanners)
          1. `Specify the path of the magnitude image files`
          1. `Specify the path of the field map image files`
     1. `Add more field maps?` Loop back to 1
     1. `Specify effective echo spacing for the functional data in seconds`
     1. `Specify phase encoding direction for the functional data`
   - `No` Skip this step

### Features

Features are analyses that are carried out on the preprocessed data, in other
words, first-level analyses.

1. `Specify first-level features?`
   - `Yes`
     1. `Specify the feature type`
        - `Task-based`
          1. `Specify feature name`
          1. `Specify images to use`
          1. `Specify the event file type`
          - `SPM multiple conditions` A MATLAB .mat file containing three
            arrays: `names` (condition), `onsets` and `durations`
          - `FSL 3-column` One text file for each condition. Each file has its
            corresponding condition in the filename. The first column specifies
            the event onset, the second the duration. The third column of the
            files is ignored, so parametric modulation is not supported
          - `BIDS TSV` A tab-separated table with named columns `trial_type`
            (condition), `onset` and `duration`. While BIDS supports defining
            additional columns, `HALFpipe` will currently ignore these
          1. `Specify the path of the event files`
          1. `Select conditions to add to the model`
          1. `Specify contrasts`
             1. `Specify contrast name`
             1. `Specify contrast values`
             1. `Add another contrast?`
                - `Yes` Loop back to 1
                - `No` Continue
          1. `Apply a temporal filter to the design matrix?` A separate temporal
             filter can be specified for the design matrix. In contrast, the
             temporal filtering of the input image and any confound regressors
             added to the design matrix is specified in 10. In general, the two
             settings should match
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

## Running on a high-performance computing cluster

1. Log in to your cluster's head node

1. Request an interactive job. Refer to your cluster's documentation for how to
   do this

1. In the interactive job, run the `HALFpipe` user interface, but add the flag
   `--use-cluster` to the end of the command. \
   For example, `singularity run --no-home --cleanenv --bind /:/ext halfpipe_latest.sif --use-cluster`

1. As soon as you finish specifying all your data, features and models in the
   user interface, `HALFpipe` will now generate everything needed to run on the
   cluster. For hundreds of subjects, this can take up to a few hours.

1. When `HALFpipe` exits, edit the generated submit script `submit.slurm.sh`
   according to your cluster's documentation and then run it. This submit script
   will calculate everything except group statistics.

1. As soon as all processing has been completed, you can run group statistics.
   This is usually very fast, so you can do this in an interactive session. Run
   `singularity run --no-home --cleanenv --bind /:/ext halfpipe_latest.sif --only-model-chunk`
   and then select `Run without modification` in the user interface.

> A common issue with remote work via secure shell is that the connection may
> break after a few hours. For batch jobs this is not an issue, but for
> interactive jobs this can be quite frustrating. When the connection is lost,
> the node you were connected to will automatically quit all programs you were
> running. To prevent this, you can run interactive jobs within `screen` or
> `tmux` (whichever is available). These commands allow you to open sessions in
> the terminal that will continue running in the background even when you close
> or disconnect. Here's a quick overview of how to use the commands (more
> in-depth documentation is available for example at
> [http://www.dayid.org/comp/tm.html]).
>
> 1. Open a new screen/tmux session on the head node by running either `screen`
>    or `tmux`
> 1. Request an interactive job from within the session, for example with
>    `srun --pty bash -i`
> 1. Run the command that you want to run
> 1. Detach from the screen/tmux session, meaning disconnecting with the ability
>    to re-connect later \
>    For screen, this is done by first pressing `Control+a`, then letting go, and
>    then pressing `d` on the keyboard. \
>    For tmux, it's `Control+b` instead of `Control+a`. \
>    Note that this is always `Control`, even if you're on a mac.
> 1. Close your connection to the head node with `Control+d`. `screen`/`tmux`
>    will remain running in the background
> 1. Later, connect again to the head node. Run `screen -r` or `tmux attach` to
>    check back on the interactive job. If everything went well and the command
>    you wanted to run finished, close the interactive job with `Control+d` and
>    then the `screen`/`tmux` session with `Control+d` again. If the command
>    hasn't finished yet, detach as before and come back later

## Quality checks

Please see the manual at <https://docs.google.com/document/d/1evDkVaoXqSaxulp5eSxVqgaxro7yZl-gao70D0S2dH8>

## Outputs

- A visual report page `reports/index.html`

- A table with image quality metrics `reports/reportvals.txt`

- A table containing the preprocessing status `reports/reportpreproc.txt`

- The untouched `fmriprep` derivatives. Some files have been omitted to save
  disk space `fmriprep` is very strict about only processing data that is
  compliant with the BIDS standard. As such, we may need to format subjects
  names for compliance. For example, an input subject named `subject_01` will
  appear as `subject01` in the `fmriprep` derivatives. `derivatives/fmriprep`

### Subject-level features

- For task-based, seed-based connectivity and dual regression features,
  `HALFpipe` outputs the statistical maps for the effect, the variance, the
  degrees of freedom of the variance and the z-statistic. In FSL, the effect and
  variance are also called `cope` and `varcope` \
  `derivatives/halfpipe/sub-.../func/..._stat-effect_statmap.nii.gz` \
  `derivatives/halfpipe/sub-.../func/..._stat-variance_statmap.nii.gz` \
  `derivatives/halfpipe/sub-.../func/..._stat-dof_statmap.nii.gz` \
  `derivatives/halfpipe/sub-.../func/..._stat-z_statmap.nii.gz` \
  The design and contrast matrix used for the final model will be outputted alongside
  the statistical maps \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._desc-design_matrix.tsv`
  \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._feature-..._desc-contrast_matrix.tsv`

- ReHo and fALFF are not calculated based on a linear model. As such, only one
  statistical map of the z-scaled values will be output \
  `derivatives/halfpipe/sub-.../func/..._alff.nii.gz` \
  `derivatives/halfpipe/sub-.../func/..._falff.nii.gz` \
  `derivatives/halfpipe/sub-.../func/..._reho.nii.gz`

- For every feature, a JSON file containing a summary of the preprocessing
- settings, and a list of the raw data files that were used for the analysis
  (`RawSources`) \
  `derivatives/halfpipe/sub-.../func/....json`

- For every feature, the corresponding brain mask is output beside the
  statistical maps. Masks do not differ between different features calculated,
  they are only copied out repeatedly for convenience \
  `derivatives/halfpipe/sub-.../func/...desc-brain_mask.nii.gz`

- Atlas-based connectivity outputs the time series and the full covariance and
  correlation matrices as text files \
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

- Filtered confounds time series, where all filters that are applied to the BOLD
  image are applied to the regressors as well. Note that this means that when
  grand mean scaling is active, confounds time series are also scaled, meaning
  that values such as `framewise displacement` can not be interpreted in terms
  of their original units anymore. \
  `derivatives/halfpipe/sub-.../func/sub-..._task-..._setting-..._desc-confounds_regressors.tsv`

### Group-level

- `grouplevel/...`

## Troubleshooting

- If an error occurs, this will be output to the command line and simultaneously
  to the `err.txt` file in the working directory
- If the error occurs while running, usually a text file detailing the error
  will be placed in the working directory. These are text files and their file
  names start with `crash`
  - Usually, the last line of these text files contains the error message.
    Please read this carefully, as may allow you to understand the error
  - For example, consider the following error message:
    `ValueError: shape (64, 64, 33) for image 1 not compatible with first image shape (64, 64, 34) with axis == None`
    This error message may seem cryptic at first. However, looking at the
    message more closely, it suggests that two input images have different,
    incompatible dimensions. In this case, `HALFpipe` correctly recognized this
    issue, and there is no need for concern. The images in question will simply
    be excluded from preprocessing and/or analysis
  - In some cases, the cause of the error can be a bug in the `HALFpipe` code.
    Please check that no similar issue has been reported
    [here on GitHub](https://github.com/HALFpipe/HALFpipe/issues). In this case,
    please submit an
    [issue](https://github.com/HALFpipe/HALFpipe/issues/new/choose).

## Command line flags

### Control command line logging

```bash
--verbose
```

By default, only errors and warnings will be output to the command line. This
makes it easier to see when something goes wrong, because there is less output.
However, if you want to be able to inspect what is being run, you can add the
`--verbose` flag to the end of the command used to call `HALFpipe`.

Verbose logs are always written to the `log.txt` file in the working directory,
so going back and inspecting this log is always possible, even if the
`--verbose` flag was not specified.

Specifying the flag `--debug` will print additional, fine-grained messages. It
will also automatically start the
[Python Debugger](https://docs.python.org/3/library/pdb.html) when an error
occurs. You should only use `--debug` if you know what you're doing.

### Automatically remove unneeded files

```bash
--keep
```

`HALFpipe` saves intermediate files for each pipeline step. This speeds up
re-running with different settings, or resuming after a job after it was
cancelled. The intermediate file are saved by the
[`nipype`](https://nipype.readthedocs.io/) workflow engine, which is what
`HALFpipe` uses internally. `nipype` saves the intermediate files in the
`nipype` folder in the working directory.

In environments with limited disk capacity, this can be problematic. To limit
disk usage, `HALFpipe` can delete intermediate files as soon as they are not
needed anymore. This behavior is controlled with the `--keep` flag.

The default option `--keep some` keeps all intermediate files from fMRIPrep and
MELODIC, which would take the longest to re-run. We believe this is a good
tradeoff between disk space and computer time. `--keep all` turns of all
deletion of intermediate files. `--keep none` deletes as much as possible,
meaning that the smallest amount possible of disk space will be used.

### Configure nipype

```bash
--nipype-<omp-nthreads|memory-gb|n-procs|run-plugin>
```

`HALFpipe` chooses sensible defaults for all of these values.

### Choose which parts to run or to skip

```bash
--<only|skip>-<spec-ui|workflow|run|model-chunk>
```

A `HALFpipe` run is divided internally into three stages, spec-ui, workflow, and
run.

1. The `spec-ui` stage is where you specify things in the user interface. It
   creates the `spec.json` file that contains all the information needed to run
   `HALFpipe`. To only run this stage, use the option `--only-spec-ui`. To skip
   this stage, use the option `--skip-spec-ui`
1. The `workflow` stage is where `HALFpipe` uses the `spec.json` data to search
   for all the files that match what was input in the user interface. It then
   generates a `nipype` workflow for preprocessing, feature extraction and group
   models. `nipype` then validates the workflow and prepares it for execution.
   This usually takes a couple of minutes and cannot be parallelized. For
   hundreds of subjects, this may even take a few hours. This stage has the
   corresponding option `--only-workflow` and `--skip-workflow`.

- This stage saves several intermediate files. These are named
  `workflow.{uuid}.pickle.xz`, `execgraph.{uuid}.pickle.xz` and
  `execgraph.{n_chunks}_chunks.{uuid}.pickle.xz`. The `uuid` in the file name is
  a unique identifier generated from the `spec.json` file and the input files.
  It is re-calculated every time we run this stage. The uuid algorithm produces
  a different output if there are any changes (such as when new input files for
  new subjects become available, or the `spec.json` is changed, for example to
  add a new feature or group model). Otherwise, the `uuid` stays the same.
  Therefore, if a workflow file with the calculated `uuid` already exists, then
  we do not need to run this stage. We can simple re-use the workflow from the
  existing file, and save some time.
- In this stage, we can also decide to split the execution into chunks. The flag
  `--subject-chunks` creates one chunk per subject. The flag `--use-cluster`
  automatically activates `--subject-chunks`. The flag `--n-chunks` allows the
  user to specify a specific number of chunks. This is useful if the execution
  should be spread over a set number of computers. In addition to these, a model
  chunk is generated.

1. The `run` stage loads the `execgraph.{n_chunks}_chunks.{uuid}.pickle.xz` file
   generated in the previous step and runs it. This file usually contains two
   chunks, one for the subject level preprocessing and feature extraction
   ("subject level chunk"), and one for group statistics ("model chunk"). To run
   a specific chunk, you can use the flags `--only-chunk-index ...` and
   `--only-model-chunk`.

### Working directory

```bash
--workdir
```

> TODO

### Data file system root

```bash
--fs-root
```

The `HALFpipe` container, or really most containers, contain the entire base
system needed to run

## Contact

For questions or support, please submit an
[issue](https://github.com/HALFpipe/HALFpipe/issues/new/choose) or contact us
via e-mail.

| Name        | Role            | E-mail address         |
| ----------- | --------------- | ---------------------- |
| Lea Waller  | Developer       | lea.waller@charite.de  |
| Ilya Veer   | Project manager | ilya.veer@charite.de   |
| Susanne Erk | Project manager | susanne.erk@charite.de |
