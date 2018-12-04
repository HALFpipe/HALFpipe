# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

def flatten(l):
    """
    Flatten a list
    Always returns a list even if the input is not

    :param l: Input list

    """
    if isinstance(l, str):
        return [l]
    else:
        o = []
        for k in l:
            o += flatten(k)
        return o

def transpose(d):
    """
    Transpose a dictionary

    :param d: Input dictionary

    """
    out = dict()
    for key0, value0 in d.items():
        for key1, value1 in value0.items():
            if key1 not in out:
                out[key1] = dict()
            while isinstance(value1, dict) and len(value1) == 1 and "" in value1:
                value1 = value1[""]
            out[key1][key0] = value1
    return out

def lookup(d, subject_id = None, run_id = None, condition_id = None):
    """
    Look up value in three-level dictionary based on three keys

    :param d: Input dictionary
    :param subject_id: Outer key (Default value = None)
    :param run_id: Middle key (Default value = None)
    :param condition_id: Inner key (Default value = None)

    """
    key0 = []
    if isinstance(d, dict) and len(d) == 1 and "" in d:
        key0.append("")
    elif subject_id is None:
        key0 += list(d.keys())
    else:
        key0.append(subject_id)
    
    if not key0[0] in d:
        return None

    e = d[key0[0]]
    
    key1 = []
    if isinstance(e, dict) and len(e) == 1 and "" in e:
        key1.append("")
    elif run_id is None:
        key1 += list(e.keys())
    else:
        key1.append(run_id)
        
    if not key1[0] in e:
        return None

    f = e[key1[0]]
    
    key2 = []
    if isinstance(f, dict) and len(f) == 1 and "" in f:
        key2.append("")
    elif condition_id is None:
        key2 += list(f.keys())
    else:
        key2.append(condition_id)
    
    o = dict()
    for i in key0:
        o[i] = dict()
        for j in key1:
            o[i][j] = dict()
            for k in key2:
                o[i][j][k] = d[i][j][k]
                
    def flatten(dd):
        """
        Flatten a dictionary

        :param dd: Input dictionary

        """
        if isinstance(dd, dict):
            if len(dd) == 1:
                return flatten(next(iter(dd.values())))
            return {k:flatten(v) for k, v in dd.items()}
        return dd
        
    return flatten(o)

