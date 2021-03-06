# Changelog

## 1.0.1 (January 27th 2021)

### Maintenance

- Add `xlrd` dependency to allow loading xlsx files as spreadsheets.

### Bug fixes

- Fix task-based feature extraction. FMRIPrep by default automatically detects
  T1 non-equilibriated volumes at the start of each scan, and removes them. This
  can lead to timing issues when we fit a task GLM. We chose to disable this
  feature to avoid these issues. We expect researchers to manually remove these
  "dummy" volumes. Usually this is not necessary, for example Siemens scanners
  do it automatically.

## 1.0.0 (January 19th 2021)

### Maintenance

- Update `templateflow` version.
- Switch container build to GitHub Actions to make it more predictable.

### Bug fixes

- Fix slice order selection in user interface. HALFpipe allows the user to
  manually specify the slice order after activating slice timing, in case the
  image metadata is wrong or was not found. Besides sequential ordering, the
  user can choose between different schemes of interleaved slice acquisition.
  One differentiator of interleaved slice ordering schemes is whether an even
  slice is acquired first, or an odd slice. The problem with that nomenclature
  is that it is a matter of convention whether the first slice is even or odd.
  If the first slice is number one, then it is odd. However, one could also
  understand the zeroth slice to come first, for example in the context of
  programming, which would be even. We updated the user interface to make clear
  that the first slice is number one, and odd.
- Fix report page display for processing errors by outputting the
  reports/reporterror.js output file. Include a new version if the
  reports/index.html file that can parse and display it.
- Fix running Docker container on macOS, as the '--volume' flag mounts the macOS
  disk only in a subdirectory of /ext or /mnt.

## 1.0.0 Beta 6 (December 8th 2020)

### Enhancements

