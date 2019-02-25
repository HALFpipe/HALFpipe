Welcome to the mindandbrain/pipeline!
=====================================

``mindandbrain/pipeline`` is a Docker container that facilitates reproducible analysis of fMRI data, including preprocessing, single-subject, and group analysis.
 
It uses `fmriprep <https://fmriprep.readthedocs.io/>`_ for preprocessing, 
and `FSL <http://fsl.fmrib.ox.ac.uk/>`_ for statistics. 

You can install it by running:

::

  docker pull mindandbrain/pipeline

Then, it can be run from the terminal with the following command:

::

  docker run -it -v /:/ext mindandbrain/pipeline
  
Alternatively, one can use singularity to build and run the container, for which we provide two shell scripts (singularity_install.sh and singularity_run.sh). 

Looking at this command in more detail, docker run tells the docker engine to start the 
container, ``-it`` means that the container can get input/output from the terminal, 
and ``-v /:/ext`` tells the docker engine to make your file system ``/`` available to 
the container at the path ``/ext``. 
This is necessary so that image data on your computer can be accessed. 

Shortly after starting the container, the command line interface appears. 
This interface will ask you a series of questions that will determine how 
data processing will be performed. First it asks you for the working directory (needs to already exist), where 
all intermediate and output files of the pipeline will be saved.

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/master/static/image_workdir.png

For the preprocessing of functional data, high-resolution anatomical/structural 
scans are required by `fmriprep <https://fmriprep.readthedocs.io/>`_. 
In our example, the scans are located in the folder /home/mindandbrain/data/t1 
and the files are named as subject_01_t1.nii.gz, subject_02_t1.nii.gz and so on. 
The container needs to know how these files are named, so that it can later 
match the files to other scans of the same subject. 
For this, we take an example file path, such as 

::

  /home/mindandbrain/data/t1/subject_01_t1.nii.gz

We replace only the subject name in the path with a ``*``. This sort of replacement 
is called a wildcard, and allows the container to get all the files that fit the 
pattern of

::

  /home/mindandbrain/data/t1/*_t1.nii.gz

Where ``*`` can be anything.

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/master/static/image_anatomical.png

Note that one can use multiple wildcards in the path when individual data is stored in separate folders. For example

::

  /home/mindandbrain/data/t1/subject_01/subject_01_t1.nii.gz
  
will need to be entered as

::

  /home/mindandbrain/data/t1/*/*_t1.nii.gz

Next, the the functional scans are specified. The pipeline separates the input 
for resting state data and task data, because the analyses options are 
different.

First comes resting state. Although only one anatomical scan is allowed for each 
subject, multiple functional scans are allowed. In the example below, the participants 
were scanned for two runs, resulting in the scans ``subject_01_run_1.nii.gz`` 
and ``subject_01_runs_2.nii.gz``. Here, we not only replace the subject name with 
a ``*``, but also the run name with a ``?``:

::

  /home/mindandbrain/data/rest/*_rest_?.nii.gz

If there is only one run, then the ``?`` should be omitted. 

Now, the container handles the rest. Multiple runs are combined using a 
fixed-effects model.

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/master/static/image_functionaldata.png

Once resting state data is specified, the pipeline will ask some additional 
questions about the analyses that can be performed on the data. For resting state, 
the options are seed connectivity, dual regression using ICA network templates, and correlation matrices constructed from a parcellation template of your choice. ALFF and ReHo are currently calculated automatically.

For task, you will need to specify the experimental conditions/explanatory 
variables. These can be in 
`FSL 3-column format <https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FEAT/FAQ>`_, 
or in `SPM multiple conditions <http://elden.ua.edu/blog/generating-onset-and-duration-mat-file-for-spm-for-fmri-analysis>`_
format. FSL 3-column format means that one text file for each condition, 
each with three columns: ``onset``, ``duration`` and ``strength``. 
The third column is ignored. 
In the SPM format, a MATLAB MAT-file with three fields: ``onsets``, 
``durations`` and ``names`` is expected. 

As the names of the conditions are not in the file itself for the FSL 3-column 
format, these need to be inferred from the filenames. The input prompt allows 
you to specify different input for each subject and each run, but the ``*``- and 
``?``-wildcards can also be omitted if the conditions are the same. The 
filenames should contain the names of the experimental conditions. Then, by 
replacing the condition name with the ``$``-wildcard, the container can infer the 
condition names.

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/master/static/image_fsl3column.png

Taken together, here is the entire procedure to specify the functional imaging 
data:

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/master/static/image_functional.png

After specifying the functional scans, some general parameters for preprocessing 
need to be set:  

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/master/static/image_preprocessingparams.png

Finally, the statistical analyses across subjects needs to be specified. These are
done with a general linear model. If nothing is specified, a one-sample t-test is 
performed. To further specify the model, a CSV-file should be passed.
This is called ``covariates.csv`` in the example.
In this file, one column should contain subject names. These should be the same as 
in the file names (i.e., the ``*`` wildcard part). If multiple groups should be 
compared, another column is expected to contain the group names for each subject. 
The remaining columns are used as covariates and are regressed out. Commonly, variables
such as age, sex or left/right-handedness are used. 

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/master/static/image_groupstats.png

After specifying all this, your inputs are saved to the file ``pipeline.json`` in
the working directory specified previously. Then, the processing and analysis of
data will begin.

Have fun!
