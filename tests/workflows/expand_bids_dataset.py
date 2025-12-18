import re
import shutil
from pathlib import Path

# from datasets import Dataset

# # this downloads a small fragment of the whole dataset
# dataset = Dataset(
#     name="fibromyalgia",
#     openneuro_id="ds004144",
#     openneuro_url="https://openneuro.org/datasets/ds004144/versions/1.0.2",
#     url="https://github.com/OpenNeuroDatasets/ds004144.git",
#     paths=[
#         "sub-002/anat/sub-002_T1w.nii.gz",
#         "sub-002/anat/sub-002_T1w.json",
#         "sub-002/func/sub-002_task-epr_bold.nii.gz",
#         "sub-002/func/sub-002_task-epr_bold.json",
#         "sub-002/func/sub-002_task-epr_events.tsv",
#         "sub-002/func/sub-002_task-rest_bold.nii.gz",
#         "sub-002/func/sub-002_task-rest_bold.json",
#     ],
# )


def expand_bids_dataset(
    base_dataset_dir: Path,
    output_dataset_dir: Path,
    base_subject: str = "sub-002",
    n_subjects: int = 3,
    n_sessions: int = 1,
):
    """
    Expand a base BIDS dataset into multiple subjects/sessions,
    keeping:
      - ALL functional data
      - ONLY T1w anatomical data
    """

    base_subject_dir = base_dataset_dir / base_subject
    if not base_subject_dir.exists():
        raise ValueError(f"Base subject directory not found: {base_subject_dir}")

    # Copy dataset-level files
    output_dataset_dir.mkdir(parents=True, exist_ok=True)
    for item in base_dataset_dir.iterdir():
        if item.name.startswith("sub-"):
            continue
        if item.is_file():
            shutil.copy(item, output_dataset_dir / item.name)

    for subj_idx in range(1, n_subjects + 1):
        new_sub = f"sub-{subj_idx:03d}"

        for ses_idx in range(1, n_sessions + 1):
            ses = f"ses-{ses_idx:04d}"

            for src_file in base_subject_dir.rglob("*"):
                if src_file.is_dir():
                    continue

                rel = src_file.relative_to(base_subject_dir)
                datatype = rel.parts[0]  # anat / func / fmap / etc.
                fname = src_file.name

                # ---------- FILTER ----------
                if datatype == "anat":
                    if "_T1w" not in fname:
                        continue
                elif datatype == "func":
                    pass  # keep all func
                else:
                    continue  # drop fmap, dwi, etc. (change if needed)

                # ---------- OUTPUT DIR ----------
                out_dir = output_dataset_dir / new_sub / ses / datatype
                out_dir.mkdir(parents=True, exist_ok=True)

                # ---------- RENAME ----------
                new_fname = fname.replace(base_subject, new_sub)

                if "ses-" not in new_fname:
                    new_fname = re.sub(
                        rf"({new_sub})_",
                        rf"\1_{ses}_",
                        new_fname,
                    )

                shutil.copy(src_file, out_dir / new_fname)


#
# tmp_path='./tessst'
# # dataset.download(tmp_path)
#
# expand_bids_dataset(
#     base_dataset_dir=Path(tmp_path),
#     output_dataset_dir=Path('./modified'),
#     base_subject="sub-002",
#     n_subjects=3,
#     n_sessions=3,
# )
#
#
