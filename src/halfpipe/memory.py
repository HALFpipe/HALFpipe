# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

import pint
import psutil

ureg = pint.UnitRegistry()


def limit_from_file(file_name: Path) -> Optional[int]:
    try:
        with open(file_name, "r") as file_pointer:
            return int(file_pointer.read())
    except (OSError, IOError, ValueError):
        return None


def cgroup_memory_limit():
    # translated from
    # https://github.com/openjdk/jdk/blob/jdk-17+18/src/hotspot/os/linux/cgroupSubsystem_linux.cpp

    proc_cgroups = Path("/proc/cgroups")
    proc_self_cgroup = Path("/proc/self/cgroup")
    proc_self_mountinfo = Path("/proc/self/mountinfo")

    # determine_type
    cg_infos: dict[str, dict] = dict(memory=dict(), cpuset=dict(), cpu=dict(), cpuacct=dict())

    # Read /proc/cgroups so as to be able to distinguish cgroups v2 vs cgroups v1.
    try:
        with open(proc_cgroups, "r") as cgroups_file_pointer:
            cgroups_lines = cgroups_file_pointer.readlines()
    except (OSError, IOError):
        return
    for p in cgroups_lines:
        m = re.fullmatch(r"(?P<name>\w+)\s(?P<hierarchy_id>\d+)\s\d+\s(?P<enabled>\d+)", p.strip())
        if m is None:
            continue
        name = m.group("name")
        hierarchy_id = int(m.group("hierarchy_id"))
        enabled = int(m.group("enabled"))
        if name in cg_infos:
            cg_infos[name] = dict(
                name=name,
                hierarchy_id=hierarchy_id,
                enabled=(enabled == 1),
            )

    is_cgroups_v2 = all(cg_info.get("hierarchy_id") == 0 for cg_info in cg_infos.values())
    all_controllers_enabled = all(cg_info.get("enabled") is True for cg_info in cg_infos.values())

    if not all_controllers_enabled:
        return

    # Read /proc/self/cgroup and determine:
    #   - the cgroup path for cgroups v2 or
    #   - on a cgroups v1 system, collect info for mapping
    #     the host mount point to the local one via /proc/self/mountinfo below.
    try:
        with open(proc_self_cgroup, "r") as cgroup_file_pointer:
            cgroup_lines = cgroup_file_pointer.readlines()
    except (OSError, IOError):
        return
    for p in cgroup_lines:
        m = re.fullmatch(
            r"(?P<hierarchy_id>\d+):(?P<controllers>[^:]*):(?P<cgroup_path>.+)",
            p.strip(),
        )
        if m is None:
            continue
        hierarchy_id = int(m.group("hierarchy_id"))
        controllers = m.group("controllers").split(",")
        cgroup_path = m.group("cgroup_path")
        if not is_cgroups_v2:
            for controller in controllers:
                if controller in cg_infos:
                    cg_infos[controller]["cgroup_path"] = cgroup_path
        else:
            for cg_info in cg_infos.values():
                cg_info["cgroup_path"] = cgroup_path

    # Find various mount points by reading /proc/self/mountinfo
    try:
        with open(proc_self_mountinfo, "r") as mountinfo_file_pointer:
            mountinfo_lines = mountinfo_file_pointer.readlines()
    except (OSError, IOError):
        return
    for p in mountinfo_lines:
        m = re.fullmatch(
            r"\d+\s\d+\s\d+:\d+\s(?P<root>[^\s]+)\s(?P<mount_point>[^\s]+)\s[^-]+-\s(?P<fs_type>[^\s]+)\s[^\s]+\s(?P<cgroups>[^\s]+)",
            p.strip(),
        )
        if m is None:
            continue
        root = m.group("root")
        mount_point = m.group("mount_point")
        fs_type = m.group("fs_type")
        cgroups = m.group("cgroups").split(",")
        if not is_cgroups_v2:
            if fs_type != "cgroup":
                continue
            for token in cgroups:
                if token in cg_infos:
                    cg_infos[token]["mount_path"] = mount_point
                    cg_infos[token]["root_mount_path"] = root
        else:
            if fs_type != "cgroup2":
                continue
            for cg_info in cg_infos.values():
                cg_info["mount_path"] = mount_point

    if all(len(cg_info) == 0 for cg_info in cg_infos):
        # Neither cgroup2 nor cgroup filesystems mounted via /proc/self/mountinfo
        # No point in continuing.
        return

    # simplified logic since we only care about memory here
    memory_cgroup = cg_infos["memory"]

    if "mount_path" not in memory_cgroup or "cgroup_path" not in memory_cgroup:
        return

    memory_root_path = Path(memory_cgroup.get("root_mount_path", "") + memory_cgroup.get("mount_path", ""))

    memory_cgroup_path = Path(
        memory_cgroup.get("root_mount_path", "") + memory_cgroup.get("mount_path", "") + memory_cgroup.get("cgroup_path", "")
    )

    memory_cgroups_to_consider = set(
        [
            memory_cgroup_path,
            *memory_cgroup_path.parents,
        ]
    ) - set(memory_root_path.parents)

    if not is_cgroups_v2:
        memory_limit_files = [
            "memory.limit_in_bytes",
            "memory.memsw.limit_in_bytes",
            "memory.soft_limit_in_bytes",
        ]
    else:
        memory_limit_files = [
            "memory.max",
        ]

    memory_limits = set()
    for path in memory_cgroups_to_consider:
        for f in memory_limit_files:
            memory_file_name = path / f
            if memory_file_name.is_file():
                memory_limit = limit_from_file(memory_file_name)
                if isinstance(memory_limit, int) and memory_limit > 0:
                    memory_limits.add(memory_limit)

    if len(memory_limits) > 0:
        return min(memory_limits) * ureg.bytes


