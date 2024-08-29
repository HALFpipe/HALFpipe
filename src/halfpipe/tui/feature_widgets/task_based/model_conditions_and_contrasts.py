# -*- coding: utf-8 -*-
from itertools import cycle

import pandas as pd
from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, HorizontalScroll, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, SelectionList
from textual.widgets.selection_list import Selection

from ...utils.false_input_warning_screen import FalseInputWarning

cursors = cycle(["column", "row", "cell"])


class ContrastTableInputWindow(ModalScreen[str | None]):
    """Modal screen to capture user's new contrast values."""

    CSS_PATH = ["tcss/contrast_table_input_window.tcss"]

    def __init__(self, table_row_index, current_col_labels) -> None:
        self.table_row_index = table_row_index
        self.current_col_labels = current_col_labels
        #   self.top_parent = top_parent
        super().__init__()

    def compose(self) -> ComposeResult:
        input_elements = []
        for key, value in self.table_row_index.items():
            input_box = Input(
                placeholder="Value",
                value=value,
                name=key,
                classes="input_values",
            )
            label = Label(key)
            label.tooltip = value
            input_elements.append(Horizontal(label, input_box, classes="row_element"))
        yield VerticalScroll(
            Input(placeholder="Specify contrast name", id="contrast_name"),
            *input_elements,
            Grid(
                Button("Ok", classes="ok_button"),
                Button("Cancel", classes="cancel_button"),
                id="button_grid",
            ),
            id="the_window",
        )

    def on_mount(self):
        self.get_widget_by_id("the_window").border_title = "Contrast"

    @on(Button.Pressed, "ContrastTableInputWindow .ok_button")
    def bla(self):
        self._confirm_window()

    @on(Button.Pressed, "ContrastTableInputWindow .cancel_button")
    def cancel_window(self):
        self._cancel_window()

    def key_escape(self):
        self._cancel_window()

    def _confirm_window(self):
        if self.get_widget_by_id("contrast_name").value in self.current_col_labels:
            self.app.push_screen(FalseInputWarning(warning_message="The selected column name already exists"))
        elif self.get_widget_by_id("contrast_name").value == "":
            self.app.push_screen(FalseInputWarning(warning_message="Specify contrast name!"))
        elif any(i.value == "" for i in self.query(".input_values")):
            print([i for i in self.query(".input_values")])
            self.app.push_screen(FalseInputWarning(warning_message="Fill all values!"))
        else:
            for i in self.query(".input_values"):
                self.table_row_index[i.name] = i.value
            self.dismiss(self.get_widget_by_id("contrast_name").value)

    def _cancel_window(self):
        self.dismiss(None)


