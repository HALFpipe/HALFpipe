# 1.0.0b5 (October 29, 2020)

## Enhancements

- Implement continuous integration that runs automated tests of any
  changes in code. This means that, if implemented correctly, bugs that
  are fixed once can be covered by these tests so that they are not
  accidentally introduced again further down the line. This approach is 
  called regression testing.
- Add codecov plugin to monitor the percentage of code that is covered by
  automated tests. Halfpipe is currently at 2%, which is very low, but
  this will improve over time as we write more testing code.
- Improve granularity of the `--keep` automatic intermediate file deletion
  so that more files are deleted, and add automated tests to verify the
  correctness of file deletion decisions.
- Add `--nipype-resource-monitor` command line option to monitor memory
  usage of the workflow and thus diagnose memory issues
- Re-implement logging code to run in a separate process, reducing the
  burden on the main process. This works by passing a Python
  `multiprocessing.Queue` to all nipype worker processes, so that all
  workers put log messages into the queue using a
  `logging.handlers.QueueHandler`.
  I then implemented a listener that would read from this queue and route
  the log messages to the appropriate log files and the terminal standard
  output.
  I first implemented the listener with `threading`. Threading is a simple
  way to circumvent I/O delays slowing down the main code. With threading,
  the Python interpreter switches between the logging and main threads
  regularly. As a result, when the logging thread waits for the operating
  system to write to disk or to acquire a file lock, the main thread can
  do work in the meantime, and vice versa.
  Very much unexpectedly, this code led to segmentation faults in
  Python. To better diagnose these errors, I refactored the logging
  thread to a separate process, because I thought there may be some
  kind of problem with threading.
  Through this work, I discovered that I was using a different
  `multiprocessing` context for instantiating the logging queue and the
  nipype workers, which caused the segmentation faults. Even though it
  is now unnecessary, I decided to keep the refactored code with
  logging in a separate process, because there are no downsides and I
  had already put the work in.
- Re-phrase some logging messages for improved clarity.
- Refactor command line argument parser and dispatch code to a
  separate module to increase code clarity and readability.
- Refactor spreadsheet loading code to new parse module.
- Print warnings when encountering invalid NIfTI file headers.
- Avoid unnecessary re-runs of preprocessing steps by naming workflows
  using hashes instead of counts. This way adding/removing features
  and settings from the spec.json can be more efficient if
  intermediate results are kept.
- Refactor `--watchdog` code
- Refactor workflow code to use the new collect_boldfiles function to
  decide which functional images to pre-process and which to exclude
  from processing.
  The collect_boldfiles function implements new rules to resolve
  duplicate files. If multiple functional images with the same tags are found,
  for example identical subject name, task and run number, only one will
  be included. Ideally, users would delete such duplicate files before
  running Halfpipe, but we also do not want Halfpipe to fail in these
  cases.
  Two heuristic rules are used: 1) Use the longer functional image.
  Usually, the shorter image will be a scan that was aborted due to
  technical issues and had to be repeated. 2) If both images have the
  same number of volumes, the one with the alphabetically last file
  name will be used.

## Maintenance

- Apply pylint code style rules.
- Refactor automated tests to use pytest fixtures.

## Bug fixes

- Log all warning messages but reduce the severity level of warnings
  that are known to be benign.
- Fix custom interfaces MaskCoverage, MergeMask, and others based on
  the Transformer class to not discard the NIfTI header when
  outputting the transformed images
- Fix execution stalling when the logger is unable to acquire a lock
  on the log file. Use the `flufl.lock` package for hard link-based file
  locking, which is more robust on distributed file systems and NFS.
  Add a fallback to regular `fcntl`-based locking if that fails, and
  another fallback to circumvent log file locking entirely, so that
  logs will always be written out no matter what (#10).
- Fix accidentally passing T1w images to fmriprep that don’t have
  corresponding functional images.
- Fix merging multiple exclude.json files when quality control is done
  collaboratively.
- Fix displaying a warning for README and dataset_description.json
  files in BIDS datasets.
- Fix parsing phase encoding direction from user interface to not only
  parse the axis  but also the direction. Before, there was no
  difference between selecting anterior-to-posterior and
  posterior-to-anterior, which is incorrect.
- Fix loading repetition time coded in milliseconds or microseconds
  from NIfTI files (#13).
- Fix error when trying to load repetition time from 3D NIfTI file
  (#12).
- Fix spreadsheet loading with UTF-16 file encoding (#3).
- Fix how missing values are displayed in the user interface when
  checking metadata.
- Fix unnecessary inconsistent setting warnings in the user interface.

