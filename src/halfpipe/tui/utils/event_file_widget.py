# -*- coding: utf-8 -*-


from dataclasses import dataclass

from rich.text import Text
from textual import on
from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button

from .file_pattern_steps import (
    AddAtlasImageStep,
    AddBinarySeedMapStep,
    AddSpatialMapStep,
    MatEventsStep,
    TsvEventsStep,
    TxtEventsStep,
)
from .non_bids_file_itemization import FileItem
from .selection_modal import SelectionModal


class FilePanelTemplate(Widget):
    file_pattern_counter = 0
    class_name = "AtlasFilePanel"
    id_string = "atlas_file_panel"
    file_item_id_base = "atlas_file_pattern_"
    the_class = None
    pattern_class = AddAtlasImageStep
    current_file_pattern_id = None
    value: reactive[bool] = reactive(None, init=False)
    # cache: reactive[dict] = reactive(ctx.cache)

    @dataclass
    class FileItemIsDeleted(Message):
        file_panel: Widget
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.file_panel

    @dataclass
    class Changed(Message):
        file_panel: Widget
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.file_panel

    # @dataclass
    # class CacheChanged(Message):
    #     atlas_file_panel: "AtlasFilePanel"
    #     value: str
    #
    #     @property
    #     def control(self):
    #         """Alias for self.file_browser."""
    #         return self.atlas_file_panel

    def __init__(self, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        type(self).the_class = self.__class__  # Sets the_class at the class level
        self.the_app = self.app
        # print("wwwwwwwwwwwwwwwwwwwwwwwwwwww on init", self.app.walk_children())
        # print("self._screen_stacksself._screen_stacksself._screen_stacks", self.app._screen_stacks["_default"])

    #          self.current_atlas_file_pattern_id = None

    def callback_func(self, message_dict):
        info_string = Text("")
        for key in message_dict:
            # print("kkkkkkkkkkkkk", message_dict[key], key)
            # if there is only one item, we do not separate items on new lines
            # print("lllllllllllllllllllllllllll len(message_dict[key])", len(message_dict[key]))
            if len(message_dict[key]) <= 1:
                # print(
                #     "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii am i here?",
                #     (len(key) + len(message_dict[key]) + 3),
                #     len(key),
                #     len(message_dict[key]),
                # )
                sep_char = ""
                separ_line = "-" * (len(key) + len(message_dict[key][0]) + 3)
            else:
                sep_char = "\n"
                separ_line = "-" * (max([len(s) for s in [key] + message_dict[key]]) + 3)
            info_string += Text(key + ": " + sep_char, style="bold green") + Text(
                " ".join(message_dict[key]) + separ_line + "\n", style="white"
            )

        self.callback_message = info_string

    #    self.value = info_string

    def watch_value(self) -> None:
        self.post_message(self.Changed(self, self.value))

    # def watch_cache(self) -> None:
    #     print('cccccccccccccccccccahce chaaaaaaaaaaaaaaaaaaaaaaahned')
    #     self.post_message(self.CacheChanged(self, self.cache))

    def compose(self):
        yield VerticalScroll(Button("Add", id="add_file_button"), id=self.id_string)

    @on(Button.Pressed, "#add_file_button")
    async def _on_button_add_file_item_pressed(self):
        await self.add_file_item_pressed()

    async def add_file_item_pressed(self):
        await self.create_file_item(load_object=None)

    async def create_file_item(self, load_object=None, message_dict=None):
        async def mount_file_item_widget():
            the_file_item = FileItem(
                id=self.file_item_id_base + str(self.the_class.file_pattern_counter),
                classes="file_patterns",
                pattern_class=self.pattern_class(app=self.app, callback=self.callback_func),
            )
            # regular FileItem mount when user clicks "Add" and creates the file pattern
            await self.get_widget_by_id(self.id_string).mount(the_file_item)
            print("--------------- mmmmmmmmmmmmmmmmmmmmmmmmounting in:::: mount_file_item_widget")
            self.current_file_pattern_id = self.file_item_id_base + str(self.the_class.file_pattern_counter)

            self.the_class.file_pattern_counter += 1
            self.refresh()

        if load_object is None:
            await mount_file_item_widget()
        else:
            await self.get_widget_by_id(self.id_string).mount(
                FileItem(
                    id=self.file_item_id_base + str(self.the_class.file_pattern_counter),
                    classes="file_patterns",
                    load_object=load_object,
                    message_dict=message_dict,
                    # pattern_class=self.pattern_class(),
                )
            )
            # print("--------------- mmmmmmmmmmmmmmmmmmmmmmmmounting in::::
            # async def create_file_item(self, load_object=None)")
            self.current_file_pattern_id = self.file_item_id_base + str(self.the_class.file_pattern_counter)
            self.the_class.file_pattern_counter += 1
        return self.current_file_pattern_id

    def on_mount(self):
        # use first event file panel widget to make copies for the newly created one
        if self.app.walk_children(self.the_class) != []:
            first_file_panel_widget = self.app.walk_children(self.the_class)[0]
            # only use if it is not the first one!
            if first_file_panel_widget != self:
                print("*******************************am i creating fileitems???????????????")
                for file_item_widget in first_file_panel_widget.walk_children(FileItem):
                    # mounting FileItems when a new Feature is added, this basically copies FileItems from the
                    # very first Feature
                    self.get_widget_by_id(self.id_string).mount(
                        FileItem(
                            id=file_item_widget.id,
                            classes="file_patterns",
                            load_object=file_item_widget.get_pattern_match_results,
                            callback_message=file_item_widget.get_callback_message,
                        )
                    )
                    print("------------ file_item_widget. get_callback_message", file_item_widget.get_callback_message)
                    print("--------------- mmmmmmmmmmmmmmmmmmmmmmmmounting in:::: on_mount")

    @on(FileItem.IsDeleted)
    async def _on_file_item_is_deleted(self, message):
        message.control.remove()
        # print("vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv******", message)
        self.post_message(self.FileItemIsDeleted(self, message.control.id))

    @on(FileItem.IsFinished)
    @on(FileItem.PathPatternChanged)
    async def _on_update_all_instances(self, event):
        self.value = event.value
        print("************************** what is the event value?", event.value)
        # creating copies to all feature tasks
        # the one that was is the latest one, create new instances
        # print('self._screen_stacksself._screen_stacksself._screen_stacks', self.app._screen_stacks)
        # print(
        #     "222self._screen_stacksself._screen_stacksself._screen_stacks",
        #     self.app._screen_stacks["_default"][0].walk_children(),
        # )

        print("aaaaaaaaaaaat least heeeeeeeeeeeereeeeeeeee?", event.control.id, "-----", self.current_file_pattern_id)
        print(
            "******************************** compare these two: event/control/id == self/current_file_pattern_id",
            event.control.id,
            " === ",
            self.current_file_pattern_id,
        )
        if event.control.id == self.current_file_pattern_id and event.value["file_pattern"] != "":
            # loop through the all existing event file panels
            print("vvvvvvvvvvvvvvv self.app.walk_children(self.the_class)", self.app.walk_children(self.the_class))
            print("222 vvvvvvvvvvvvvvv self.app.walk_children(self.the_class)", self.app.walk_children())
            print("333 vvvvvvvvvvvvvvv self.app.walk_children(self.the_class)", self.the_app.walk_children())
            #
            # print('self.the_class-self.the_class-self.the_class', self.the_class)
            #
            print(
                "******************************** the loop goes over this "
                "self.app._screen_stacks[_default][0].walk_children((self.the_class))",
                self.app._screen_stacks["_default"][0].walk_children((self.the_class)),
            )
            for w in self.app._screen_stacks["_default"][0].walk_children((self.the_class)):
                # create new fileitem in every other EventFilePanel
                print("******************************** this is the w: ", w)
                print("iiiiiiiiiiiiiiiiiam i getting hereeeeeeeeeeeee????? self.the_class", self.the_class)
                print("******************************** this is the self: ", self)
                if w != self:
                    # print(
                    #     "******************************** is w self? if no i see this (we have 2 different widgets of the
                    #     same type but in different features)"
                    # )
                    file_items_ids_in_other_file_panel = [
                        other_file_item_widget.id for other_file_item_widget in w.walk_children(FileItem)
                    ]
                    print("******************************** walk the w: ", w.walk_children(FileItem))
                    # id does not exist, mount new FileItem
                    print(
                        "iiiiiiiiiiiiiiiiiiiiiiiiiii ds event.control.id not in file_items_ids_in_other_event_file_panel",
                        event.control.id,
                        " ::: ",
                        file_items_ids_in_other_file_panel,
                    )
                    print(
                        "********************************* we are going to try to mount these: "
                        "file_items_ids_in_other_file_panel",
                        file_items_ids_in_other_file_panel,
                    )
                    print("********************************* if this is not in the list event.control.id", event.control.id)
                    if event.control.id not in file_items_ids_in_other_file_panel:
                        await w.get_widget_by_id(self.id_string).mount(
                            FileItem(
                                id=event.control.id,
                                classes="file_patterns",
                                load_object=event.control.get_pattern_match_results,
                                callback_message=event.control.get_callback_message,
                            )
                        )
                        print(
                            "*****************",
                            event.control.id,
                            event.control.get_pattern_match_results,
                            event.control.get_callback_message,
                        )
                        print("cccccccccccccccccccccccccccccccccccccccccccccccccccc", event.control.get_callback_message)
                        print("--------------- mmmmmmmmmmmmmmmmmmmmmmmmounting in:::: _on_update_all_instances")


class EventFilePanel(FilePanelTemplate):
    class_name = "EventFilePanel"
    id_string = "event_file_panel"
    file_item_id_base = "event_file_pattern_"
    pattern_class = None

    async def add_file_item_pressed(self):
        options = {
            "spm": "SPM multiple conditions",
            "fsl": "FSL 3-column",
            "bids": "BIDS TSV",
        }
        choice = await self.app.push_screen_wait(
            SelectionModal(
                title="Event file type specification",
                instructions="Specify the event file type",
                options=options,
                id="event_files_type_modal",
            )
        )
        options_class_map = {"spm": MatEventsStep, "fsl": TxtEventsStep, "bids": TsvEventsStep}
        self.pattern_class = options_class_map[choice]
        await self.create_file_item(load_object=None)


class AtlasFilePanel(FilePanelTemplate):
    class_name = "AtlasFilePanel"
    id_string = "atlas_file_panel"
    file_item_id_base = "atlas_file_pattern_"
    pattern_class = AddAtlasImageStep


class SeedMapFilePanel(FilePanelTemplate):
    class_name = "SeedMapFilePanel"
    id_string = "seed_map_file_panel"
    file_item_id_base = "seed_map_file_pattern_"
    pattern_class = AddBinarySeedMapStep


class SpatialMapFilePanel(FilePanelTemplate):
    class_name = "SpatialMapFilePanel"
    id_string = "spatial_map_file_panel"
    file_item_id_base = "spatial_map_file_pattern_"
    pattern_class = AddSpatialMapStep
