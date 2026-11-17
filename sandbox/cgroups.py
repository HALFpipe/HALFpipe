import re
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Type

proc_cgroups = Path("/proc/cgroups")
proc_self_cgroup = Path("/proc/self/cgroup")
proc_self_mountinfo = Path("/proc/self/mountinfo")


class Cgroup(AbstractContextManager):
    def __init__(self):
        with open(proc_self_mountinfo, "r") as mountinfo_file_pointer:
            mountinfo_lines = mountinfo_file_pointer.readlines()

        for mountinfo_line in mountinfo_lines:
            m = re.fullmatch(
                r"\d+\s\d+\s\d+:\d+\s(?P<root>[^\s]+)\s(?P<mount_point>[^\s]+)\s[^-]+-\s(?P<fs_type>[^\s]+)\s[^\s]+\s(?P<cgroups>[^\s]+)",
                mountinfo_line.strip(),
            )
            if m is None:
                continue
            fs_type = m.group("fs_type")
            if "cgroup" not in fs_type:
                continue
            cgroup_mount_point = Path(m.group("mount_point"))
            break
        else:
            raise RuntimeError("Could not find cgroup mount point")

        with open(proc_self_cgroup, "r") as cgroup_file_handle:
            cgroup_lines = cgroup_file_handle.readlines()

        for cgroup_line in cgroup_lines:
            m = re.fullmatch(r"(?P<id>\d+):(?P<controllers>[^:]*):(?P<path>.+)", cgroup_line.strip())
            if m is None:
                continue
            cgroup_path = cgroup_mount_point / m.group("path").removeprefix("/")
            break
        else:
            raise RuntimeError("Could not determine cgroup path from /proc/self/cgroup")

        self.memory_peak_path = cgroup_path / "memory.peak"
        self.memory_peak: int | None = None

    def __enter__(self) -> None:
        self.memory_peak_path.write_text("0\n")

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.memory_peak = int(self.memory_peak_path.read_text().strip())
