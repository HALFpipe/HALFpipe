# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


from abc import ABC, abstractmethod
from argparse import Action, ArgumentParser, Namespace
from typing import Any, Callable, Iterable, Sequence


class Command(ABC):
    @abstractmethod
    def setup(self, add_parser: Callable[[str], ArgumentParser]):
        raise NotImplementedError()

    @abstractmethod
    def run(self, arguments: Namespace):
        raise NotImplementedError()


class AppendObjectAction(Action):
    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str,
        key: str,
        nargs: int | str | None = None,
        const: Any | None = None,
        default: Any | None = None,
        type: Callable[[str], Any] | None = None,
        choices: Iterable[Any] | None = None,
        required: bool = False,
        help: str | None = None,
        metavar: str | tuple[str, ...] | None = None,
    ) -> None:
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(
            option_strings,
            dest,
            nargs=1,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )
        self.key = key

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        objects = getattr(namespace, self.dest, None)
        if objects is None:
            objects = list()

        objects.append(
            {
                self.key: values,
            }
        )

        setattr(namespace, self.dest, objects)


class ObjectSetAttributeAction(Action):
    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str,
        nargs: int | str | None = None,
        const: Any | None = None,
        default: Any | None = None,
        type: Callable[[str], Any] | None = None,
        choices: Iterable[Any] | None = None,
        required: bool = False,
        help: str | None = None,
        metavar: str | tuple[str, ...] | None = None,
    ) -> None:
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(
            option_strings,
            dest,
            nargs=1,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )
