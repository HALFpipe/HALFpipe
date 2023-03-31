# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

"""

"""
import logging
import os
from operator import attrgetter
from os import path as op
from threading import Event, Thread
from typing import Any, Dict, List, Optional

import inflect

from ....ingest.glob import (
    remove_tag_remainder_match,
    show_tag_suggestion_check,
    suggestion_match,
    tag_glob,
    tag_parse,
    tokenize,
)
from ..file import resolve
from ..keyboard import Key
from ..text import Text, TextElement, TextElementCollection
from ..view import CallableView
from .choice import SingleChoiceInputView
from .text import TextInputView, common_chars

logger = logging.getLogger("halfpipe.ui")
p = inflect.engine()


class NestedTextInputView(TextInputView):
    def __init__(self, parent_view: CallableView, *args, **kwargs):
        self.parent_view = parent_view
        super().__init__(*args, **kwargs)

    def update(self):
        self.parent_view.update()


class NestedSingleChoiceInputView(SingleChoiceInputView):
    def __init__(self, parent_view: CallableView, *args, **kwargs):
        self.parent_view = parent_view
        super().__init__(*args, **kwargs)

    def update(self):
        self.parent_view.update()


class FilePatternInputView(CallableView):
    def __init__(
        self,
        entities: List[str],
        required_entities=[],
        entity_colors_list=["ired", "igreen", "imagenta", "icyan", "iyellow"],
        dironly=False,
        base_path=None,
        **kwargs,
    ):
        super(FilePatternInputView, self).__init__(**kwargs)
        self.text_input_view = NestedTextInputView(
            self,
            base_path,
            tokenizefun=self._tokenize,
            nchr_prepend=1,
            messagefun=self._messagefun,
            forbidden_chars="'\"'",
            maxlen=256,
        )
        self.suggestion_view = NestedSingleChoiceInputView(
            self, [], isVertical=True, addBrackets=False
        )

        self.message: Text = TextElement("")
        self.message_is_dirty = False

        self.matching_files: list[Text] = []
        self.cur_dir = None
        self.cur_dir_files: list[str] = []
        self.dironly = dironly
        self.is_ok = False

        self.entities = entities
        self.required_entities = required_entities
        self.entity_colors_list = entity_colors_list
        self.color_by_tag: Optional[Dict[str, Any]] = None
        self.tag_suggestions: List[Text] = []
        self.is_suggesting_entities = False
        self.tab_pressed = False

        self._scan_thread = None
        self._is_scanning = True
        self._scan_requested_event = Event()
        self._scan_complete_event = Event()

    @property
    def text(self):
        return self.text_input_view.text

    @text.setter
    def text(self, val):
        self._scan_files()
        self.text_input_view.text = val

    def show_message(self, msg):
        if isinstance(msg, Text):
            self.message = msg
        else:
            self.message = self._tokenize(msg, addBrackets=False)
        self.message_is_dirty = True

    def _suggest_entities(self):
        self.matching_files = []

        self.is_suggesting_entities = True
        self._update_suggestion_view(self.tag_suggestions)

    def _suggest_matches(self):
        self.tag_suggestions = []
        self.is_suggesting_entities = False
        self._update_suggestion_view(self.matching_files)

    def _update_suggestion_view(self, options: List[Text]):
        options = sorted(options, key=attrgetter("value"))
        self.suggestion_view.set_options(options)

        self._scan_complete_event.set()
        self.update()

    def _tokenize(self, text, addBrackets=True):
        if addBrackets:
            text = f"[{text}]"

        tokens = tokenize.split(text)
        tokens = [token for token in tokens if token is not None]

        text_element_collection = TextElementCollection()

        for token in tokens:
            color = None

            matchobj = tag_parse.fullmatch(token)
            if matchobj is not None:

                tag_name = matchobj.group("tag_name")
                assert self.color_by_tag is not None
                color = self.color_by_tag.get(tag_name, self.highlightColor)

            text_element_collection.append(TextElement(token, color=color))

        return text_element_collection

    def _messagefun(self):
        return self.message

    def setup(self):
        super(FilePatternInputView, self).setup()

        self.text_input_view.layout = self.layout
        self.text_input_view.setup()

        self.suggestion_view.layout = self.layout
        self.suggestion_view.setup()

        self.color_by_tag = {
            entity: self.layout.color.from_string(color_str)
            for entity, color_str in zip(self.entities, self.entity_colors_list)
        }

    def _before_call(self):
        self.text_input_view._before_call()
        self.text_input_view.isActive = True

        self._scan_thread = Thread(target=self._scan_files_loop)
        self._is_scanning = True
        self._scan_thread.start()

        self._scan_files()

    def _after_call(self):
        self._is_scanning = False
        self._scan_thread.join()
        super()._after_call()

    def _is_ok(self):
        return self.is_ok

    def _getOutput(self):
        if self.text is not None:
            path = str(self.text).strip()
            return resolve(path)

    def _scan_files(self):
        self._scan_requested_event.set()

    def _scan_files_loop(self):
        while self._is_scanning:
            was_requested = self._scan_requested_event.wait(timeout=0.1)
            if was_requested is not True:
                continue  # timeout reached

            # scan was requested
            self._scan_complete_event.clear()
            self._scan_requested_event.clear()

            is_suggestion_done = False

            if self.text is not None:
                text = str(self.text).strip()
                cur_index = self.text_input_view.cur_index

                start_match = show_tag_suggestion_check.match(text[:cur_index])
                if start_match is not None:
                    tag_name = start_match.group("tag_name")
                    newfilter = start_match.group("newfilter")
                    if newfilter is None:
                        newfilter = ""

                    self.tag_suggestions = list()
                    for entity in self.entities:
                        if not entity.startswith(tag_name):
                            continue

                        end_match = remove_tag_remainder_match.match(text[cur_index:])

                        if len(newfilter) > 0:
                            if end_match is not None:
                                end_filter = end_match.group("oldtag")
                                if end_filter is not None:
                                    newfilter += end_filter[:-1]

                        start = start_match.start("newtag")
                        newtext = op.basename(text[:start])

                        newtext += f"{{{entity}{newfilter}}}"

                        if end_match is not None:
                            cur_index += end_match.end("oldtag")

                        newtext += text[cur_index:]

                        self.tag_suggestions.append(
                            self._tokenize(newtext, addBrackets=False)
                        )

                    self._suggest_entities()
                    is_suggestion_done = True

            if self._scan_requested_event.is_set():
                continue

            if self.text is None or len(self.text) == 0:
                pathname = op.join(os.curdir, "")
            else:
                pathname = str(self.text)
                if not op.isabs(pathname):
                    pathname = op.join(os.curdir, pathname)

            newpathname = pathname + "{suggestion:.*}"
            newpathname = resolve(newpathname)
            tag_glob_generator = tag_glob(
                newpathname, self.entities + ["suggestion"], self.dironly
            )

            new_suggestions = set()
            suggestiontempl = op.basename(newpathname)
            filepaths = []
            tagdictlist = []

            def _is_candidate(filepath):
                if self.dironly is True:
                    return op.isdir(filepath)
                else:
                    return op.isfile(filepath)

            try:
                for filepath, tagdict in tag_glob_generator:
                    if "suggestion" in tagdict and len(tagdict["suggestion"]) > 0:
                        suggestionstr = suggestion_match.sub(
                            tagdict["suggestion"], suggestiontempl
                        )
                        if op.isdir(filepath):
                            suggestionstr = op.join(
                                suggestionstr, ""
                            )  # add trailing slash
                        new_suggestions.add(suggestionstr)

                    elif _is_candidate(filepath):
                        filepaths.append(filepath)
                        tagdictlist.append(tagdict)

                    if self._scan_requested_event.is_set():
                        break

            except ValueError as e:
                logger.debug("Error scanning files: %s", e, exc_info=True)
                pass
            except AssertionError as e:
                logger.debug("Error scanning files: %s", e, exc_info=True)
                return

            if self._scan_requested_event.is_set():
                continue

            tagsetdict = {}
            if len(tagdictlist) > 0:
                tagsetdict = {
                    k: set(dic[k] for dic in tagdictlist)
                    for k in tagdictlist[0]
                    if k != "suggestion"
                }

            nfile = len(filepaths)

            has_all_required_entities = all(
                entity in tagsetdict for entity in self.required_entities
            )
            logger.debug(f"has_all_required_entities={has_all_required_entities}")

            if not self.message_is_dirty:
                value = self.message.value
                color = self.message.color

                if nfile == 0:
                    value = ""

                elif has_all_required_entities:
                    color = self.layout.color.iblue
                    value = p.inflect(f"Found {nfile} plural('file', {nfile})")

                    if len(tagsetdict) > 0:
                        value += " "
                        value += "for"
                        value += " "
                        tagmessages = [
                            p.inflect(f"{len(v)} plural('{k}', {len(v)})")
                            for k, v in tagsetdict.items()
                        ]
                        value += p.join(tagmessages)

                else:
                    color = self.layout.color.iyellow
                    value = "Missing"
                    value += " "
                    value += p.join(
                        [
                            f"{{{entity}}}"
                            for entity in self.required_entities
                            if entity not in tagsetdict
                        ]
                    )
                self.message = TextElement(value, color)

            self.message_is_dirty = False

            if nfile > 0 and has_all_required_entities:
                self.is_ok = True
            else:
                self.is_ok = False

            if not is_suggestion_done:
                self.matching_files = [
                    self._tokenize(s, addBrackets=False) for s in new_suggestions
                ]
                self._suggest_matches()

    def _handleKey(self, c):
        cur_text = str(self.text)
        cur_index = self.text_input_view.cur_index

        needs_update = False

        def _enter_suggestion_view():
            nonlocal needs_update

            if not self._scan_complete_event.is_set():
                return

            if self.is_suggesting_entities or len(self.matching_files) > 0:
                self.suggestion_view.isActive = True
                self.text_input_view.isActive = False
                self.suggestion_view._before_call()
                needs_update = True

        def _exit_suggestion_view():
            nonlocal needs_update

            self.suggestion_view.offset = 0
            self.suggestion_view.cur_index = None
            self.suggestion_view.isActive = False
            self.text_input_view.isActive = True
            self.text_input_view._before_call()
            needs_update = True

        def _apply_suggestion(selection: str):
            if not self._scan_complete_event.is_set():
                return

            cur_index = self.text_input_view.cur_index

            text = str(self.text)
            new_text = op.join(op.dirname(text[:cur_index]), selection)

            if text != new_text and len(new_text) > len(text):
                self.text = new_text
                self.text_input_view.cur_index = len(self.text)

                return new_text

        if c == Key.Break:
            self.text = None
            self.suggestion_view.set_options([])
            self.isActive = False

        elif (
            self.suggestion_view.isActive and self.suggestion_view.cur_index is not None
        ):
            self.tab_pressed = False

            if c == Key.Up and self.suggestion_view.cur_index == 0:  # exit and discard
                _exit_suggestion_view()

            elif c == Key.Return or c == Key.Right:  # exit and choose
                selection = str(self.suggestion_view._getOutput())

                _apply_suggestion(selection)
                _exit_suggestion_view()

            elif c == Key.Left:
                self.text = op.dirname(str(self.text))

            else:
                self.suggestion_view._handleKey(c)
        else:

            if c == Key.Down:
                _enter_suggestion_view()

            elif c == Key.Tab:
                tab_completion_candidates = []
                if self.is_suggesting_entities:
                    if isinstance(self.tag_suggestions, list):
                        tab_completion_candidates = self.tag_suggestions
                else:
                    if isinstance(self.matching_files, list):
                        tab_completion_candidates = self.matching_files

                if len(tab_completion_candidates) > 0:
                    cc = common_chars(tab_completion_candidates)
                    new_text = _apply_suggestion(cc)
                    if new_text is None:
                        if self.tab_pressed:
                            _enter_suggestion_view()
                        else:
                            self.tab_pressed = True

            elif c == Key.Return:
                if self._is_ok() and self._scan_complete_event.is_set():
                    self.suggestion_view.set_options([])
                    self.suggestion_view.isActive = False
                    self.text_input_view.isActive = False
                    self.isActive = False
                else:
                    logger.debug("Ignoring return key because input is not ok.")

            else:
                if not self.text_input_view.isActive:
                    self.suggestion_view.isActive = False
                    self.text_input_view.isActive = True
                    self.text_input_view._before_call()
                    self.update()
                self.text_input_view._handleKey(c)

            if c != Key.Tab:
                self.tab_pressed = False

        if self.text is not None and str(self.text) != cur_text:
            self.message_is_dirty = False
            self._scan_files()

            needs_update = True

        if cur_index != self.text_input_view.cur_index:
            needs_update = True

        if needs_update:
            self.update()

    def drawAt(self, y):
        if y is not None:
            size: int = 0

            text_input_view_draw_size = self.text_input_view.drawAt(y + size)
            if isinstance(text_input_view_draw_size, int):
                size += text_input_view_draw_size

            suggestion_view_draw_size = self.suggestion_view.drawAt(y + size)
            if isinstance(suggestion_view_draw_size, int):
                size += suggestion_view_draw_size

            self._viewWidth = max(
                self._viewWidth,
                self.text_input_view._viewWidth,
                self.suggestion_view._viewWidth,
            )

            return size
