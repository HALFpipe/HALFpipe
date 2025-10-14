# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-

from dataclasses import dataclass
from itertools import cycle

import pandas as pd
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, HorizontalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, DataTable

from ...features.utils.model_conditions_and_contrasts import ContrastTableInputWindow


class AdditionalContrastsCategoricalVariablesTable(Widget):
    """With some exceptions, this is very similar to ModelConditionsAndContrasts class.
    As a future TODO, one can make a abstract class for this and the above mentioned class.
    For now, for more information just look at the ModelConditionsAndContrasts class.
    """

    @dataclass
    class Changed(Message):
        additional_contrasts_categorical_variables_table: "AdditionalContrastsCategoricalVariablesTable"
        value: str

        @property
        def control(self):
            """Alias for self.file_browser."""
            return self.additional_contrasts_categorical_variables_table

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

    # if so, the selection and the table need an update
    condition_values: reactive[list] = reactive([], init=False)

    def __init__(
        self,
        all_possible_conditions: list,
        feature_contrasts_dict: list,
        feature_conditions_list: list,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """The pandas dataframe is to remember all choices even when some images or conditions are turned off.
        This is because when they are turned on, the condition values will be also back.
        The feature_contrasts_dict is used when the widget is created either from read-in (from existing json file) or
        when duplicated.
        The tricky part in this widget is to keep sync between the selection list and the table and on top of  that
        with the images selection list from the upper widget. Also one needs to properly store and recover table values
        on change.
        The all_possible_conditions is a list of all conditions based on the available images (bold) files.
        The feature_contrasts_dict is reference to the list in the ctx.cache!
        """
        super().__init__(id=id, classes=classes)
        self.feature_contrasts_dict = feature_contrasts_dict
        self.feature_conditions_list = feature_conditions_list
        # This means now all possible levels, because if user change subjects to use, then we should get more rows and there
        # should be also memory of the previous choice.
        self.all_possible_conditions = all_possible_conditions
        self.row_dict: dict = {}
        self.update_all_possible_conditions(all_possible_conditions)

    def update_all_possible_conditions(self, all_possible_conditions: list) -> None:
        self.df = pd.DataFrame()
        # This here assign the row incides, so in our case these are all possible values of categorical variables,
        # or in other words the 'levels'.
        self.df["condition"] = all_possible_conditions
        self.df.set_index("condition", inplace=True)
        # if there are dict entries then set defaults
        # if self.feature_contrasts_dict is not None:  # Ensure it is not None
        if self.feature_contrasts_dict != []:
            # convert dict to pandas
            for contrast_dict in self.feature_contrasts_dict:
                #   for row_index in self.df.index:
                for condition_name in contrast_dict["values"]:
                    self.df.loc[condition_name, contrast_dict["name"]] = contrast_dict["values"][condition_name]
            self.table_row_index = dict.fromkeys(list(self.feature_contrasts_dict[0]["values"].keys()))

    def compose(self) -> ComposeResult:
        table = DataTable(zebra_stripes=True, header_height=2, id="contrast_table")
        # to init the table, stupid but nothing else worked
        table.add_column(label="temp", key="temp")
        # first case is used upon duplication or load, here we use the feature_conditions_list to add the rows to table
        if self.feature_conditions_list != []:
            # hence this list reflects already the selected images
            [table.add_row(None, label=o, key=o) for o in self.feature_conditions_list]
        # second case is standard case when a new task based feature is added, now we use all possible conditions
        else:
            [table.add_row(None, label=o, key=o) for o in self.all_possible_conditions]
        table.remove_column("temp")

        table.cursor_type = "column"
        table.zebra_stripes = True

        if self.feature_contrasts_dict != [] or self.feature_conditions_list != []:
            for contrast_dict in self.feature_contrasts_dict:
                table.add_column(contrast_dict["name"], key=contrast_dict["name"])
                for row_key in table.rows:
                    table.update_cell(row_key, contrast_dict["name"], contrast_dict["values"][row_key.value])
        # here this to avoid error
        self.table_row_index = dict.fromkeys(sorted([r.value for r in table.rows]))

        yield HorizontalScroll(
            table,
            id="contrast_table_upper",
        )
        yield Horizontal(
            Button("Add contrast", classes="add_button"),
            Button("Remove contrast", classes="delete_button"),
            Button("Sort table", classes="sort_button"),
            id="button_panel",
        )

    def action_add_column(self):
        """Add column with new contrast values to te table."""

        def add_column(new_column_name: str):  # , new_column_values=None):
            # new_column_name is just the column label
            # is dictionary with the new column values
            table = self.get_widget_by_id("contrast_table")

            if new_column_name is not False:
                table.add_column(new_column_name, default=1, key=new_column_name)
                for row_key in table.rows:
                    table.update_cell(row_key, new_column_name, self.table_row_index[row_key.value])
                    self.df.loc[row_key.value, new_column_name] = self.table_row_index[row_key.value]
            else:
                pass
            self.dump_contrast_values()

        # start with opening of the modal screen
        self.app.push_screen(
            ContrastTableInputWindow(
                table_row_index=self.table_row_index,
                current_col_labels=self.df.columns.values,
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

    @on(Button.Pressed, "AdditionalContrastsCategoricalVariablesTable .add_button")
    async def add_col(self) -> None:
        await self.run_action("add_column()")

    @on(Button.Pressed, "AdditionalContrastsCategoricalVariablesTable .delete_button")
    async def remove_col(self) -> None:
        await self.run_action("remove_column()")

    @on(Button.Pressed, "AdditionalContrastsCategoricalVariablesTable .sort_button")
    async def sort_cols(self) -> None:
        self.sort_by_row_label()

    def sort_by_row_label(self, default: str | None = None):
        """
        Parameters
        ----------
        default : str, optional
            Custom sort type to override the default cycling sort types.
        """
        condition_selection = self.get_widget_by_id("model_conditions_selection")
        groups = [i.value for i in condition_selection._option_to_index.keys()]
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
        else:

            def find_group_index(element):
                return next(i for i, key in enumerate(groups) if element == key)

            sort_function = find_group_index

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

    def dump_contrast_values(self) -> None:
        table = self.get_widget_by_id("contrast_table")
        df_filtered = self.df.loc[sorted([i.value for i in table.rows])]

        #  if self.feature_contrasts_dict is not None:  # Ensure it is not None
        self.feature_contrasts_dict.clear()
        # Iterate over each column in the DataFrame
        for column in df_filtered.columns:
            self.feature_contrasts_dict.append(
                {"type": "t", "name": column, "variable": [self.id[:-15]], "values": df_filtered[column].to_dict()}
            )

        self.feature_conditions_list.clear()
        self.feature_conditions_list.extend(df_filtered.index.values)
        self.post_message(self.Changed(self, self.feature_contrasts_dict))
