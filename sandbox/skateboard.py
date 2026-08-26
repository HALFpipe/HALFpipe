#!/usr/bin/env python

import concurrent.futures
import os
import pickle
import sys
from dataclasses import dataclass, field
from pathlib import Path
from shelve import open as open_shelf
from subprocess import check_call, check_output
from typing import Any

import networkx as nx
import nipype.pipeline.engine as pe
import pint
from rich.console import Console
from tqdm.rich import tqdm

ureg = pint.UnitRegistry()
console = Console()

# freesurfer_home = "/scratch/imaging/freesurfer"
# os.environ["FREESURFER_HOME"] = freesurfer_home
# os.environ["SUBJECTS_DIR"] = f"{freesurfer_home}/subjects"
# os.environ["MINC_BIN_DIR"] = f"{freesurfer_home}/mni/bin"
# os.environ["MNI_DATAPATH"] = f"{freesurfer_home}/mni/data"
# os.environ["FUNCTIONALS_DIR"] = f"{freesurfer_home}/sessions"
# os.environ["MNI_DIR"] = f"{freesurfer_home}/mni"
# os.environ["PERL5LIB"] = f"{freesurfer_home}/mni/lib/perl5/5.8.5"
# os.environ["MNI_PERL5LIB"] = f"{freesurfer_home}/mni/lib/perl5/5.8.5"
# os.environ["LOCAL_DIR"] = f"{freesurfer_home}/local"

freesurfer_home = Path(os.environ["FREESURFER_HOME"])

freesurfer_license = """halfpipe@fmri.science
73053
 *C8FMo8yrzcZA
 FSCA7.lDgNIow
 e1n3o06osRFD3qtBRgsTy9f9bQHGOpY/riIUrHoEx5c="""
(freesurfer_home / "license.txt").write_text(freesurfer_license)

# path_parts = os.environ["PATH"].split(":")
# path_parts.append(f"{freesurfer_home}/bin")
# path_parts.append(f"{freesurfer_home}/tktools")
# path_parts.append(f"{freesurfer_home}/mni/bin")
# os.environ["PATH"] = ":".join(path_parts)

# os.environ["FSLDIR"] = os.environ["CONDA_PREFIX"]
# os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"


# def memory_to_bytes(memory: float) -> int:
#     """
#     Convert memory in GB to bytes
#     """
#     return int((memory * ureg.gigabyte).to(ureg.byte).magnitude)


# def systemd_run(command: list[str], input_bytes: bytes, memory: float) -> bytes:
#     """
#     Run a command with systemd-run to isolate it in a transient scope
#     """
#     return check_output(
#         [
#             "systemd-run",
#             "--user",
#             "--scope",
#             "--property=MemoryAccounting=yes",
#             # f"--property=MemoryMax={memory_to_bytes(memory)}",
#             "--quiet",
#             *command,
#         ],
#         input=input_bytes,
#     )


def run_node(node: pe.Node) -> dict:
    function = node.run
    input_bytes = pickle.dumps(function)

    cgroup_arguments = ["-g", f"memory:{node.fullname}"]

    check_call(["cgcreate", *cgroup_arguments])

    output_bytes = check_output(["cgexec", *cgroup_arguments, sys.executable, "-m", "run_node"], input=input_bytes)
    output = pickle.loads(output_bytes)

    check_call(["cgdelete", *cgroup_arguments])

    return output


def check_result(node: pe.Node, output: dict[str, Any]) -> None:
    error = output.get("error", None)
    if error is not None:
        raise error

    observed = (output["memory_peak"] * ureg.byte).to(ureg.gigabyte).magnitude
    predicted = node.mem_gb

    if observed > predicted:
        message = f"Node {node.fullname} exceeded memory limit: Observed {observed:.2f} GB, predicted {predicted:.2f} GB"
        console.print(message, style="red on white")

    with Path("/work/charite/notebooks/25/10/memory_usage.txt").open("a") as file_handle:
        file_handle.write(f"{node.fullname}\t{node.n_procs}\t{output['memory_peak']}\n")


@dataclass(order=True, frozen=True, eq=True)
class Job:
    memory: float
    processors: int
    node_index: int


@dataclass
class Skateboard:
    graph: nx.DiGraph

    memory: float
    processors: int

    nodes: list[pe.Node] = field(default_factory=list)
    in_degrees: dict[int, int] = field(default_factory=dict)
    ready: list[Job] = field(default_factory=list)

    def __post_init__(self):
        self.nodes.extend(self.graph)
        for node_index, node in enumerate(self.nodes):
            node.index = node_index
            self.in_degrees[node_index] = self.graph.in_degree(node)

    def update(self) -> None:
        for node_index, in_degree in list(self.in_degrees.items()):
            if in_degree > 0:  # Not ready
                continue

            del self.in_degrees[node_index]

            node = self.nodes[node_index]
            job = Job(processors=node.n_procs, memory=node.mem_gb, node_index=node_index)

            self.ready.append(job)
        self.ready.sort()

    def loop(self) -> None:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=32)

        futures: dict[concurrent.futures.Future, Job] = dict()
        available_memory = self.memory
        available_processors = self.processors
        self.update()

        progress_bar = tqdm(total=len(self.nodes), unit="node", options=dict(console=console), leave=False)

        with progress_bar, executor:
            while self.ready or futures:
                # Submit ready jobs that fit resource constraints
                for job in self.ready.copy():
                    memory = job.memory
                    if memory > self.memory:
                        memory = self.memory  # Cap to max memory
                    if memory > available_memory or job.processors > available_processors:
                        continue  # Not enough resources
                    future = executor.submit(run_node, self.nodes[job.node_index])
                    futures[future] = job
                    available_memory -= job.memory
                    available_processors -= job.processors
                    self.ready.remove(job)

                # Wait for at least one job to complete
                done, _ = concurrent.futures.wait(futures.keys(), return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    progress_bar.update(1)

                    exception = future.exception()
                    if exception is not None:
                        raise exception

                    job = futures.pop(future)
                    node = self.nodes[job.node_index]
                    check_result(node, future.result())

                    # Update in-degrees of successors
                    for successor in self.graph.successors(node):
                        self.in_degrees[successor.index] -= 1

                    available_memory += job.memory
                    available_processors += job.processors
                if done:
                    self.update()


if __name__ == "__main__":
    graphs = open_shelf(sys.argv[1], flag="r")
    # chunks = list(graphs.keys())
    graph = graphs[sys.argv[2]]
    s = Skateboard(graph=graph, memory=30.0, processors=32)
    s.loop()
