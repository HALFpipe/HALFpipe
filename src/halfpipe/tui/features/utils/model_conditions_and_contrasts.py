# -*- coding: utf-8 -*-
from itertools import cycle

import pandas as pd
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, HorizontalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Label, SelectionList
from textual.widgets.selection_list import Selection

from ...general_widgets.draggable_modal_screen import DraggableModalScreen
from ...specialized_widgets.confirm_screen import Confirm

cursors = cycle(["column", "row", "cell"])


class ContrastTableInputWindow(DraggableModalScreen):
    """
    A modal window for setting contrast values through a user interface.

    This class provides a modal window that allows users to input contrast
    name and values for the contrast table.

    Attributes
    ----------
    CSS_PATH : list[str]
        List containing paths to the CSS files for styling the window.
    table_row_index : dict[str, str]
        A dictionary representing the row index of the contrast table,
        where keys are condition names and values are their initial values.
    current_col_labels : list[str]
        A list of current column labels in the contrast table.

    Methods
    -------
    on_mount :
        Mounts the input widgets onto the window when the window is displayed.
    ok :
        Confirms the input values and performs validation checks.
    cancel_window :
        Cancels the window and dismisses it without saving user input.
    key_escape :
        Cancels the window and dismisses it when the escape key is pressed.
    _confirm_window :
        Validates the user inputs and updates the table row index if inputs are valid.
    _cancel_window :
        Dismisses the window without saving any user inputs.
    """

    CSS_PATH = ["tcss/contrast_table_input_window.tcss"]

    def __init__(self, table_row_index, current_col_labels) -> None:
        """
        Initializes the ContrastTableInputWindow instance.

        Parameters
        ----------
        table_row_index : dict[str, str]
            A dictionary representing the row index of the contrast table,
            where keys are condition names and values are their initial values.
        current_col_labels : list[str]
            A list of current column labels in the contrast table.
        """
        self.table_row_index = table_row_index
        self.current_col_labels = current_col_labels
        super().__init__()
        self.title_bar.title = "Set contrast values"

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
        self.widgets_to_mount = [
            Input(placeholder="Specify contrast name", id="contrast_name"),
            *input_elements,
            Horizontal(
                Button("Ok", classes="ok_button"),
                Button("Cancel", classes="cancel_button"),
                id="button_panel",
            ),
        ]

    def on_mount(self):
        self.content.mount(*self.widgets_to_mount)

    @on(Button.Pressed, "ContrastTableInputWindow .ok_button")
    def ok(self):
        """
        Confirms the input values and checks for column name conflicts.

        This method is called when the "Ok" button is pressed. It triggers
        the `_confirm_window`.
        """
        self._confirm_window()

    @on(Button.Pressed, "ContrastTableInputWindow .cancel_button")
    def cancel_window(self):
        """
        Cancels the window and dismisses it without saving user input.

        This method is called when the "Cancel" button is pressed. It
        triggers the `_cancel_window` method to dismiss the modal.
        """
        self._cancel_window()

    def key_escape(self):
        """
        Cancels the window and dismisses it when the escape key is pressed.

        This method is called when the escape key is pressed. It triggers
        the `_cancel_window` method to dismiss the modal.
        """
        self._cancel_window()

    def _confirm_window(self):
        """
        Validates the user inputs and updates the table row index if inputs are valid.

        This method checks if the contrast name is unique and if all input
        values are filled. If the inputs are valid, it updates the
        `table_row_index` and dismisses the modal. Otherwise, it displays
        an error message.
        """
        if self.get_widget_by_id("contrast_name").value in self.current_col_labels:
            self.app.push_screen(
                Confirm(
                    "The selected column name already exists",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Existing name",
                    classes="confirm_error",
                )
            )
        elif self.get_widget_by_id("contrast_name").value == "":
            self.app.push_screen(
                Confirm(
                    "Specify contrast name!",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Existing name",
                    classes="confirm_error",
                )
            )
        elif any(i.value == "" for i in self.query(".input_values")):
            self.app.push_screen(
                Confirm(
                    "Fill all values!",
                    left_button_text=False,
                    right_button_text="OK",
                    right_button_variant="default",
                    title="Existing name",
                    classes="confirm_error",
                )
            )
        else:
            for i in self.query(".input_values"):
                self.table_row_index[i.name] = i.value
            self.dismiss(self.get_widget_by_id("contrast_name").value)

    def _cancel_window(self):
        """
        Dismisses the window without saving any user inputs.

        This method dismisses the modal window without making any changes.
        """
        self.dismiss(False)


