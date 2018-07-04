def ambiguous_match(string, pattern, wildcards):
    for k in wildcards:
        assert len(k) == 1
        
    o, u = _ambiguous_match(string, pattern, wildcards)
    
    for v in o:
        for k in wildcards:
            if k + "_final" in v:
                del v[k + "_final"]
            if len(o) > 1:
                if not k + "_contains" in v:
                    v[k + "_contains"] = None
    
    return o

def _ambiguous_match(string, pattern, wildcards):
    o = [{k : "" for k in wildcards}]
    u = ""
    
    def _append(a, b):
        o = dict()
        
        for k in wildcards:
            if (k + "_final" not in a) and (k + "_final" not in b):
                o[k] = a[k] + b[k]
        
        for k, v in b.items():
            if k not in o:
                o[k] = v
                
        for k, v in a.items():
            if k not in o:
                o[k] = v
                
        return o
    
    if len(string) > 0 and len(pattern) > 0:
        c = string[0]
        d = pattern[0]
        
        if c == d:
            o, v = _ambiguous_match(string[1:], pattern[1:], wildcards)
            u = c + v
            
            if o is not None:
                for v in o:
                    for k in wildcards:
                        if v[k] != "":
                            v[k + "_final"] = True
            
        elif d in wildcards:
            for v in o:
                v[d] += c
                
            m, mu = _ambiguous_match(string[1:], pattern, wildcards) # continue wildcard
            n, nu = _ambiguous_match(string[1:], pattern[1:], wildcards) # finish wildcard
            
            if m and not n:
                o = [_append(v, w) for v in o for w in m]
            elif n and not m:
                o = [_append(v, w) for v in o for w in n]
            elif n and m: # ambiguous
                om = [_append(v, w) for v in o for w in m]
                on = [_append(v, w) for v in o for w in n]
                for v in om:
                    if d + "_contains" in v:
                        v[d + "_contains"] += [nu]
                    else:
                        v[d + "_contains"] = [nu]
                o = om + on
            else:
                o = None
        else:
            o = None
    elif len(string) == 0 and len(pattern) == 0:
        pass
    else:
        o = None
    return o, u