class ModelConditionsAndContrasts(Widget):
    BORDER_TITLE = "Model conditions & contrast vales"

    BINDINGS = [
        ("a", "add_column", "Add column"),
        ("r", "remove_column", "Add column"),
        ("s", "submit", "Submit"),
    ]

    sort_type_cycle = cycle(
        [
            "alphabetically",
            "reverse_alphabetically",
            "by_group",
            "reverse_by_group",
        ]
    )

    # condition_values: list of the conditions in the selection, this can be changed also externally by other widget
    # if so, the selection and the table need an update
    condition_values: reactive[list] = reactive([], init=False)

    def __init__(self, all_possible_conditions, feature_contrasts_dict=None, **kwargs) -> None:
        """The pandas dataframe is to remember all choices even when some images or conditions are turned off.
        This is because when they are turned on, the condition values will be also back.
        The feature_contrasts_dict is used when the widget is created either from read-in (from existing json file) or
        when duplicated.
        The tricky part in this widget is to keep sync between the selection list and the table and on top of  that
        with the images selection list from the upper widget. Also one needs to properly store and recover table values
        on change.
        """
        super().__init__(**kwargs)
        # self.top_parent = app
        self.feature_contrasts_dict = feature_contrasts_dict

        self.row_dict: dict = {}
        self.update_all_possible_conditions(all_possible_conditions)
        # self.df = pd.DataFrame()
        # self.df["condition"] = all_possible_conditions
        # self.df.set_index("condition", inplace=True)
        # self.default_conditions = []
        # # if there are dict entries then set defaults
        # if self.feature_contrasts_dict != []:
        # # convert dict to pandas
        # for contrast_dict in self.feature_contrasts_dict:
        # #   for row_index in self.df.index:
        # for condition_name in contrast_dict["values"]:
        # self.df.loc[condition_name, contrast_dict["name"]] = contrast_dict["values"][condition_name]

        # self.default_conditions = self.feature_contrasts_dict[0]["values"].keys()
        # self.table_row_index = dict.fromkeys(list(self.feature_contrasts_dict[0]["values"].keys()))

    def update_all_possible_conditions(self, all_possible_conditions):
        # self.row_dict: dict = {}
        self.df = pd.DataFrame()
        self.df["condition"] = all_possible_conditions
        self.df.set_index("condition", inplace=True)
        self.default_conditions = []
        # if there are dict entries then set defaults
        if self.feature_contrasts_dict != []:
            # convert dict to pandas
            for contrast_dict in self.feature_contrasts_dict:
                #   for row_index in self.df.index:
                for condition_name in contrast_dict["values"]:
                    self.df.loc[condition_name, contrast_dict["name"]] = contrast_dict["values"][condition_name]

            self.default_conditions = self.feature_contrasts_dict[0]["values"].keys()
            self.table_row_index = dict.fromkeys(list(self.feature_contrasts_dict[0]["values"].keys()))

    def watch_condition_values(self) -> None:
        self.update_condition_selection()

    def compose(self) -> ComposeResult:
        yield SelectionList[str](
            *[Selection(condition, condition, initial_state=True, id=condition) for condition in self.default_conditions],
            id="model_conditions_selection",
        )
        yield HorizontalScroll(
            DataTable(zebra_stripes=True, header_height=2, id="contrast_table"),
            id="contrast_table_upper",
        )
        yield Horizontal(
            Button("Add contrast values", classes="add_button"),
            Button("Remove contrast values", classes="delete_button"),
            Button("Sort table", classes="sort_button"),
            id="button_panel",
        )

    def on_mount(self) -> None:
        self.get_widget_by_id("contrast_table_upper").border_title = "Table of Contrast Values"
        table = self.query_one(DataTable)
        # to init the table, stupid but nothing else worked
        table.add_column(label="temp", key="temp")
        [table.add_row(None, label=o, key=o) for o in self.default_conditions]
        table.remove_column("temp")

        table.cursor_type = next(cursors)
        table.zebra_stripes = True
        # read table defaults if there are some
        if self.feature_contrasts_dict is not None:
            for contrast_dict in self.feature_contrasts_dict:
                table.add_column(contrast_dict["name"], key=contrast_dict["name"])
                for row_key in table.rows:
                    table.update_cell(row_key, contrast_dict["name"], contrast_dict["values"][row_key.value])

    #       self._update_row_dict()

    @on(SelectionList.SelectedChanged, "#model_conditions_selection")
    def update_table(self) -> None:
        """When the selection is changed, the table needs to be updated."""
        table = self.get_widget_by_id("contrast_table")

        row_dict = {}
        for r in table.rows:
            row_dict[r.value] = r

        # if there are more rows in the table than in selection, we need to find which one we need to remove
        if len(self.get_widget_by_id("model_conditions_selection").selected) < len(table.rows):
            out = list(set(row_dict.keys()) - set(self.get_widget_by_id("model_conditions_selection").selected))
            [table.remove_row(row_dict[o]) for o in out]
        # if there are less rows in the table than in selection, we need to find which one we need to add
        elif len(self.get_widget_by_id("model_conditions_selection").selected) > len(table.rows):
            out = list(set(self.get_widget_by_id("model_conditions_selection").selected) - set(row_dict.keys()))
            # for c in table.columns:
            # for r in table.rows:
            # print("1", c.value)
            # print("2", table.get_cell(r, c))
            print(self.df)
            [table.add_row(*self.df.loc[o].values, label=o, key=o) for o in out]

        self.table_row_index = dict.fromkeys(sorted([r.value for r in table.rows]))
        self.sort_by_row_label(default="by_group")
        self.dump_contrast_values()

    def action_add_column(self):
        """Add column with new contrast values to te table."""

        def add_column(new_column_name, new_column_values=None):
            # value is just the column label
            # is dictionary with the new column values
            table = self.get_widget_by_id("contrast_table")

            value = new_column_name
            if new_column_values is not None:
                self.table_row_index = new_column_values

            if value is not None:
                table.add_column(value, default=1, key=value)
                for row_key in table.rows:
                    table.update_cell(row_key, value, self.table_row_index[row_key.value])
                    self.df.loc[row_key.value, value] = self.table_row_index[row_key.value]
            else:
                pass
            self.dump_contrast_values()

        # start with opening of the modal screen
        self.app.push_screen(
            ContrastTableInputWindow(
                table_row_index=self.table_row_index,
                current_col_labels=self.df.columns.values,
                # top_parent=self.top_parent,
            ),
            add_column,
        )

    async def action_remove_column(self):
        table = self.get_widget_by_id("contrast_table")
        if len(table.ordered_columns) != 0:
            row_key, column_key = table.coordinate_to_cell_key(table.cursor_coordinate)
            table.remove_column(column_key)
            self.df = self.df.drop(column_key.value, axis=1)
            self.dump_contrast_values()

    async def action_submit(self):
        self.dump_contrast_values()

    @on(Button.Pressed, "ModelConditionsAndContrasts .add_button")
    async def add_col(self) -> None:
        await self.run_action("add_column()")

    @on(Button.Pressed, "ModelConditionsAndContrasts .delete_button")
    async def remove_col(self) -> None:
        await self.run_action("remove_column()")

    @on(Button.Pressed, "ModelConditionsAndContrasts .sort_button")
    async def sort_cols(self) -> None:
        self.sort_by_row_label()

    def key_c(self):
        table = self.get_widget_by_id("contrast_table")
        table.cursor_type = next(cursors)

    def update_condition_selection(self):
        """When some images are selected/deselected, the condition selection needs to be upgraded
        and accordingly therefore the table.
        """
        conditions = self.condition_values

        condition_selection = self.get_widget_by_id("model_conditions_selection")
        available_conditions = list(condition_selection._option_ids.keys())

        if conditions != []:
            # this is to preserve the wanted order of the conditions
            if len(available_conditions) == 0:
                add_this_condtions = conditions
            else:
                add_this_condtions = list(set(conditions) - set(available_conditions))
                add_this_condtions.sort()

            for key in add_this_condtions:
                condition_selection.add_option(Selection(key, key, initial_state=True, id=key))
            for key in set(available_conditions) - set(conditions):
                condition_selection.remove_option(key)
        else:
            with condition_selection.prevent(SelectionList.SelectedChanged):
                condition_selection.clear_options()

        # now upgrade the table
        self.update_table()
        self.dump_contrast_values()

    def sort_by_row_label(self, default=None):
        condition_selection = self.get_widget_by_id("model_conditions_selection")
        groups = list(condition_selection._option_ids.keys())
        table = self.get_widget_by_id("contrast_table")
        # add this  column for sorting purpose, later it is removed
        table.add_column("condition", key="condition")
        for row_key in table.rows:
            table.update_cell(row_key, "condition", row_key.value)

        if default is None:
            sort_type = next(self.sort_type_cycle)
        else:
            sort_type = default
        if "alphabetically" in sort_type:

            def identity_func(value):
                return value

            sort_function = identity_func
        #   sort_function = lambda condition: condition
        else:

            def find_group_index(element):
                return next(i for i, key in enumerate(groups) if element == key)

            sort_function = find_group_index
        #     sort_function = lambda element: next(i for i, key in enumerate(groups) if element == key)

        if "reverse" in sort_type:
            reverse = True
        else:
            reverse = False

        table.sort(
            "condition",
            key=sort_function,
            reverse=reverse,
        )

        table.remove_column("condition")

    def dump_contrast_values(self):
        table = self.get_widget_by_id("contrast_table")
        df_filtered = self.df.loc[sorted([i.value for i in table.rows])]
        self.feature_contrasts_dict.clear()
        # Iterate over each column in the DataFrame
        for column in df_filtered.columns:
            self.feature_contrasts_dict.append({"type": "t", "name": column, "values": df_filtered[column].to_dict()})