class ModelConditionsAndContrasts(Widget):
    """
    Manages condition and contrast values for a dataset.

    This class provides a widget for managing condition values and contrast
    values for a given dataset. It allows users to add, remove, and update
    these values dynamically. It synchronizes selections between the
    condition list and the associated data table, ensuring consistency.

    Attributes
    ----------
    BORDER_TITLE : str
        Title of the border for the contrast values table.
    BINDINGS : list[tuple[str, str, str]]
        Key bindings for the add, remove, and submit actions.
    sort_type_cycle : cycle[str]
        An iterator that cycles through sorting types: alphabetically,
        reverse_alphabetically, by_group, and reverse_by_group.
    condition_values : reactive[list[str]]
        List of conditions in the selection, which can be modified externally
        and requires updates to the selection and table.
    df : pd.DataFrame
        A pandas DataFrame to store and manage condition and contrast values.
    feature_contrasts_dict : list[dict]
        A list of dictionaries, where each dictionary represents a contrast
        and contains its name and values.
    feature_conditions_list : list[str]
        A list of conditions that are currently selected.
    all_possible_conditions : list[str]
        A list of all possible conditions based on the available images.
    table_row_index : dict[str, str]
        A dictionary representing the row index of the contrast table,
        where keys are condition names and values are their initial values.

    Methods
    -------
    update_all_possible_conditions :
        Updates the possible conditions in the data table.
    watch_condition_values :
        Watches the condition values and triggers an update when they change.
    compose :
        Composes the widget elements.
    on_mount :
        Sets up the table and other widget components on mounting.
    update_table :
        Updates the data table based on changes in the selection list.
    set_heights :
        Adjusts the height of the widget and its components.
    action_add_column :
        Adds a new column with contrast values to the data table.
    action_remove_column :
        Removes the currently selected column from the data table.
    add_col :
        Button event that triggers the action_add_column method.
    remove_col :
        Button event that triggers the action_remove_column method.
    sort_cols :
        Button event that triggers sorting of the table by row labels.
    update_condition_selection :
        Updates the condition selection based on selected images.
    sort_by_row_label :
        Sorts the table by row labels.
    dump_contrast_values :
        Dumps the contrast values to the `feature_contrasts_dict`.
    """

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

    def __init__(
        self,
        all_possible_conditions: list,
        feature_contrasts_dict: list,
        feature_conditions_list: list,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Initializes the ModelConditionsAndContrasts widget.

        Parameters
        ----------
        all_possible_conditions : list[str]
            A list of all possible conditions based on the available images.
        feature_contrasts_dict : list[dict]
            A list of dictionaries, where each dictionary represents a contrast
            and contains its name and values.
        feature_conditions_list : list[str]
            A list of conditions that are currently selected.
        id : str, optional
            The ID of the widget, by default None.
        classes : str, optional
            CSS classes for the widget, by default None.

        Notes
        -----
        The pandas dataframe is to remember all choices even when some images or conditions are turned off.
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
        self.all_possible_conditions = all_possible_conditions
        self.row_dict: dict = {}
        self.update_all_possible_conditions(all_possible_conditions)

    def update_all_possible_conditions(self, all_possible_conditions: list) -> None:
        """
        Updates the possible conditions in the data table.

        This method updates the class attribute DataFrame 'df' with the new possible
        conditions and sets default conditions if a feature contrasts
        dictionary is provided.

        Parameters
        ----------
        all_possible_conditions : list[str]
            A list of all possible conditions.
        """
        self.df = pd.DataFrame()
        self.df["condition"] = all_possible_conditions
        self.df.set_index("condition", inplace=True)
        if self.feature_contrasts_dict != []:
            # convert dict to pandas
            for contrast_dict in self.feature_contrasts_dict:
                #   for row_index in self.df.index:
                for condition_name in contrast_dict["values"]:
                    self.df.loc[condition_name, contrast_dict["name"]] = contrast_dict["values"][condition_name]
            self.table_row_index = dict.fromkeys(list(self.feature_contrasts_dict[0]["values"].keys()))

    def watch_condition_values(self) -> None:
        """
        Watches the condition values and triggers an update when they change.

        This method is called when the `condition_values` reactive attribute
        changes. It calls `update_condition_selection` to update the
        selection list and the table.
        """
        self.update_condition_selection()

    def compose(self) -> ComposeResult:
        """
        Composes the widget elements.

        This method defines the layout and components of the widget,
        including the selection list, data table, and control buttons.
        """
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
        # read table defaults if there are some, this put columns into table (on load or on duplication)
        # if self.feature_contrasts_dict is not None:  # Ensure it is not None
        # the "or" is a must, one can make a duplicate from a widget where there are some conditions selections but there are
        # no columns in the table
        if self.feature_contrasts_dict != [] or self.feature_conditions_list != []:
            for contrast_dict in self.feature_contrasts_dict:
                table.add_column(contrast_dict["name"], key=contrast_dict["name"])
                for row_key in table.rows:
                    table.update_cell(row_key, contrast_dict["name"], contrast_dict["values"][row_key.value])
            condition_selection_list = [
                Selection(condition, condition, initial_state=(condition in self.feature_conditions_list), id=condition)
                for condition in self.all_possible_conditions
            ]
        else:
            condition_selection_list = [
                Selection(condition, condition, initial_state=True, id=condition) for condition in self.all_possible_conditions
            ]

        yield SelectionList[str](
            *condition_selection_list,
            id="model_conditions_selection",
        )
        yield HorizontalScroll(
            table,
            id="contrast_table_upper",
        )
        yield Horizontal(
            Button("Add contrast values", classes="add_button", id="add_contrast_values_button"),
            Button("Remove contrast values", classes="delete_button", id="delete_contrast_values_button"),
            Button("Sort table", classes="sort_button"),
            id="button_panel",
        )

    def on_mount(self) -> None:
        """
        This method is called when the widget is mounted. It sets the
        initia; heights of the widget and its components.
        """
        self.set_heights()

    @on(SelectionList.SelectedChanged, "#model_conditions_selection")
    def update_table(self) -> None:
        """
        Updates the data table based on changes in the selection list.

        This method is called when the selection in the selection list
        changes. It updates the rows in the data table to match the
        selected conditions.

        When the selection is changed, the table needs to be updated.
        """
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
            [table.add_row(*self.df.loc[o].values, label=o, key=o) for o in out]

        self.table_row_index = dict.fromkeys(sorted([r.value for r in table.rows]))
        self.sort_by_row_label(default="by_group")
        self.dump_contrast_values()

        self.set_heights()

    def set_heights(self):
        """
        Adjusts the height of the widget and its components.

        This method dynamically adjusts the heights of the contrast table,
        the condition selection list, and the overall widget based on the
        number of selected conditions (number of table rows).
        """
        self.get_widget_by_id("contrast_table_upper").styles.height = (
            len(self.get_widget_by_id("model_conditions_selection").selected) + 6
        )
        self.get_widget_by_id("model_conditions_selection").styles.height = (
            len(self.get_widget_by_id("model_conditions_selection")._values) + 2
        )
        self.styles.height = (
            len(self.get_widget_by_id("model_conditions_selection").selected)
            + len(self.get_widget_by_id("model_conditions_selection")._values)
            + 14
        )
        if len(self.feature_conditions_list) == 0:
            self.styles.height = 1

    def action_add_column(self):
        """
        Adds a new column with contrast values to the data table.

        This method presents a modal dialog to the user for specifying the
        contrast name and values. It then adds a new column to the data
        table with the provided contrast values.
        """

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
        """
        Removes the currently selected column from the data table.

        This method removes the column that is currently selected by the
        cursor in the data table.
        """
        table = self.get_widget_by_id("contrast_table")
        if len(table.ordered_columns) != 0:
            row_key, column_key = table.coordinate_to_cell_key(table.cursor_coordinate)
            table.remove_column(column_key)
            self.df = self.df.drop(column_key.value, axis=1)
            self.dump_contrast_values()

    @on(Button.Pressed, "ModelConditionsAndContrasts .add_button")
    async def add_col(self) -> None:
        """
        Handles the event when the "Add contrast values" button is pressed.

        This method triggers the `action_add_column` method to add a new
        column to the data table.
        """
        await self.run_action("add_column()")

    @on(Button.Pressed, "ModelConditionsAndContrasts .delete_button")
    async def remove_col(self) -> None:
        """
        Handles the event when the "Remove contrast values" button is pressed.

        This method triggers the `action_remove_column` method to remove the
        currently selected column from the data table.
        """
        await self.run_action("remove_column()")

    @on(Button.Pressed, "ModelConditionsAndContrasts .sort_button")
    async def sort_cols(self) -> None:
        """
        Handles the event when the "Sort table" button is pressed.

        This method triggers the `sort_by_row_label` method to sort the
        data table by row labels.
        """
        self.sort_by_row_label()

    def update_condition_selection(self):
        """
        Updates the condition selection based on selected images.

        When some images are selected/deselected, the condition selection
        needs to be upgraded and accordingly therefore the table.
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

    def sort_by_row_label(self, default: str | None = None):
        """
        Sorts the table by row labels.

        This method sorts the rows in the data table based on their labels,
        using either alphabetical order, reverse alphabetical order, or
        group-based order.

        Parameters
        ----------
        default : str, optional
            Custom sort type to override the default cycling sort types.
        """
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
        """
        Dumps the contrast values to the `feature_contrasts_dict` which is eesentialy
        the context cache..

        This method extracts the current contrast values from the data table
        and stores them in the `feature_contrasts_dict`. It also updates
        the `feature_conditions_list` with the current conditions.
        """
        table = self.get_widget_by_id("contrast_table")
        df_filtered = self.df.loc[sorted([i.value for i in table.rows])]

        self.feature_contrasts_dict.clear()
        # Iterate over each column in the DataFrame
        for column in df_filtered.columns:
            self.feature_contrasts_dict.append({"type": "t", "name": column, "values": df_filtered[column].to_dict()})

        self.feature_conditions_list.clear()
        self.feature_conditions_list.extend(df_filtered.index.values)
