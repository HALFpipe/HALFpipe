import os
import pickle
import sys
from contextlib import redirect_stdout
from io import StringIO

from cgroups import Cgroup

os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"

capture = StringIO()
with redirect_stdout(capture):
    input_bytes = sys.stdin.buffer.read()
    function = pickle.loads(input_bytes)

    cg = Cgroup()

    with cg:
        output = dict()
        try:
            output["result"] = function()
        except Exception as exception:
            output["error"] = exception

    output["memory_peak"] = cg.memory_peak

output["stdout"] = capture.getvalue()

output_bytes = pickle.dumps(output)
sys.stdout.buffer.write(output_bytes)
