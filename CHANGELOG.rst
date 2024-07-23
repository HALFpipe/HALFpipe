Changelog
=========

1.2.2 (March 15th 2022)
-----------------------

Bug fixes
---------

- Fix issue with BOLD to T1w registration (#230, #238, #239)
- Also detect `exclude.json` files that are placed in the `reports/` folder (#228)
- Improve error message when the FreeSurfer license file is missing (#231)
- Fix a rare calculation error for `fd_mean` and related image quality metrics (#237, #241)
- Fix various warning messages (#247)
- Fix performance issue when collecting inputs for group statistics ()
- Fix a user interface issue where the option `Start over after models` was missing (#259, #260)
- Fix an issue where `sub-` prefixes were not recognized correctly when filtering inputs for group statistics (#264)
- Fix an issue when writing mixed data type columns to the text files in the `reports/` folder (#274)
- Fix warnings for missing quality check information (#276)
- Fix errors when aggregating subjects with different numbers of scans during group statistics (#280)
- Fix error when fMRIPrep skips a BOLD file (#285)

Maintenance
-----------

- Bump `indexed_gzip` (#240)
- Bump `nipype` after bug fix (#255)
- Bump `fmriprep` after bug fix (#262)
- Upgrade to Python 3.10, clean up code and add more unit tests (#269)
- Make continuous integration tests run faster (#282, #284)
- Add type checking and linting to continuous integration (#285)

1.2.1 (October 1st 2021)
------------------------

Bug fixes
---------

- Fix issues that occurred after re-scaling ``fd_perc`` to be percent (#217)
- Catch error when ``NaN`` values occur within the linear algebra code (#215)
- Reduce memory usage when running large workflows by only loading the
  chunks that will be necessary for the current process (#216)
- Improve memory usage prediction for cluster submission scripts (#219)
- Update metadata module with better log messages (#220)

1.2.0 (September 7th 2021)
--------------------------

New features and enhancements
-----------------------------

-  Improve the assignment of field maps to functional scans, print
   warnings when detecting an incomplete field map or when a complete
   field map is not recognized by fMRIPrep (#115 and #192)
-  Remove conditions that have no events from the task-based model. This
   is important for designs where the conditions depend on subject
   performance (#90)
-  Output additional images during group mode. Voxel-wise descriptive
   statistics (#142), typical subject-level variance (#148)
-  Divide outputs into subfolders to make navigating the files easier
-  Output metadata to sidecar files, including resolution, field-of-view
   and field map type (#154 and #181)
-  Add an option to skip dummy/non-steady-state scans and modify event
   onsets accordingly (#167, #176, #182 and #187)
-  Improve performance during workflow creation (#192)

Bug fixes
---------

-  Update ``fMRIPrep`` to fix normalization bug (#51)
-  Improve memory usage prediction. Fixes ``BrokenProcessPool`` and
   ``Killed: 137`` errors (#125, #156 and #157)
-  Refactor ``Dockerfile`` to correctly re-build ``matplotlib`` caches
   (#107)
-  Fix assignment of event files to functional scans. Make sure that the
   assignment is consistent between what is shown in the user interface
   and during workflow creation. Add unit tests (#139)
-  Fix crashes for datasets deviating from the ``BIDS`` specification
   and remove misleading warnings for incompatible and hidden files
-  Fix ``AssertionError`` crash when no group model is specified
-  Rephrase user interface for loading ``.mat`` event files. Do not say
   that the time unit (seconds or scans) is missing, which was
   confusing.
-  Fix various crashes when running on a cluster
-  Fix user interface crash when no categorical variables are defined in
   a spreadsheet
-  Fix loading subject-level results during group model. Get rid of
   ``LoadResult`` nodes, instead use a subclass of ``Node`` (#137)
-  Use slower but more robust least-squares solve for group statistics
   (#141)
-  Fix performance issue during ``t2z_convert`` procedure during group
   statistics (#143, #144 and #145)
-  Remove output from heterogeneity group statistics that was causing
   performance issues (#146)
-  Fix confusing ``EOFError`` message on exit by gracefully stopping
   child processes before exit (#130 and #160)
-  Fix running FreeSurfer with ``run_reconall`` option (#87)
-  Add error message when running on an unsupported file system such as
   ``FAT`` (#102)
-  Fix confusing error message when no features are specified (#147)
-  Re-scale ``fd_perc`` output to percent (#186)
-  Reduce user interface memory usage (#191)
-  Fix automated testing hanging on the logging worker (#192)

Maintenance
-----------

-  Update Python to version 3.8
-  Update ``templateflow``, ``pybids``, ``nibabel``
-  Pin ``dipy`` version due to incompatibility with ``nipype``
-  Pin ``indexed_gzip`` version due to incompatibility of newer version
   with some files (#85)
-  Add new Singularity container build workflow (#97 and #138)
-  Improve documentation to suggest running Singularity with
   ``--containall`` instead of ``--no-home --cleanenv``
-  Refactor code to use ``defaultdict`` to increase readability
-  Add more type hints
-  Rename main branch from ``master`` to ``main``
-  Add ``pre-commit`` and ``pip-tools`` to better manage dependencies
-  Install as many dependencies as possible via ``conda`` and the rest
   via ``pip`` (#164)
-  Refactor workflow code to allow handling of surface-based functional
   images (#161)
-  In-progress refactor ``model`` package into ``schema`` package. Use
   ``dataclasses`` for better integration with type checkers (#173, #174
   and #178)

1.1.1 (May 13th 2021)
---------------------

Enhancements
------------

-  Performance improvements during workflow creation

.. _maintenance-1:

Maintenance
~~~~~~~~~~~

-  Update ``pybids``
-  Remove Singularity Hub definition files, as the platform was shut
   down
-  Add ``line_profiler`` dependency

.. _bug-fixes-1:

Bug fixes
~~~~~~~~~

-  Fix path pattern support for regular expressions
-  Fix reading empty event and spreadsheet files
-  Fix detecting the path of the data partition bind mount inside the
   container

1.1.0 (April 18th 2021)
-----------------------

With many thanks to @jstaph for contributions

.. _new-features-and-enhancements-1:

New features and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  Create high-performance computing cluster submission scripts for
   Torque/PBS and SGE cluster as well (#71)
-  Calculate additional statistics such as heterogeneity
   (https://doi.org/fzx69f) and a test that data is
   missing-completely-at-random via logistic regression (#67)
-  Always enable ICA-AROMA even when its outputs are not required for
   feature extraction so that its report image is always available for
   quality assessment (#75)
-  Support loading presets or plugins that may make it easier to do
   harmonized analyses across many sites (#8)
-  Support adding derivatives of the HRF to task-based GLM design
   matrices
-  Support detecting the amount of available memory when running as a
   cluster job, or when running as a container with a memory limit such
   as when using Docker on Mac

.. _maintenance-2:

Maintenance
~~~~~~~~~~~

-  Add type hints to code. This allows a type checker like ``pyright``
   to suggest possible error sources ahead of time, making programming
   more efficient
-  Add ``openpyxl`` and ``xlsxwriter`` dependencies to support
   reading/writing Excel XLSX files
-  Update ``numpy``, ``scipy`` and ``nilearn`` versions
-  Add additional automated tests

.. _bug-fixes-2:

Bug fixes
~~~~~~~~~

-  Fix importing slice timing information from a file after going back
   to the prompt via undo (#55)
-  Fix a warning when loading task event timings from a MAT-file.
   NiftiheaderLoader tried to load metadata for it like it would for a
   NIfTI file (#56)
-  Fix ``numpy`` array broadcasting error when loading data from 3D
   NIfTI files that have been somehow marked as being four-dimensional
-  Fix misunderstanding of the output value ``resels`` of FSL’s
   ``smoothest`` command. The value refers to the size of a resel, not
   the number of them in the image. The helper function ``_critical_z``
   now taked this into account now. (nipy/nipype#3316)
-  Fix naming of output files in ``derivatives/halfpipe`` and
   ``grouplevel`` folder so that capitalization is consistent with
   original IDs and names (#57)
-  Fix the summary display after ``BIDS`` import to show the number of
   “subjects” and not the number of “subs”
-  Fix getting the required metadata fields for an image type by
   implementing a helper function
-  Fix outputting source files for the quality check web app (#62)
-  Fix assigning field maps to specific functional images, which is done
   by a mapping between field map task and functional image tags. The
   mapping is automatically inferred for BIDS datasets and manually
   specified otherwise (#66)
-  Force re-calculation of ``nipype`` workflows after ``HALFpipe``
   update so that changes from the new version are applied in existing
   working directories as well
-  Do not fail task-based feature extraction if no events are available
   for a particular condition for a particular subject (#58)
-  Force using a recent version of the ``indexed_gzip`` dependency to
   avoid error (#85)
-  Improve loading delimited data in ``loadspreadsheet`` function
-  Fix slice timing calculation in user interface

1.0.1 (January 27th 2021)
-------------------------

.. _maintenance-3:

Maintenance
~~~~~~~~~~~

-  Add ``xlrd`` dependency to allow loading xlsx files as spreadsheets.

.. _bug-fixes-3:

Bug fixes
~~~~~~~~~

-  Fix task-based feature extraction. FMRIPrep by default automatically
   detects T1 non-equilibriated volumes at the start of each scan, and
   removes them. This can lead to timing issues when we fit a task GLM.
   We chose to disable this feature to avoid these issues. We expect
   researchers to manually remove these “dummy” volumes. Usually this is
   not necessary, for example Siemens scanners do it automatically.

1.0.0 (January 19th 2021)
-------------------------

.. _maintenance-4:

Maintenance
~~~~~~~~~~~

-  Update ``templateflow`` version.
-  Switch container build to GitHub Actions to make it more predictable.

.. _bug-fixes-4:

Bug fixes
~~~~~~~~~

-  Fix slice order selection in user interface. HALFpipe allows the user
   to manually specify the slice order after activating slice timing, in
   case the image metadata is wrong or was not found. Besides sequential
   ordering, the user can choose between different schemes of
   interleaved slice acquisition. One differentiator of interleaved
   slice ordering schemes is whether an even slice is acquired first, or
   an odd slice. The problem with that nomenclature is that it is a
   matter of convention whether the first slice is even or odd. If the
   first slice is number one, then it is odd. However, one could also
   understand the zeroth slice to come first, for example in the context
   of programming, which would be even. We updated the user interface to
   make clear that the first slice is number one, and odd.
-  Fix report page display for processing errors by outputting the
   reports/reporterror.js output file. Include a new version if the
   reports/index.html file that can parse and display it.
-  Fix running Docker container on macOS, as the ‘–volume’ flag mounts
   the macOS disk only in a subdirectory of /ext or /mnt.

1.0.0 Beta 6 (December 8th 2020)
--------------------------------

.. _enhancements-1:

Enhancements
~~~~~~~~~~~~

-  Run group models with listwise deletion so that missing brain
   coverage in one subject does not lead to a missing voxel in the group
   statistic. This is not possible to do with FSL ``flameo``, but we
   still wanted to use the FLAME algorithm (`Woolrich et
   al. 2004 <https://doi.org/10.1016/j.neuroimage.2003.12.023>`__). As
   such, I re-implemented the algorithm to adaptively adjust the design
   matrix depending on brain coverage.
-  Add automated testing. Any future code changes need to pass all
   automated tests before they can be uploaded to the master branch (and
   thus be available for download). The tests take around two hours to
   complete and include a full run of Halfpipe for one subject.
-  Increase run speed by running all tasks in parallel as opposed to
   only most. Previously, the code would run all tasks related to
   copying and organizing data on the main thread. This is a convention
   introduced by ``nipype``. It is based on the assumption that the main
   thread may run on the head node of a cluster and submit all tasks as
   jobs to the cluster. To prevent quick tasks from clogging the cluster
   queue, they are run on the head node. However, as we do not use
   ``nipype`` that way, we can improve performance by getting rid of
   this behavior.
-  Improve debug output to include variable names when an error occurs.
-  Improve ``--watchdog`` option to include memory usage information.

.. _maintenance-5:

Maintenance
~~~~~~~~~~~

-  Bump ``pybids``, ``fmriprep``, ``smriprep``, ``niworkflows``,
   ``nipype`` and ``templateflow`` versions.

.. _bug-fixes-5:

Bug fixes
~~~~~~~~~

-  Fix design matrix specification with numeric subject names and
   leading zeros.
-  Fix design matrix specification of F-contrasts.
-  Fix selecting subjects by group for numeric group names.
-  Fix an error with seed connectivity when excluding a seed due to
   missing brain coverage (#19).
-  Force output file names to be BIDS compatible and improve their
   naming.
-  Stop ``fmriprep`` from creating a ``work`` folder in the Halfpipe
   working directory.

1.0.0 Beta 5 (October 29th 2020)
--------------------------------

.. _enhancements-2:

Enhancements
~~~~~~~~~~~~

-  Implement continuous integration that runs automated tests of any
   changes in code. This means that, if implemented correctly, bugs that
   are fixed once can be covered by these tests so that they are not
   accidentally introduced again further down the line. This approach is
   called regression testing.
-  Add codecov plugin to monitor the percentage of code that is covered
   by automated tests. Halfpipe is currently at 2%, which is very low,
   but this will improve over time as we write more testing code.
-  Improve granularity of the ``--keep`` automatic intermediate file
   deletion so that more files are deleted, and add automated tests to
   verify the correctness of file deletion decisions.
-  Add ``--nipype-resource-monitor`` command line option to monitor
   memory usage of the workflow and thus diagnose memory issues
-  Re-implement logging code to run in a separate process, reducing the
   burden on the main process. This works by passing a Python
   ``multiprocessing.Queue`` to all nipype worker processes, so that all
   workers put log messages into the queue using a
   ``logging.handlers.QueueHandler``. I then implemented a listener that
   would read from this queue and route the log messages to the
   appropriate log files and the terminal standard output. I first
   implemented the listener with ``threading``. Threading is a simple
   way to circumvent I/O delays slowing down the main code. With
   threading, the Python interpreter switches between the logging and
   main threads regularly. As a result, when the logging thread waits
   for the operating system to write to disk or to acquire a file lock,
   the main thread can do work in the meantime, and vice versa. Very
   much unexpectedly, this code led to segmentation faults in Python. To
   better diagnose these errors, I refactored the logging thread to a
   separate process, because I thought there may be some kind of problem
   with threading. Through this work, I discovered that I was using a
   different ``multiprocessing`` context for instantiating the logging
   queue and the nipype workers, which caused the segmentation faults.
   Even though it is now unnecessary, I decided to keep the refactored
   code with logging in a separate process, because there are no
   downsides and I had already put the work in.
-  Re-phrase some logging messages for improved clarity.
-  Refactor command line argument parser and dispatch code to a separate
   module to increase code clarity and readability.
-  Refactor spreadsheet loading code to new parse module.
-  Print warnings when encountering invalid NIfTI file headers.
-  Avoid unnecessary re-runs of preprocessing steps by naming workflows
   using hashes instead of counts. This way adding/removing features and
   settings from the spec.json can be more efficient if intermediate
   results are kept.
-  Refactor ``--watchdog`` code
-  Refactor workflow code to use the new collect_boldfiles function to
   decide which functional images to pre-process and which to exclude
   from processing. The collect_boldfiles function implements new rules
   to resolve duplicate files. If multiple functional images with the
   same tags are found, for example identical subject name, task and run
   number, only one will be included. Ideally, users would delete such
   duplicate files before running Halfpipe, but we also do not want
   Halfpipe to fail in these cases. Two heuristic rules are used: 1) Use
   the longer functional image. Usually, the shorter image will be a
   scan that was aborted due to technical issues and had to be repeated.
   2) If both images have the same number of volumes, the one with the
   alphabetically last file name will be used.

.. _maintenance-6:

Maintenance
~~~~~~~~~~~

-  Apply pylint code style rules.
-  Refactor automated tests to use pytest fixtures.

.. _bug-fixes-6:

Bug fixes
~~~~~~~~~

-  Log all warning messages but reduce the severity level of warnings
   that are known to be benign.
-  Fix custom interfaces MaskCoverage, MergeMask, and others based on
   the Transformer class to not discard the NIfTI header when outputting
   the transformed images
-  Fix execution stalling when the logger is unable to acquire a lock on
   the log file. Use the ``flufl.lock`` package for hard link-based file
   locking, which is more robust on distributed file systems and NFS.
   Add a fallback to regular ``fcntl``-based locking if that fails, and
   another fallback to circumvent log file locking entirely, so that
   logs will always be written out no matter what (#10).
-  Fix accidentally passing T1w images to fmriprep that don’t have
   corresponding functional images.
-  Fix merging multiple exclude.json files when quality control is done
   collaboratively.
-  Fix displaying a warning for README and dataset_description.json
   files in BIDS datasets.
-  Fix parsing phase encoding direction from user interface to not only
   parse the axis but also the direction. Before, there was no
   difference between selecting anterior-to-posterior and
   posterior-to-anterior, which is incorrect.
-  Fix loading repetition time coded in milliseconds or microseconds
   from NIfTI files (#13).
-  Fix error when trying to load repetition time from 3D NIfTI file
   (#12).
-  Fix spreadsheet loading with UTF-16 file encoding (#3).
-  Fix how missing values are displayed in the user interface when
   checking metadata.
-  Fix unnecessary inconsistent setting warnings in the user interface.

1.0.0 Beta 4 (October 1st 2020)
-------------------------------

.. _enhancements-3:

Enhancements
~~~~~~~~~~~~

-  ENH: Add adaptive memory requirement for the submit script generated
   by ``--use-cluster``
-  ENH: Output the proportion of seeds and atlas region that is covered
   by the brain mask to the sidecar JSON file as key ``Coverage``
-  ENH: Add option to exclude seeds and atlas regions that do not meet a
   user-specified ``Coverage`` threshold
-  ENH: More detailed display of missing metadata in user interface
-  ENH: More robust handling of NIfTI headers

.. _maintenance-7:

Maintenance
~~~~~~~~~~~

-  MAINT: Update ``fmriprep`` to latest release 20.2.0
-  MAINT: Update ``setup.cfg`` with latest ``pandas``, ``smriprep``,
   ``mriqc`` and ``niworkflows``
-  MAINT: Update ``Dockerfile`` and ``Singularity`` recipes to use the
   latest version of ``fmriprep``

.. _bug-fixes-7:

Bug fixes
~~~~~~~~~

-  FIX: Fix an error that occurred when first level design matrices are
   sometimes passed to the higher level model code alongside the actual
   statistics
-  FIX: Missing sidecar JSON file for atlas-based connectivity features
-  FIX: Allow reading of spreadsheets that contain byte-order marks (#3)
-  FIX: Incorrect file name for execgraphs file was generated or the
   submit script generated by ``--use-cluster``
-  FIX: Misleading warning for inconsistencies between NIfTI header
   ``slice_duration`` and repetition time
-  FIX: Ignore additional misleading warnings
-  FIX: Incorrect regular expression to select aCompCor columns from
   confounds
-  FIX: Detect all exclude.json files in workdir
-  FIX: Replace existing derivatives if nipype outputs have been
   overwritten

1.0.0 Beta 3 (September 14th 2020)
----------------------------------

.. _enhancements-4:

Enhancements
~~~~~~~~~~~~

-  ENH: Implement listwise deletion for missing values in linear model
   via the new filter type ``missing``
-  ENH: Allow the per-variable specification of missing value strategy
   for linear models, either listwise deletion (default) or mean
   substitution
-  ENH: Add validators for metadata
-  ENH: Allow slice timing to be specified by selecting the slice order
   from a menu
-  ENH: Add option ``Add another feature`` when using a working
   directory with existing ``spec.json``
-  ENH: Add minimum region coverage option for atlas-based connectivity

.. _maintenance-8:

Maintenance
~~~~~~~~~~~

-  MAINT: Update ``setup.cfg`` with latest ``nipype``, ``fmriprep``,
   ``smriprep`` and ``niworkflows`` versions

.. _bug-fixes-8:

Bug fixes
~~~~~~~~~

-  FIX: Do not crash when ``MergeColumns`` ``row_index`` is empty
-  FIX: Remove invalid fields from result in ``AggregateResultdicts``
-  FIX: Show slice timing option for BIDS datasets
-  FIX: Correctly store manually specified slice timing in the
   ``spec.json`` for BIDS datasets
-  FIX: Build ``nitime`` dependency from source to avoid build error
-  FIX: Do not crash when confounds contain ``n/a`` values in
   ``init_confounds_regression_wf``
-  FIX: Adapt code to new ``fmriprep`` and ``niworkflows`` versions
-  FIX: Correct capitalization in fixed effects aggregate model names
-  FIX: Do not show group model option for atlas-based connectivity
   features
-  FIX: Rename output files so that ``contrast`` from task-based
   features becomes ``taskcontrast`` to avoid conflict with the contrast
   names in group-level models
-  FIX: Catch input file errors in report viewer so that it doesn’t
   crash
-  FIX: Improve naming of group level design matrix TSV files

1.0.0 Beta 2 (August 16th 2020)
-------------------------------

-  **Slice timing:** Upon user request, ``HALFpipe`` now exposes
   ``fmriprep``\ ’s slice timing option. In ``fmriprep``, this option is
   set once when starting. As such, it is currently not possible to
   either a) do slice timing for only part of the images or b)
   simultaneously output a slice timed and a non-slice timed
   preprocessed image. For both of these cases we recommend doing
   multiple runs of ``HALFpipe``, and to repeat quality control for
   both.
-  **Metadata loading and verification:** A lot of different metadata is
   required for the correct functioning of ``HALFpipe``. Usually, the
   way metadata is stored has some user-specific idiosyncrasies and
   conventions that can be difficult to automate around. For this
   reason, we have decided to prompt the user to verify and/or enter any
   and every metadata value. To streamline this process, ``HALFpipe``
   attempts to load metadata a) from a “sidecar” JSON file placed next
   to the target file, or b) from the NIFTI header. If neither is
   possible, the user is prompted to manually enter the required
   parameter
-  **Output multiple preprocessed image files:** The user interface now
   supports outputting different preprocessed image files with different
   settings. For these files, we expose the full breadth of settings
   available in ``HALFpipe``. Specifically, these are:

   1. *Grand mean scaling*
   2. *Spatial smoothing*, implemented using AFNI ``3dBlurInMask``
   3. *Temporal filtering*

      -  *Gaussian-weighted*, using a custom implementation of the
         algorithm used by FSL ``fslmaths -bptf``. This algorithm is
         explained in the “Trend Removal” section of `Marchini & Ripley
         (2000) <https://doi.org/10.1006/nimg.2000.0628>`__
      -  *Frequency-based*, implemented using AFNI ``3dTproject``

   4. *ICA-AROMA*, using a custom implementation of the algorithm used
      by FSL ``fsl_regfilt``
   5. *Confounds regression*, using a custom implementation of the
      algorithm used by FSL ``fsl_regfilt -a``

-  **Simpler use on cluster systems:** We added the command line option
   ``—-use-cluster``. When this command line option is added to the end
   of the command, we automatically a) divide the workflow into one
   subject chunks and

   b) instead of running, output a template cluster submit script called
      ``submit.slurm.sh``. This script is made for SLURM clusters, but
      can easily be adapted to other systems

-  **Output files now follow the BIDS derivatives naming scheme:** We
   value interoperability with other software. `HALFpipe
   outputs <https://github.com/mindandbrain/halfpipe#5-outputs>`__ can
   now be automatically be parsed by software that accepts BIDS
   derivatives
-  **Additional output files:** For every statistical map, we place a
   BIDS-conforming JSON file containing a summary of the preprocessing
   settings, and a list of the raw data files that were used for the
   analysis (``RawSources``)

   -  *Task-based:* Design matrix, contrast matrix
   -  *Seed-based connectivity:* Design matrix, contrast matrix, mean
      tSNR of the seed region (``MeanTSNR``)
   -  *Dual regression:* Design matrix, contrast matrix, mean tSNR of
      the component (``MeanTSNR``)
   -  *Atlas-based connectivity matrix:* List of mean tSNR values of the
      atlas region (``MeanTSNR``)
   -  *Group models:* Design matrix, contrast matrix

-  **Improved confounds handling:** `Lindquist et
   al. (2018) <https://doi.org/10.1101/407676>`__ find that in
   preprocessing pipelines, “later preprocessing steps can reintroduce
   artifacts previously removed from the data in prior preprocessing
   steps”. This happens because individual preprocessing steps are not
   necessarily orthogonal. To circumvent this issue they recommend
   “sequential orthogonalization of covariates/linear filters performed
   in series.” We have now implemented this strategy in ``HALFpipe``.
   Note that this means that when grand mean scaling is active,
   confounds time series are also scaled, meaning that values such as
   ``framewise displacement`` can not be interpreted as millimeters
   anymore.
-  **Recovering from errors:** Even if one subject fails, group
   statistics will still be run and available. This can be useful when
   data quality issues make specific preprocessing steps fail