- Run group models with listwise deletion so that missing brain coverage in one
  subject does not lead to a missing voxel in the group statistic. This is not
  possible to do with FSL `flameo`, but we still wanted to use the FLAME
  algorithm
  ([Woolrich et al. 2004](https://doi.org/10.1016/j.neuroimage.2003.12.023)). As
  such, I re-implemented the algorithm to adaptively adjust the design matrix
  depending on brain coverage.
- Add automated testing. Any future code changes need to pass all automated
  tests before they can be uploaded to the master branch (and thus be available
  for download). The tests take around two hours to complete and include a full
  run of Halfpipe for one subject.
- Increase run speed by running all tasks in parallel as opposed to only most.
  Previously, the code would run all tasks related to copying and organizing
  data on the main thread. This is a convention introduced by `nipype`. It is
  based on the assumption that the main thread may run on the head node of a
  cluster and submit all tasks as jobs to the cluster. To prevent quick tasks
  from clogging the cluster queue, they are run on the head node. However, as we
  do not use `nipype` that way, we can improve performance by getting rid of
  this behavior.
- Improve debug output to include variable names when an error occurs.
- Improve `--watchdog` option to include memory usage information.

### Maintenance

- Bump `pybids`, `fmriprep`, `smriprep`, `niworkflows`, `nipype` and
  `templateflow` versions.

### Bug fixes

- Fix design matrix specification with numeric subject names and leading zeros.
- Fix design matrix specification of F-contrasts.
- Fix selecting subjects by group for numeric group names.
- Fix an error with seed connectivity when excluding a seed due to missing brain
  coverage (#19).
- Force output file names to be BIDS compatible and improve their naming.
- Stop `fmriprep` from creating a `work` folder in the Halfpipe working
  directory.

## 1.0.0 Beta 5 (October 29th 2020)

### Enhancements

- Implement continuous integration that runs automated tests of any changes in
  code. This means that, if implemented correctly, bugs that are fixed once can
  be covered by these tests so that they are not accidentally introduced again
  further down the line. This approach is called regression testing.
- Add codecov plugin to monitor the percentage of code that is covered by
  automated tests. Halfpipe is currently at 2%, which is very low, but this will
  improve over time as we write more testing code.
- Improve granularity of the `--keep` automatic intermediate file deletion so
  that more files are deleted, and add automated tests to verify the correctness
  of file deletion decisions.
- Add `--nipype-resource-monitor` command line option to monitor memory usage of
  the workflow and thus diagnose memory issues
- Re-implement logging code to run in a separate process, reducing the burden on
  the main process. This works by passing a Python `multiprocessing.Queue` to
  all nipype worker processes, so that all workers put log messages into the
  queue using a `logging.handlers.QueueHandler`. I then implemented a listener
  that would read from this queue and route the log messages to the appropriate
  log files and the terminal standard output. I first implemented the listener
  with `threading`. Threading is a simple way to circumvent I/O delays slowing
  down the main code. With threading, the Python interpreter switches between
  the logging and main threads regularly. As a result, when the logging thread
  waits for the operating system to write to disk or to acquire a file lock, the
  main thread can do work in the meantime, and vice versa. Very much
  unexpectedly, this code led to segmentation faults in Python. To better
  diagnose these errors, I refactored the logging thread to a separate process,
  because I thought there may be some kind of problem with threading. Through
  this work, I discovered that I was using a different `multiprocessing` context
  for instantiating the logging queue and the nipype workers, which caused the
  segmentation faults. Even though it is now unnecessary, I decided to keep the
  refactored code with logging in a separate process, because there are no
  downsides and I had already put the work in.
- Re-phrase some logging messages for improved clarity.
- Refactor command line argument parser and dispatch code to a separate module
  to increase code clarity and readability.
- Refactor spreadsheet loading code to new parse module.
- Print warnings when encountering invalid NIfTI file headers.
- Avoid unnecessary re-runs of preprocessing steps by naming workflows using
  hashes instead of counts. This way adding/removing features and settings from
  the spec.json can be more efficient if intermediate results are kept.
- Refactor `--watchdog` code
- Refactor workflow code to use the new collect_boldfiles function to decide
  which functional images to pre-process and which to exclude from processing.
  The collect_boldfiles function implements new rules to resolve duplicate
  files. If multiple functional images with the same tags are found, for example
  identical subject name, task and run number, only one will be included.
  Ideally, users would delete such duplicate files before running Halfpipe, but
  we also do not want Halfpipe to fail in these cases. Two heuristic rules are
  used: 1) Use the longer functional image. Usually, the shorter image will be a
  scan that was aborted due to technical issues and had to be repeated. 2) If
  both images have the same number of volumes, the one with the alphabetically
  last file name will be used.

## Maintenance

- Apply pylint code style rules.
- Refactor automated tests to use pytest fixtures.

## Bug fixes

- Log all warning messages but reduce the severity level of warnings that are
  known to be benign.
- Fix custom interfaces MaskCoverage, MergeMask, and others based on the
  Transformer class to not discard the NIfTI header when outputting the
  transformed images
- Fix execution stalling when the logger is unable to acquire a lock on the log
  file. Use the `flufl.lock` package for hard link-based file locking, which is
  more robust on distributed file systems and NFS. Add a fallback to regular
  `fcntl`-based locking if that fails, and another fallback to circumvent log
  file locking entirely, so that logs will always be written out no matter what
  (#10).
- Fix accidentally passing T1w images to fmriprep that don’t have corresponding
  functional images.
- Fix merging multiple exclude.json files when quality control is done
  collaboratively.
- Fix displaying a warning for README and dataset_description.json files in BIDS
  datasets.
- Fix parsing phase encoding direction from user interface to not only parse the
  axis but also the direction. Before, there was no difference between selecting
  anterior-to-posterior and posterior-to-anterior, which is incorrect.
- Fix loading repetition time coded in milliseconds or microseconds from NIfTI
  files (#13).
- Fix error when trying to load repetition time from 3D NIfTI file (#12).
- Fix spreadsheet loading with UTF-16 file encoding (#3).
- Fix how missing values are displayed in the user interface when checking
  metadata.
- Fix unnecessary inconsistent setting warnings in the user interface.

## 1.0.0 Beta 4 (October 1st 2020)

### Enhancements

- ENH: Add adaptive memory requirement for the submit script generated by
  `--use-cluster`
- ENH: Output the proportion of seeds and atlas region that is covered by the
  brain mask to the sidecar JSON file as key `Coverage`
- ENH: Add option to exclude seeds and atlas regions that do not meet a
  user-specified `Coverage` threshold
- ENH: More detailed display of missing metadata in user interface
- ENH: More robust handling of NIfTI headers

### Maintenance

- MAINT: Update `fmriprep` to latest release 20.2.0
- MAINT: Update `setup.cfg` with latest `pandas`, `smriprep`, `mriqc` and
  `niworkflows`
- MAINT: Update `Dockerfile` and `Singularity` recipes to use the latest version
  of `fmriprep`

### Bug fixes

- FIX: Fix an error that occurred when first level design matrices are sometimes
  passed to the higher level model code alongside the actual statistics
- FIX: Missing sidecar JSON file for atlas-based connectivity features
- FIX: Allow reading of spreadsheets that contain byte-order marks (#3)
- FIX: Incorrect file name for execgraphs file was generated or the submit
  script generated by `--use-cluster`
- FIX: Misleading warning for inconsistencies between NIfTI header
  `slice_duration` and repetition time
- FIX: Ignore additional misleading warnings
- FIX: Incorrect regular expression to select aCompCor columns from confounds
- FIX: Detect all exclude.json files in workdir
- FIX: Replace existing derivatives if nipype outputs have been overwritten

## 1.0.0 Beta 3 (September 14th 2020)

### Enhancements

- ENH: Implement listwise deletion for missing values in linear model via the
  new filter type `missing`
- ENH: Allow the per-variable specification of missing value strategy for linear
  models, either listwise deletion (default) or mean substitution
- ENH: Add validators for metadata
- ENH: Allow slice timing to be specified by selecting the slice order from a
  menu
- ENH: Add option `Add another feature` when using a working directory with
  existing `spec.json`
- ENH: Add minimum region coverage option for atlas-based connectivity

### Maintenance

- MAINT: Update `setup.cfg` with latest `nipype`, `fmriprep`, `smriprep` and
  `niworkflows` versions

### Bug fixes

- FIX: Do not crash when `MergeColumns` `row_index` is empty
- FIX: Remove invalid fields from result in `AggregateResultdicts`
- FIX: Show slice timing option for BIDS datasets
- FIX: Correctly store manually specified slice timing in the `spec.json` for
  BIDS datasets
- FIX: Build `nitime` dependency from source to avoid build error
- FIX: Do not crash when confounds contain `n/a` values in
  `init_confounds_regression_wf`
- FIX: Adapt code to new `fmriprep` and `niworkflows` versions
- FIX: Correct capitalization in fixed effects aggregate model names
- FIX: Do not show group model option for atlas-based connectivity features
- FIX: Rename output files so that `contrast` from task-based features becomes
  `taskcontrast` to avoid conflict with the contrast names in group-level models
- FIX: Catch input file errors in report viewer so that it doesn’t crash
- FIX: Improve naming of group level design matrix TSV files

## 1.0.0 Beta 2 (August 16th 2020)

- **Slice timing:** Upon user request, `HALFpipe` now exposes `fmriprep`’s slice
  timing option. In `fmriprep`, this option is set once when starting. As such,
  it is currently not possible to either a) do slice timing for only part of the
  images or b) simultaneously output a slice timed and a non-slice timed
  preprocessed image. For both of these cases we recommend doing multiple runs
  of `HALFpipe`, and to repeat quality control for both.
- **Metadata loading and verification:** A lot of different metadata is required
  for the correct functioning of `HALFpipe`. Usually, the way metadata is stored
  has some user-specific idiosyncrasies and conventions that can be difficult to
  automate around. For this reason, we have decided to prompt the user to verify
  and/or enter any and every metadata value. To streamline this process,
  `HALFpipe` attempts to load metadata a) from a "sidecar" JSON file placed next
  to the target file, or b) from the NIFTI header. If neither is possible, the
  user is prompted to manually enter the required parameter
- **Output multiple preprocessed image files:** The user interface now supports
  outputting different preprocessed image files with different settings. For
  these files, we expose the full breadth of settings available in `HALFpipe`.
  Specifically, these are:
  1. _Grand mean scaling_
  1. _Spatial smoothing_, implemented using AFNI `3dBlurInMask`
  1. _Temporal filtering_
     - _Gaussian-weighted_, using a custom implementation of the algorithm used
       by FSL `fslmaths -bptf`. This algorithm is explained in the "Trend
       Removal" section of
       [Marchini & Ripley (2000)](https://doi.org/10.1006/nimg.2000.0628)
     - _Frequency-based_, implemented using AFNI `3dTproject`
  1. _ICA-AROMA_, using a custom implementation of the algorithm used by FSL
     `fsl_regfilt`
  1. _Confounds regression_, using a custom implementation of the algorithm used
     by FSL `fsl_regfilt -a`
- **Simpler use on cluster systems:** We added the command line option
  `—-use-cluster`. When this command line option is added to the end of the
  command, we automatically a) divide the workflow into one subject chunks and
  b) instead of running, output a template cluster submit script called
  `submit.slurm.sh`. This script is made for SLURM clusters, but can easily be
  adapted to other systems
- **Output files now follow the BIDS derivatives naming scheme:** We value
  interoperability with other software.
  [`HALFpipe` outputs](https://github.com/mindandbrain/halfpipe#5-outputs) can
  now be automatically be parsed by software that accepts BIDS derivatives
- **Additional output files:** For every statistical map, we place a
  BIDS-conforming JSON file containing a summary of the preprocessing settings,
  and a list of the raw data files that were used for the analysis
  (`RawSources`)
  - _Task-based:_ Design matrix, contrast matrix
  - _Seed-based connectivity:_ Design matrix, contrast matrix, mean tSNR of the
    seed region (`MeanTSNR`)
  - _Dual regression:_ Design matrix, contrast matrix, mean tSNR of the
    component (`MeanTSNR`)
  - _Atlas-based connectivity matrix:_ List of mean tSNR values of the atlas
    region (`MeanTSNR`)
  - _Group models:_ Design matrix, contrast matrix
- **Improved confounds handling:**
  [Lindquist et al. (2018)](https://doi.org/10.1101/407676) find that in
  preprocessing pipelines, "later preprocessing steps can reintroduce artifacts
  previously removed from the data in prior preprocessing steps". This happens
  because individual preprocessing steps are not necessarily orthogonal. To
  circumvent this issue they recommend "sequential orthogonalization of
  covariates/linear filters performed in series." We have now implemented this
  strategy in `HALFpipe`. Note that this means that when grand mean scaling is
  active, confounds time series are also scaled, meaning that values such as
  `framewise displacement` can not be interpreted as millimeters anymore.
- **Recovering from errors:** Even if one subject fails, group statistics will
  still be run and available. This can be useful when data quality issues make
  specific preprocessing steps fail