def make_process_independent():
    pid = os.getpid()
    if pid > 0:
        try:
            os.setpgid(pid, pid)
        except OSError:
            pass


def ulimit_memory_limit():
    try:
        proc = subprocess.Popen(
            ["bash", "-c", "ulimit -a"],
            preexec_fn=make_process_independent,  # make the process its own process group
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        ulimit_stdout_bytes, _ = proc.communicate()
        ulimit_lines = ulimit_stdout_bytes.decode().splitlines()
    except OSError:
        return

    memory_limit_keys = [
        "max memory size",  # -m bash
        "resident set size",  # -m zsh
        "virtual memory",  # -v bash
        "address space",  # -v zsh
        "data seg size",  # -d
    ]
    memory_limit_re = "(?:" + "|".join(memory_limit_keys) + ")"

    memory_limits = set()
    for p in ulimit_lines:
        m = re.fullmatch(r".*{:s}[^\d]*(?P<limit>\d+)".format(memory_limit_re), p)
        if m is None:
            continue
        limit_in_kilobytes = int(m.group("limit"))
        if limit_in_kilobytes <= 0:
            continue
        memory_limits.add(limit_in_kilobytes)

    if len(memory_limits) > 0:
        return min(memory_limits) * ureg.kilobytes


def available_memory_bytes():
    return psutil.virtual_memory().available * ureg.bytes


def memory_limit() -> float:
    memory_limits = [
        available_memory_bytes(),
        ulimit_memory_limit(),
        cgroup_memory_limit(),
    ]
    memory_limits_in_gigabytes = [float(ml.m_as(ureg.gigabytes)) for ml in memory_limits if ml is not None]

    memory_limit = min(memory_limits_in_gigabytes) * 0.9  # nipype uses 90% of max as a safety precaution

    process = psutil.Process(pid=os.getpid())
    resident_set_size = process.memory_info().rss * ureg.bytes
    memory_limit -= resident_set_size.m_as(ureg.gigabytes)  # subtract memory used by current process

    return memory_limit
