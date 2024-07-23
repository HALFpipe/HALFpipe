# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from abc import ABC, abstractmethod

from ...model.file.base import File


class Loader(ABC):
    @abstractmethod
    def fill(self, fileobj: File, key: str) -> bool:
        pass
