# -*- coding: utf-8 -*-

import sys

sys.path.append("/home/tomas/github/HALFpipe/src/")

from rich.text import Text
from textual import events, on
from textual.containers import Container, Grid, HorizontalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from halfpipe.tui.utils.file_browser_modal import FileBrowserModal
from halfpipe.tui.utils.list_of_files_modal import ListOfFiles
from halfpipe.tui.utils.pattern_suggestor import (
    InputWithColoredSuggestions,
    SegmentHighlighting,
    SelectCurrentWithInputAndSegmentHighlighting,
)


# utilities
def evaluate_files(newpathname):
    """
    Function to evaluate how many and what files were found based on the provided file pattern.
    TODO: refine the whole function
    """
    from os import path as op
    from threading import Event

    import inflect

    from halfpipe.ingest.glob import (
        suggestion_match,
        tag_glob,
    )

    class Config:
        fs_root: str = "/"

    def resolve(path) -> str:
        abspath = op.abspath(path)

        fs_root = Config.fs_root

        if not abspath.startswith(fs_root):
            abspath = fs_root + abspath

        return op.normpath(abspath)

    # fix this, the task was not here
    schema_entities = ["subject", "session", "run", "acquisition", "task"]
    #   entity_colors_list = ["ired", "igreen", "imagenta", "icyan"]
    # required_in_path_entities = ["subject"]
    #   required_entities = required_in_path_entities

    dironly = False

    tag_glob_generator = tag_glob(newpathname, schema_entities + ["suggestion"], dironly)

    new_suggestions = set()
    suggestiontempl = op.basename(newpathname)
    filepaths = []
    tagdictlist = []
    _scan_requested_event = Event()

    def _is_candidate(filepath):
        if dironly is True:
            return op.isdir(filepath)
        else:
            return op.isfile(filepath)

    try:
        for filepath, tagdict in tag_glob_generator:
            if "suggestion" in tagdict and len(tagdict["suggestion"]) > 0:
                suggestionstr = suggestion_match.sub(tagdict["suggestion"], suggestiontempl)
                if op.isdir(filepath):
                    suggestionstr = op.join(suggestionstr, "")  # add trailing slash
                new_suggestions.add(suggestionstr)

            elif _is_candidate(filepath):
                filepaths.append(filepath)
                tagdictlist.append(tagdict)

            if _scan_requested_event.is_set():
                break
    except ValueError as e:
        print("Error scanning files: %s", e)

    tagsetdict = {}
    if len(tagdictlist) > 0:
        tagsetdict = {k: set(dic[k] for dic in tagdictlist) for k in tagdictlist[0] if k != "suggestion"}

    # temporary fix
    if "subject" not in newpathname:
        filepaths = []
        tagdictlist = []

    nfile = len(filepaths)

    #   has_all_required_entities = all(entity in tagsetdict for entity in required_entities)

    print("filepaths", filepaths)

    print("tagdictlist", tagdictlist)
    p = inflect.engine()
    value = p.inflect(f"Found {nfile} plural('file', {nfile})")

    if len(tagsetdict) > 0:
        value += " "
        value += "for"
        value += " "
        tagmessages = [p.inflect(f"{len(v)} plural('{k}', {len(v)})") for k, v in tagsetdict.items()]
        value += p.join(tagmessages)

    return value, filepaths


