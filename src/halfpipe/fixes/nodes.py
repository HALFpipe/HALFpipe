# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

from collections import defaultdict
from copy import deepcopy

import nipype.pipeline.engine as pe
from nipype.interfaces.base import InterfaceResult, Undefined, isdefined, traits
from nipype.pipeline.engine.utils import (
    evaluate_connect_function,
    load_resultfile,
    save_resultfile,
)
from nipype.utils.misc import str2bool

from ..logging import logger


class Node(pe.Node):
    _got_inputs: bool

    def __init__(
        self,
        interface,
        name: str,
        keep: bool = False,
        allow_missing_input_source: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(interface, name, **kwargs)
        self.keep: bool = keep
        self.allow_missing_input_source: bool = allow_missing_input_source

    def _get_inputs(self):
        """
        Retrieve inputs from pointers to results files.
        This mechanism can be easily extended/replaced to retrieve data from
        other data sources (e.g., XNAT, HTTP, etc.,.)
        """
        if self._got_inputs:  # Inputs cached
            return

        if not self.input_source:  # No previous nodes
            self._got_inputs = True
            return

        prev_results = defaultdict(list)
        for key, info in list(self.input_source.items()):
            prev_results[info[0]].append((key, info[1]))

        logger.debug(
            '[Node] Setting %d connected inputs of node "%s" from %d previous nodes.',
            len(self.input_source),
            self.name,
            len(prev_results),
        )

        for results_fname, connections in list(prev_results.items()):
            outputs = None
            try:
                outputs = load_resultfile(results_fname).outputs
            except AttributeError as e:
                logger.critical("%s", e)
            except FileNotFoundError as e:
                if self.allow_missing_input_source:
                    logger.warning(
                        f'Missing input file "{results_fname}". '
                        "This may indicate that errors occurred during previous processing steps.",
                        exc_info=e,
                    )
                else:
                    raise

            if outputs is None:
                if self.allow_missing_input_source:
                    continue
                else:
                    raise RuntimeError(
                        """\
    Error populating the inputs of node "%s": the results file of the source node \
    (%s) does not contain any outputs."""
                        % (self.name, results_fname)
                    )

            for key, conn in connections:
                output_value = Undefined
                if isinstance(conn, tuple):
                    value = getattr(outputs, conn[0])
                    if isdefined(value):
                        output_value = evaluate_connect_function(conn[1], conn[2], value)
                else:
                    output_name = conn
                    try:
                        output_value = outputs.trait_get()[output_name]
                    except AttributeError:
                        output_value = outputs.dictcopy()[output_name]
                    logger.debug("output: %s", output_name)

                try:
                    self.set_input(key, deepcopy(output_value))
                except traits.TraitError as e:
                    msg = (
                        e.args[0],
                        "",
                        "Error setting node input:",
                        "Node: %s" % self.name,
                        "input: %s" % key,
                        "results_file: %s" % results_fname,
                        "value: %s" % str(output_value),
                    )
                    e.args = ("\n".join(msg),)
                    raise

        # Successfully set inputs
        self._got_inputs = True


class MapNode(pe.MapNode, Node):
    def __init__(
        self,
        interface,
        iterfield,
        name: str,
        allow_undefined_iterfield: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(interface=interface, iterfield=iterfield, name=name, **kwargs)
        self.allow_undefined_iterfield: bool = allow_undefined_iterfield

    def _make_empty_results(self):
        finalresult = InterfaceResult(interface=[], runtime=[], provenance=[], inputs=[], outputs=self.outputs)
        if self.outputs:
            assert self.config is not None
            for key, _ in list(self.outputs.items()):
                rm_extra = self.config["execution"]["remove_unnecessary_outputs"]
                if str2bool(rm_extra) and self.needed_outputs:
                    if key not in self.needed_outputs:
                        continue
                    setattr(finalresult.outputs, key, list())

        return finalresult

    def _run_interface(self, execute=True, updatehash=False):
        cwd = self.output_dir()

        if self.allow_undefined_iterfield:
            has_undefined_iterfield = False

            for iterfield in self.iterfield:
                assert isinstance(iterfield, str)
                if not isdefined(getattr(self.inputs, iterfield)):
                    has_undefined_iterfield = True

            if has_undefined_iterfield:
                result = self._make_empty_results()
                save_resultfile(result, cwd, self.name, rebase=False)
                return result

        super()._run_interface(execute=execute, updatehash=updatehash)
