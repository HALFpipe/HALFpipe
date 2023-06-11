# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from halfpipe.utils.table import SynchronizedTable


def test_synchronized_table(tmp_path):
    synchronized_table = SynchronizedTable(tmp_path / "report_test.js")

    with synchronized_table:
        synchronized_table.put(
            dict(
                sub="01",
                a=1,
                b=2.34,
                c="text",
                d=False,
            )
        )
        synchronized_table.put(
            dict(
                sub="02",
                a=2,
                b=3.45,
                c="word",
                d=2,
            )
        )
        synchronized_table.put(
            dict(
                sub="03",
                a=2,
                b=False,
                c="word",
                d=2,
            )
        )

        synchronized_table.to_table()
