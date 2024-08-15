# -*- coding: utf-8 -*-

import sys

sys.path.append("/home/tomas/github/HALFpipe/src/")


from textual import on
from textual.app import App
from textual.containers import Horizontal, HorizontalScroll, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Static

from halfpipe.tui.utils.list_of_files_modal import ListOfFiles
from halfpipe.tui.utils.path_pattern_builder import PathPatternBuilder

from ..utils.context import ctx
from ..utils.false_input_warning_screen import SimpleMessageModal

# TODO
# For bids, this is automatic message
# Found 0 field map image files
# after putting BOLD images, i need this message
# Check repetition time values
# 18 images - 0.75 seconds
# 36 images - 2.0 seconds
# Proceed with these values?
# [Yes] [No]
# Specify repetition time in seconds
# [0]
# There are 4 SummarySteps: FilePatternSummaryStep, AnatSummaryStep, BoldSummaryStep, FmapSummaryStep
# AnatSummaryStep > BoldSummaryStep > get_post_func_steps > FmapSummaryStep > END
# get_post_func_steps: will now be checked in different tab
# def get_post_func_steps(this_next_step_type: Optional[Type[Step]]) -> Type[Step]:
# class DummyScansStep(Step):
# class CheckBoldSliceTimingStep(CheckMetadataStep):
# class CheckBoldSliceEncodingDirectionStep(CheckMetadataStep):
# class DoSliceTimingStep(YesNoStep):

# entity_colors = {
# "sub": "red",
# "ses": "green",
# "run": "magenta",
# "task": "cyan",
# "dir": "yellow",
# "condition": "orange",
# "desc": "orange",
# "acq": "cyan",
# "echo": "orange",
# }


# class FilePatternStep:

# entity_display_aliases = entity_display_aliases
# header_str = None
# ask_if_missing_entities: List[str] = list()
# required_in_path_entities: List[str] = list()

# def __init__(self,
# filetype_str= "file",
# filedict: Dict[str, str] = dict(),
# schema: Union[Type[BaseFileSchema], Type[FileSchema]] = FileSchema,
# ctx=None,
# path='',
# ):

# self.filetype_str = filetype_str
# self.filedict = filedict
# self.schema = schema
# self.entities = get_schema_entities(schema)  # Assumes a function to extract schema entities
# self.path = path
# self.ctx = ctx

# self.fileobj: File | None = None

# schema_entities = get_schema_entities(self.schema)
# schema_entities = [entity for entity in reversed(entities) if entity in schema_entities]  # keep order
# # convert to display
# self.schema_entities = [
# (self.entity_display_aliases[entity] if entity in self.entity_display_aliases else entity)
# for entity in schema_entities
# ]

# # need original entities for this
# self.entity_colors_list = [entity_colors[entity] for entity in schema_entities]

# self.required_entities = [
# *self.ask_if_missing_entities,
# *self.required_in_path_entities,
# ]

# def _transform_extension(self, ext):
# return ext

# @property
# def get_entities(self):
# return self.schema_entities
# @property
# def get_entity_colors_list(self):
# return self.entity_colors_list
# @property
# def get_required_entities(self):
# return self.required_entities

# def push_path_to_context_obj(self, path):
# inv = {alias: entity for entity, alias in self.entity_display_aliases.items()}

# i = 0
# _path = ""
# for match in tag_parse.finditer(path):
# groupdict = match.groupdict()
# if groupdict.get("tag_name") in inv:
# _path += path[i : match.start("tag_name")]
# _path += inv[match.group("tag_name")]
# i = match.end("tag_name")

# _path += path[i:]
# path = _path

# # create file obj
# filedict = {**self.filedict, "path": path, "tags": {}}
# _, ext = split_ext(path)
# filedict["extension"] = self._transform_extension(ext)

# loadresult = self.schema().load(filedict)
# assert isinstance(loadresult, File), "Invalid schema load result"
# self.fileobj = loadresult

# self.ctx.spec.files.append(self.fileobj)


# class AnatStep(FilePatternStep):

# required_in_path_entities = ["subject"]
# header_str = "Specify anatomical/structural data"

# def __init__(self, ctx=None, path=''):
# super().__init__(
# filetype_str="T1-weighted image", filedict={"datatype": "anat", "suffix": "T1w"}, schema=T1wFileSchema, ctx=ctx,
# path=path
# )


######################################


