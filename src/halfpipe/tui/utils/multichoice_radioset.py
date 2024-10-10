# -*- coding: utf-8 -*-
#    from _radio_set2 import RadioSet
#    from draggable_modal_screen import DraggableModalScreen
import numpy as np
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.widget import Widget
from textual.widgets import Button, Label, RadioButton

from ._radio_set2 import RadioSet
from .draggable_modal_screen import DraggableModalScreen


class MultipleRadioSet(Widget):
    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
        horizontal_label_set: None | list = None,
        vertical_label_set: None | list = None,
    ):
        super().__init__(id=id, classes=classes)
        self.horizontal_label_set = (
            horizontal_label_set
            if horizontal_label_set is not None
            else ["h_label1", "h_lab2", "h_long_label3", "4", "h_label5"]
        )
        self.horizontal_label_set[-1] = self.horizontal_label_set[-1] + "  "
        self.vertical_label_set = (
            vertical_label_set if vertical_label_set is not None else ["v_label1", "v_long_label2", "v_label3", "v_label4"]
        )

    def compose(self) -> ComposeResult:
        #     hmax_length = max([len(i) for i in self.horizontal_label_set])
        vmax_length = max([len(i) for i in self.vertical_label_set])
        hmax_vertical_length = 1

        print("beeeeeeeeeeeeeeeeeeeeeeeeefore", self.horizontal_label_set)
        # modify the h labels so that if there is a label on multiple lines, the longest line becomes wrapped with spaces
        for i, h_val in enumerate(self.horizontal_label_set):
            split_label = [h for h in h_val.split("\n")]
            hmax_vertical_length = max([hmax_vertical_length, len(split_label)])
            index_longest_line = np.argmax([len(h) for h in split_label])
            split_label[index_longest_line] = "  " + split_label[index_longest_line] + "  "
            self.horizontal_label_set[i] = "\n".join(split_label)
        print("aaaaaaaaaaaaaaaaaaaaaaaaaaafter", self.horizontal_label_set)

        # with  ScrollableContainer(id='top_container'):
        with Horizontal(id="h_label_container"):
            for h_label in [" " * (vmax_length + 2)] + self.horizontal_label_set:
                this_label = Label(h_label, classes="h_labels")
                # set height of the hlabels to the one with the most lines
                this_label.styles.height = hmax_vertical_length
                yield this_label
        for i, v_label in enumerate(self.vertical_label_set):
            with Horizontal(classes="radio_table_rows"):
                yield Label(v_label + " " * (vmax_length - len(v_label)) + "  ", classes="v_labels")
                with RadioSet(classes="row_radio_sets_" + str(i)):
                    for j, _ in enumerate(self.horizontal_label_set):
                        yield RadioButton(classes="radio_column_" + str(j), value=(j - 1))

    def on_mount(self):
        for i, h_val in enumerate(self.horizontal_label_set):
            for this_radio_button in self.query(".radio_column_" + str(i)):
                # if there is a line break in the label, we count the length of the longest line
                h_val_length = max([len(h) for h in h_val.split("\n")])
                this_radio_button.styles.width = h_val_length + 1
                this_radio_button.styles.content_align = ("center", "middle")

    def get_selections(self):
        selections = {}
        for i, v_val in enumerate(self.vertical_label_set):
            for this_radio_set in self.query(".row_radio_sets_" + str(i)):
                selections[v_val] = this_radio_set._selected
                print("xxxxxxxxxxxxxxxxxxxxxxxx", v_val, ":   ", this_radio_set._selected)
        return selections

    # _selected


class MultipleRadioSetModal(DraggableModalScreen):
    CSS_PATH = ["tcss/confirm.tcss"]

    def __init__(
        self,
        title="Field maps to functional images",
        id: str | None = None,
        classes: str | None = None,
        width=None,
        horizontal_label_set: None | list = None,
        vertical_label_set: None | list = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.title_bar.title = title
        self.horizontal_label_set = (
            horizontal_label_set
            if horizontal_label_set is not None
            else ["h_label1", "h_lab2", "h_long_label3", "4", "h_label5"]
        )
        self.vertical_label_set = (
            vertical_label_set if vertical_label_set is not None else ["v_label1", "v_long_label2", "v_label3", "v_label4"]
        )

    async def on_mount(self) -> None:
        await self.content.mount(
            Label("Assign field maps to functional images:", id="instructions"),
            ScrollableContainer(
                MultipleRadioSet(horizontal_label_set=self.horizontal_label_set, vertical_label_set=self.vertical_label_set),
                id="outer_table_container",
            ),
            Horizontal(Button("OK", id="ok"), classes="button_grid"),
        )
        print("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee self._container_size.width", self._container_size.width)

    # def on_resize(self):
    # if self._container_size.width > 150:
    # outer_table_container = self.get_widget_by_id('outer_table_container')
    # outer_table_container.width = 100
    # print('qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq self._container_size.width', self._container_size.width )
    # #
    #  self.title_bar.query_one(".window_title").styles.width = self._container_size.width

    @on(Button.Pressed, "#ok")
    def ok(self):
        selections = self.query_one(MultipleRadioSet).get_selections()
        print("sssssssselections  ", selections)
        self.dismiss(selections)


class Main(App):
    CSS_PATH = "radio_set_changed.tcss"

    def compose(self):
        yield Button("OK", id="ok")
        yield Button("Mount modal", id="show_modal")
        yield MultipleRadioSet()

    @on(Button.Pressed, "#show_modal")
    def on_button_show_modal_pressed(self):
        self.app.push_screen(
            MultipleRadioSetModal(
                horizontal_label_set=[
                    "h_label1",
                    "h_lab2",
                    "h_long_label3\n_long_label3----\n_long_label3",
                    "4",
                    "h_label5",
                    "h_label5",
                    "4",
                    "h_label5",
                    "h_label5",
                    "h_label5",
                ],
                vertical_label_set=["v_label1", "v_long_label2", "v_label3", "v_label4", "v_label222222222222222224"],
            )
        )

    @on(Button.Pressed, "#ok")
    def on_button_pressed(self):
        selections = self.query_one(MultipleRadioSet).get_selections()
        print("sssssssselections  ", selections)


if __name__ == "__main__":
    app = Main()
    app.run()
