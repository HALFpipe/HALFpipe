import numpy as np
from scipy.io import loadmat

def _flatten(x):
    if isinstance(x, np.ndarray):
        return _flatten(x[0])
    return x

def parse_condition_files(files, format = "FSL 3-column"):
    conditions = dict()
    for subject, value0 in files.items():
        conditions[subject] = dict()
        for run, value1 in value0.items():
            conditions[subject][run] = dict()
            for condition, value2 in value1.items():
                if format == "SPM multiple conditions":
                    data = None
                    try:
                        data = loadmat(value2)
                    except:
                        pass
                
                    if data is not None:
                        durations_ = np.squeeze(data["durations"])
                        onsets_ = np.squeeze(data["onsets"])
                        for i, name in enumerate(data["names"]):
                            name_ = _flatten(name)
                            conditions[subject][run][name_] = {"onsets": np.ravel(onsets_[i]).tolist(), "durations": np.ravel(durations_[i]).tolist()}
                    
                if format == "FSL 3-column":
                    data = np.loadtxt(value2)
                    conditions[subject][run][condition] = {"onsets": data[:, 0].tolist(), \
                        "durations": data[:, 1].tolist()}
    
    return conditions