class FileItem(Widget):
    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
        delete_button=True,
        title="",
        pattern_class=None,
        id_key="",
        **kwargs,
    ) -> None:
        """ """
        super().__init__(id=id, classes=classes, **kwargs)
        # dictionary for results from the PathPatternBuilder
        self.pattern_match_results = {"file_pattern": "", "message": "Found 0 files.", "files": []}
        self.delete_button = delete_button
        self.title = pattern_class.header_str
        self.pattern_class = pattern_class
        print(
            "FileItem ssssssssssssssssssssssssssssssssssssssssssssssssssss",
            self.pattern_class.get_entities,
            self.pattern_class.get_entity_colors_list,
            self.pattern_class.get_required_entities,
        )
        print("FileItem aaaaaaaaaaaaaaaa", pattern_class.header_str)
        if self.pattern_class.next_step_type is not None:
            print("hhhhhhhhhhhhhhhhhhhhhhhhhhhas nextt steppp")
            self.pattern_class.callback = self.callback_func
        self.pattern_class.id_key = id

    def callback_func(self, message_dict):
        info_string = ""
        for key in message_dict:
            info_string += key + ": " + " ".join(message_dict[key]) + "\n"

        self.callback_message = info_string

    def compose(self):
        yield HorizontalScroll(Static("Edit to enter the file pattern", id="static_file_pattern"))
        with Horizontal(id="icon_buttons_container"):
            if self.pattern_class.callback is not None:
                yield Button(" ℹ", id="info_button", classes="icon_buttons")
            yield Button("🖌", id="edit_button", classes="icon_buttons")
            yield Button("👁", id="show_button", classes="icon_buttons")
            if self.delete_button:
                yield Button("❌", id="delete_button", classes="icon_buttons")

    def on_mount(self) -> None:
        self.get_widget_by_id("edit_button").tooltip = "Edit"
        if self.delete_button:
            self.get_widget_by_id("delete_button").tooltip = "Delete"
        self.app.push_screen(
            PathPatternBuilder(
                #  path="/home/tomas/github/ds002785_v2/sub-0001/func/sub-0001_task-emomatching_acq-seq_bold.nii.gz",
                #  path="/home/tomas/github/ds005115/sub-01/ses-01/fmap/sub-01_ses-01_phasediff.nii.gz",
                path="/home/tomas/github/ds005115/sub-01/ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz",
                title=self.title,
                highlight_colors=self.pattern_class.get_entity_colors_list,
                labels=self.pattern_class.get_entities,
            ),
            self._update_file_pattern,
        )

    @on(Button.Pressed, "#edit_button")
    def _on_edit_button_pressed(self):
        """
        Opens modal for selecting the search file pattern.
        The results from this modal goes then to _update_file_pattern function.
        """
        self.app.push_screen(
            PathPatternBuilder(
                # path="/home/tomas/github/ds002785_v2/sub-0001/func/sub-0001_task-emomatching_acq-seq_bold.nii.gz",
                path="/home/tomas/github/ds005115/sub-01/ses-01/fmap/sub-01_ses-01_phasediff.nii.gz",
                # path="/home/tomas/github/ds005115/sub-01/ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz",
                title=self.title,
            ),
            self._update_file_pattern,
        )

    def _update_file_pattern(self, pattern_match_results):
        """Update various variables based on the results from the PathPatternBuilder"""
        self.pattern_match_results = pattern_match_results
        # Update the static label using the file pattern.
        self.get_widget_by_id("static_file_pattern").update(pattern_match_results["file_pattern"])
        # Tooltip telling us how many files were  found.
        self.get_widget_by_id("show_button").tooltip = pattern_match_results["message"]
        # If 0 files were found, the border is red, otherwise green.
        if len(pattern_match_results["files"]) > 0:
            self.styles.border = ("solid", "green")
        else:
            self.styles.border = ("solid", "red")

        # try to push to ctx
        print("iiiiiiiiiiiiiiiiiiiiiiiiii", pattern_match_results["file_pattern"])
        # obj = AnatStep(ctx=self.app.ctx, path=pattern_match_results["file_pattern"].plain)
        # obj.setup()
        # fix this because sometimes this can be just ordinary string
        if isinstance(pattern_match_results["file_pattern"], str):
            self.pattern_class.push_path_to_context_obj(path=pattern_match_results["file_pattern"])
        else:
            self.pattern_class.push_path_to_context_obj(path=pattern_match_results["file_pattern"].plain)

    @on(Button.Pressed, "#delete_button")
    def _on_delete_button_pressed(self):
        """Remove the file pattern item."""
        ctx.cache.pop(self.id)
        self.remove()

    @on(Button.Pressed, "#show_button")
    def _on_show_button_pressed(self):
        """Shows a modal with the list of files found using the given pattern."""
        self.app.push_screen(ListOfFiles(self.pattern_match_results))

    @on(Button.Pressed, "#info_button")
    def _on_info_button_pressed(self):
        """Shows a modal with the list of files found using the given pattern."""
        print("iiiiiiiiiiiiiiiiiiiiiiiiiiiiiii", self.callback_message)
        self.app.push_screen(SimpleMessageModal(self.callback_message, title="Meta information"))


class Main(App):
    CSS_PATH = ["./tcss/path_segment_highlighter2.tcss"]

    def compose(self):
        with VerticalScroll(id="test_container"):
            yield Button("Add", id="add_button")

    def on_mount(self) -> None:
        self.get_widget_by_id("add_button").tooltip = "Add new file pattern"

    @on(Button.Pressed, "#add_button")
    def _add_file_time(self):
        self.get_widget_by_id("test_container").mount(FileItem(classes="file_patterns"))
        self.refresh()


if __name__ == "__main__":
    app = Main()
    app.run()