# Classes
class ColorButton(Button):
    """Sets current highlighting color by pressing the button."""

    def __init__(self, color: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color
        self.styles.background = color

    async def on_click(self, event: events.Click) -> None:
        path_widget = self.app.get_widget_by_id("input_prompt")
        path_widget.highlight_color = self.color


class PathPatternBuilder(ModalScreen):
    """
    Serves for creating a file pattern to search for e.g. T1 files.
    Consists of color button to switch between the highlight colors, the string itself,
    some edit buttons and Ok/Cancel buttons.
    The key component is the InputWithColoredSuggestions which allows the string highlighting
    and supports also pattern suggestions.
    """

    def __init__(
        self,
        path: str,
        highlight_colors=None,
        labels=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.path = path
        self.highlight_colors = ["red", "green", "blue", "yellow", "magenta"] if highlight_colors is None else highlight_colors
        self.labels = ["subject", "Session", "Run", "Acquisition", "task"] if labels is None else labels
        self.pattern_match_results = {"file_pattern": self.path, "message": "Found 0 files.", "files": []}
        self.original_value = path

    def compose(self):
        colors_and_labels = dict(zip(self.highlight_colors, self.labels, strict=False))
        yield Grid(
            *[
                ColorButton(label=item[1], color=item[0], id="button_" + item[1], classes="color_buttons")
                for item in colors_and_labels.items()
            ],
            classes="panels",
        )
        yield HorizontalScroll(
            InputWithColoredSuggestions(
                [(Text(self.path), self.path)],
                prompt_default=self.path,
                colors_and_labels=colors_and_labels,
                top_parent=self,
                id="path_widget",
            ),
            id="path_widget_container",
        )
        yield Grid(
            Button("Browse", id="browse_button"),
            Button("Reset highlights", id="reset_button"),
            Button("Reset all", id="reset_all"),
            Button("Submit", id="submit_button"),
            classes="panels",
        )
        with Container(id="feedback_and_confirm_panel"):
            yield Container(
                Static("Found 0 files.", id="feedback"),
                Button("👁", id="show_button", classes="icon_buttons"),
                id="feedback_container",
            )
            yield Container(Button("OK", id="ok_button"), Button("Cancel", id="cancel_button"), id="testtt")

    def on_mount(self):
        # active button at start
        self.activate_pressed_button("button_" + self.labels[0])

    def deactivate_pressed_button(self):
        """Fade the button when inactive."""
        if self.active_button_id is not None:
            self.get_widget_by_id(self.active_button_id).remove_class("activated")

    def activate_pressed_button(self, _id):
        """Light up the button when inactive."""
        clicked_color_button = self.get_widget_by_id(_id)
        clicked_color_button.add_class("activated")
        self.active_button_id = _id

    @on(Button.Pressed, "#browse_button")
    def open_browse_window(self):
        self.app.push_screen(FileBrowserModal(), self.update_input)

    def update_input(self, selected_path: str) -> None:
        """Update the Prompt value."""
        if selected_path is not None:
            self.get_widget_by_id("input_prompt").value = str(selected_path)
            self.get_widget_by_id("input_prompt").original_value = str(selected_path)

    @on(Button.Pressed, "#reset_button")
    def reset_highlights(self):
        self.get_widget_by_id("input_prompt").reset_highlights()

    @on(Button.Pressed, "#reset_all")
    def reset_all(self):
        self.get_widget_by_id("input_prompt").reset_all()

    @on(Button.Pressed, "#submit_button")
    def submit_highlights(self):
        self.get_widget_by_id("input_prompt").submit_path()

    @on(InputWithColoredSuggestions.Changed)
    @on(SegmentHighlighting.Submitted)
    @on(SegmentHighlighting.Changed)
    def _segment_highlighting_submitted(self, event):
        """Update the pattern_match_results dictionary based on the output of various methods."""
        if isinstance(event.value, Text):
            event_value = event.value.plain
            match_feedback_message, filepaths = evaluate_files(event_value)
            self.path = event_value
        else:
            match_feedback_message, filepaths = evaluate_files(event.value)
            self.path = event.value

        highlights = self.get_widget_by_id("input_prompt").current_highlights
        self.get_widget_by_id("feedback").update(match_feedback_message)
        self.get_widget_by_id("show_button").tooltip = match_feedback_message
        self.pattern_match_results = {
            "file_pattern": Text(self.path, spans=highlights),
            "message": match_feedback_message,
            "files": filepaths,
        }
        # Change outine from red to green if some files were found.
        if len(self.pattern_match_results["files"]) > 0:
            self.query_one(SelectCurrentWithInputAndSegmentHighlighting).styles.outline = ("solid", "green")
        else:
            self.query_one(SelectCurrentWithInputAndSegmentHighlighting).styles.outline = ("solid", "red")

    @on(Button.Pressed, ".color_buttons")
    def activate_and_deactivate_press(self, event: Button.Pressed):
        self.deactivate_pressed_button()
        self.activate_pressed_button(event.button.id)

    @on(Button.Pressed, "#ok_button")
    def _ok(self, event: Button.Pressed):
        self.dismiss(self.pattern_match_results)

    @on(Button.Pressed, "#cancel_button")
    def _close(self, event: Button.Pressed):
        self.dismiss()

    @on(Button.Pressed, "#show_button")
    def _remove_self(self):
        self.app.push_screen(ListOfFiles(self.pattern_match_results))

    async def on_key(self, event: events.Key):
        """Handles keyboard events to move the cursor and toggle highlighting mode."""
        path_widget = self.get_widget_by_id("input_prompt")
        if event.key in ["1", "2", "3", "4", "5"]:
            # Set highlight color based on key pressed.
            index = int(event.key) - 1
            path_widget.highlight_color = self.highlight_colors[index]
            self.deactivate_pressed_button()
            self.activate_pressed_button("button_" + self.labels[index])

    def key_enter(self):
        self.get_widget_by_id("input_prompt").submit_path()

    def key_escape(self):
        self.get_widget_by_id("input_prompt").reset_highlights()
