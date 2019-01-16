Welcome to the mindandbrain/pipeline!
=====================================

``mindandbrain/pipeline`` is a Docker container for fast, accurate, and 
reproducible analysis of functional magnetic imaging data.
 
It uses `fmriprep <https://fmriprep.readthedocs.io/>`_ for preprocessing, 
and `FSL <http://fsl.fmrib.ox.ac.uk/>`_ for statistics. 

You can install it by running:

::

  docker pull mindandbrain/pipeline

Then, it can be run from the terminal with the following command:

::

  docker run -it -v /:/ext mindandbrain/pipeline

Unpacking this command, docker run tells the docker engine to start the 
container, ``-it`` means that the container can get input/output from the terminal, 
and ``-v /:/ext`` tells the docker engine to make your file system ``/`` available to 
the container at the path ``/ext``. 
This is necessary so that image data on your computer can be accessed. 

Shortly after starting the container, the command line interface appears. 
This interface will ask you a series of questions that will determine how 
data processing will be performed. First comes the working directory, where 
all intermediate and output files of the pipeline will be saved.

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/7c62b15091fb4fee5771d7ca7b76632d278785bb/static/image_workdir.png

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

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/7c62b15091fb4fee5771d7ca7b76632d278785bb/static/image_anatomical.png

Next, the the functional scans are specified. The pipeline separates the input 
for resting state data and task data, because the statistical analyses are 
different. 

First comes resting state. Although only one anatomical scan is allowed for each 
subject, multiple functional scans are allowed. In our example, the participants 
were scanned on two days, resulting in the scans ``subject_01_day_1.nii.gz`` 
and ``subject_01_day_2.nii.gz``. Here, we not only replace the subject name with 
a ``*``, but also the day/run name with a ``?``:

::

  /home/mindandbrain/data/rest/*_rest_?.nii.gz

The container handles the rest.

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/7c62b15091fb4fee5771d7ca7b76632d278785bb/static/image_functionaldata.png

Once resting state data is specified, the pipeline will ask some additional 
questions about the analyses that will be performed. For resting state, 
these are seed connectivity and dual regression. 

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

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/7c62b15091fb4fee5771d7ca7b76632d278785bb/static/image_fsl3column.png

Taken together, here is the entire procedure to specify the functional imaging 
data:

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/7c62b15091fb4fee5771d7ca7b76632d278785bb/static/image_functional.png

After specifying the functional scans, some general parameters for preprocessing 
need to be set:  

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/7c62b15091fb4fee5771d7ca7b76632d278785bb/static/image_preprocessingparams.png

Finally, the statistical analyses across subjects needs to be specified. 
For this, a CSV-file needs to be prepared. In one column the container 
expects the same subject names as contained in the file names (i.e., the ``*`` wildcard part). If multiple groups should be 
compared, another column is expected to contain the group names for each subject. 

.. image:: https://raw.githubusercontent.com/mindandbrain/pipeline/7c62b15091fb4fee5771d7ca7b76632d278785bb/static/image_groupstats.png

After specifying all this, your inputs are saved to the file ``pipeline.json`` in
the working directory specified previously. Then, the processing and analysis of
data will begin.

Have fun!
