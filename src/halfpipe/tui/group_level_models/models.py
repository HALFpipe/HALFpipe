# -*- coding: utf-8 -*-

from dataclasses import dataclass
from itertools import chain, combinations, cycle
from typing import Any, Dict

import pandas as pd
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, HorizontalScroll, ScrollableContainer, Vertical
from textual.css.query import NoMatches  # Import the NoMatches exception
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Select, SelectionList, Static, Switch
from textual.widgets.selection_list import Selection

from ...ingest.spreadsheet import read_spreadsheet
from ...model.file.spreadsheet import SpreadsheetFileSchema
from ...model.variable import VariableSchema
from ..feature_widgets.model_conditions_and_contrasts import ContrastTableInputWindow
from ..utils.context import ctx
from ..utils.custom_general_widgets import SwitchWithSelect
from ..utils.custom_switch import TextSwitch
from ..utils.draggable_modal_screen import DraggableModalScreen
from ..utils.file_browser_modal import FileBrowserModal, path_test_with_isfile_true
from ..utils.multichoice_radioset import MultipleRadioSet


class AdditionalContrastsCategoricalVariablesTable(Widget):
    # BORDER_TITLE = "Model conditions & contrast vales"

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

    # def watch_condition_values(self) -> None:
    #     self.update_condition_selection()

    def compose(self) -> ComposeResult:
        table = DataTable(zebra_stripes=True, header_height=2, id="contrast_table")
        # table = self.query_one(DataTable)
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

        ##############
        if self.feature_contrasts_dict != [] or self.feature_conditions_list != []:
            for contrast_dict in self.feature_contrasts_dict:
                table.add_column(contrast_dict["name"], key=contrast_dict["name"])
                for row_key in table.rows:
                    table.update_cell(row_key, contrast_dict["name"], contrast_dict["values"][row_key.value])
        #############
        # here this to avoid error
        self.table_row_index = dict.fromkeys(sorted([r.value for r in table.rows]))

        yield HorizontalScroll(
            table,
            id="contrast_table_upper",
        )
        yield Horizontal(
            Button("Add contrast values", classes="add_button"),
            Button("Remove contrast values", classes="delete_button"),
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


def widget_exists(where, widget):
    try:
        where.get_widget_by_id(widget)
        return True
    except NoMatches:
        return False


class ModelTemplate(Widget):
    """
    FeatureTemplate

    A widget for creating and managing feature-based settings and selections within a user interface. This widget
    handles both the initialization of a new widget and the loading of settings from a specification file, adapting
    its behavior accordingly.

    Attributes
    ----------
    entity : str
        An identifier for the type of entity the widget interacts with.
    filters : dict
        A dictionary specifying the datatype and suffix to filter the database queries.
    featurefield : str
        The specific feature field in the settings.
    type : str
        The type of the feature.
    file_panel_class : type
        The class used for the file panel within this widget.
    feature_dict : dict
        A dictionary containing feature-specific settings and values.
    setting_dict : dict
        A dictionary containing general settings and configuration values.
    event_file_pattern_counter : int
        A counter for file patterns.
    tagvals : list
        A list of available tags for selection.
    bandpass_filter_low_key : str
        The key for the low-pass filter setting.
    bandpass_filter_high_key : str
        The key for the high-pass filter setting.
    images_to_use : dict
        A dictionary specifying which images to use, keyed by task.
    confounds_options : dict
        Available options for confounds removal, with their descriptions and default states.
    preprocessing_panel : Vertical
        A panel containing pre-processing options such as smoothing, mean scaling, and temporal filtering.
    images_to_use_selection_panel : SelectionList
        A panel containing the selection list of images to use.
    tag_panel : SelectionList
        A panel containing the selection list of tags.

    Methods
    -------
    __init__(this_user_selection_dict, id=None, classes=None)
        Initializes the widget with user selections and settings.
    compose()
        Composes the user interface elements within the widget.
    on_file_panel_file_item_is_deleted(message)
        Handles the event when a file item is deleted from the file panel.
    on_file_panel_changed(message)
        Handles the event when the file panel changes, updating the tag selection.
    """

    # filters: dict = {"datatype": "", "suffix": ""}
    type: str = ""
    bold_filedict = {"datatype": "func", "suffix": "bold"}
    aggregate_order = ["dir", "run", "ses", "task"]

    # Check if any dictionary in the list has the required key-value pairs
    def extract_from_existing_filters(self, type_identifier, search_field="filters"):
        for filter_dict in self.model_dict[search_field]:
            if type_identifier.items() <= filter_dict.items():
                return filter_dict
        return None

    def __init__(self, this_user_selection_dict: dict, id: str | None = None, classes: str | None = None) -> None:
        """At the beginning there is a bunch of 'if not in'. If a new widget is created the pass
        this_user_selection_dict is empty and the nested keys need some initialization. On the other
        hand, if a new widget is created automatically on spec file load then this dictionary is not empty and these
        values are then used for the various widgets within this widget.
        """
        super().__init__(id=id, classes=classes)
        # The variable "is_new" is a flag that signals whether we are loading (or copying) or just creating a completely
        # new model. If it is new, then in the model_dict is exactly one key, i.e., 'name'.
        self.model_dict = this_user_selection_dict["models"]
        self.is_new = list(self.model_dict.keys()) == ["name"]

        print("ffffffffffffffffffffffffresh ", self.model_dict)
        self.model_dict.setdefault("type", self.type)
        self.model_dict.setdefault("filters", [])

        # In case of loading from a file or duplicating, we check whether there are some cutoffs made, if not then we switch
        # off the cutoff widget switch. It is enough to just check one of the cutoffs in the filter field.
        if (
            self.model_dict["filters"] != []
            and self.extract_from_existing_filters({"type": "cutoff", "field": "fd_mean"}) is not None
        ):
            cutoff_default_value = False
        else:
            cutoff_default_value = True

        # We need to field the filter dictionaries either from existing fields or assign default values to them.
        self.fd_mean_cutoff_dict = self.extract_from_existing_filters({"type": "cutoff", "field": "fd_mean"}) or {
            "type": "cutoff",
            "action": "exclude",
            "field": "fd_mean",
            "cutoff": "0.5",
        }

        self.fd_perc_cutoff_dict = self.extract_from_existing_filters({"type": "cutoff", "field": "fd_perc"}) or {
            "type": "cutoff",
            "action": "exclude",
            "field": "fd_perc",
            "cutoff": "10.0",
        }

        if self.model_dict["filters"] == []:
            self.model_dict["filters"].append(self.fd_mean_cutoff_dict)
            self.model_dict["filters"].append(self.fd_perc_cutoff_dict)

        # self.model_dict.setdefault("inputs", [])
        # First find all available tasks, assign True to all of them
        self.tasks_to_use: dict | None = {}
        for w in ctx.cache:
            if "features" in ctx.cache[w] and ctx.cache[w]["features"] != {}:
                if ctx.cache[w]["features"]["type"] == "task_based":
                    self.tasks_to_use[ctx.cache[w]["features"]["name"]] = True

        # If there are no pre-existing cutoff filters, then we just assign the keys from tasks_to_use dict, otherwise
        # we change values of the keys in tasks_to_use to dict to False if there are not present in the 'inputs' dict.
        if "inputs" not in self.model_dict:
            # self.model_dict["inputs"] = [task for task in self.tasks_to_use.keys() if self.tasks_to_use[task] is True]
            self.model_dict["inputs"] = list(self.tasks_to_use.keys())
        else:
            self.tasks_to_use = {task_key: task_key in self.model_dict["inputs"] for task_key in self.tasks_to_use.keys()}

        self.tasks_to_use_selection_panel = SelectionList[str](
            *[Selection(task, task, self.tasks_to_use[task]) for task in self.tasks_to_use.keys()],
            id="tasks_to_use_selection",
            classes="components",
        )

        self.cutoff_panel = Vertical(
            Grid(
                Static("Exclude subjects based on movements", classes="description_labels"),
                TextSwitch(value=cutoff_default_value, id="exclude_subjects"),
            ),
            Grid(
                Static("Specify the maximum allowed mean framewise displacement in mm", classes="description_labels"),
                Input(value=str(self.fd_mean_cutoff_dict["cutoff"]), placeholder="value", id="cutoff_fd_mean"),
                id="cutoff_fd_mean_panel",
            ),
            Grid(
                Static(
                    "Specify the maximum allowed percentage of frames above the framewise displacement threshold of 0.5 mm",
                    classes="description_labels",
                ),
                Input(value=str(self.fd_perc_cutoff_dict["cutoff"]), placeholder="value", id="cutoff_fd_perc"),
                id="cutoff_fd_perc_panel",
            ),
            id="cutoff_panel",
            classes="components",
        )

    async def on_mount(self) -> None:
        if self.tasks_to_use is not None:
            self.get_widget_by_id("tasks_to_use_selection").border_title = "Tasks to use"
        self.get_widget_by_id("cutoff_panel").border_title = "Cutoffs"

    @on(Input.Changed, "#cutoff_fd_mean")
    def _on_cutoff_fd_mean_input_changed(self, message: Message):
        self.fd_mean_cutoff_dict["cutoff"] = message.value

    @on(Input.Changed, "#cutoff_fd_perc")
    def _on_cutoff_fd_perc_input_changed(self, message: Message):
        self.fd_perc_cutoff_dict["cutoff"] = message.value

    @on(SelectionList.SelectedChanged, "#tasks_to_use_selection")
    def _on_selection_list_changed(self):
        self.model_dict["inputs"] = self.get_widget_by_id("tasks_to_use_selection").selected

    @on(Switch.Changed, "#exclude_subjects")
    def on_exclude_subjects_switch_changed(self, message: Message):
        if message.value is True:
            self.model_dict["filters"].append(self.fd_mean_cutoff_dict)
            self.model_dict["filters"].append(self.fd_perc_cutoff_dict)
            self.get_widget_by_id("cutoff_fd_mean_panel").styles.visibility = "visible"
            self.get_widget_by_id("cutoff_fd_perc_panel").styles.visibility = "visible"
            self.get_widget_by_id("cutoff_fd_perc_panel").styles.height = "auto"
        else:
            self.model_dict["filters"].remove(self.fd_mean_cutoff_dict)
            self.model_dict["filters"].remove(self.fd_perc_cutoff_dict)
            self.get_widget_by_id("cutoff_fd_mean_panel").styles.visibility = "hidden"
            self.get_widget_by_id("cutoff_fd_perc_panel").styles.visibility = "hidden"
            self.get_widget_by_id("cutoff_fd_perc_panel").styles.height = 7


class InterceptOnlyModel(ModelTemplate):
    type = "me"

    def __init__(self, this_user_selection_dict=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, id=id, classes=classes)

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_models"):
            if self.tasks_to_use is not None:
                yield self.tasks_to_use_selection_panel
            yield self.cutoff_panel


class LinearModel(ModelTemplate):
    type = "lme"

    def __init__(self, this_user_selection_dict=None, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(this_user_selection_dict=this_user_selection_dict, id=id, classes=classes)
        print("self.model_dictself.model_dictself.model_dict init", self.model_dict)
        self.spreadsheet_filepaths: dict[str, str] = {}
        self.model_dict.setdefault("contrasts", [])

        self.model_dict.setdefault("spreadsheet", None)
        # In case loading or duplicating, the spreadsheet field is not None. So we need to find matching fileobject in the
        # ctx.cache and assign it in this widget.
        for key in ctx.cache:
            if key.startswith("__spreadsheet_file_"):
                self.spreadsheet_filepaths[key] = ctx.cache[key]["files"].path  # type: ignore

        print("self.spreadsheet_filepathsself.spreadsheet_filepathsself.spreadsheet_filepaths", self.spreadsheet_filepaths)
        # self.options: dict = {f: (f, True if f == filepaths[-1] else False) for f in filepaths} if filepaths else {}

        # there has to be button to Add new spreadsheet
        self.spreadsheet_panel = Vertical(
            # Static('No spreadsheet selected!', id='spreadsheet_path_label'),
            Select([(i[1], i[0]) for i in self.spreadsheet_filepaths.items()], id="spreadsheet_selection"),
            Horizontal(
                Button("Add", id="add_spreadsheet"),
                Button("Delete", id="delete_spreadsheet"),
                Button("Details", id="details_spreadsheet"),
            ),
            id="spreadsheet_selection_panel",
            classes="components",
        )
        self.spreadsheet_panel.border_title = "Covariates/group data spreadsheet file"

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="top_container_models"):
            if self.tasks_to_use is not None:
                yield self.tasks_to_use_selection_panel
            yield self.cutoff_panel
            yield self.spreadsheet_panel

    async def on_mount(self):
        if self.model_dict["spreadsheet"] is not None:
            print("ffffffffffffffffffffffffff")
            matching_key = next(
                (key for key, value in self.spreadsheet_filepaths.items() if value == self.model_dict["spreadsheet"]), None
            )
            print("matching_keymatching_keymatching_key", matching_key)
            self.get_widget_by_id("spreadsheet_selection").value = matching_key
            # await self.load_selections_based_on_spreadsheet(matching_key)

    @on(Button.Pressed, "#add_spreadsheet")
    async def _on_button_select_spreadsheet_pressed(self):
        def update_spreadsheet_label(new_spreadsheet_selection):
            print("ffffffffffffffffff", new_spreadsheet_selection)
            if new_spreadsheet_selection is not False:
                self.spreadsheet_filepaths[new_spreadsheet_selection[0]] = new_spreadsheet_selection[1]
                self.get_widget_by_id("spreadsheet_selection").set_options(
                    [(i[1], i[0]) for i in self.spreadsheet_filepaths.items()]
                )
                self.get_widget_by_id("spreadsheet_selection").value = new_spreadsheet_selection[0]
                self.model_dict["spreadsheet"] = new_spreadsheet_selection[1]
                # self.get_widget_by_id('spreadsheet_path_label').update(selected_path)
                # self.get_widget_by_id("spreadsheet_path_label").styles.border = ("solid", "green")

        await self.app.push_screen(AddSpreadsheetModal(), update_spreadsheet_label)

    @on(Select.Changed, "#spreadsheet_selection")
    async def _on_spreadsheet_selection_changed(self, message):
        print("mmmmmmmmmmmmmmmmm", message.control.id)
        print("vvvvvvvvvvvvvvvvvvvv", message.value)
        spreadsheet_cache_id = message.value
        #     await self.load_selections_based_on_spreadsheet(spreadsheet_cache_id)
        #
        # async def load_selections_based_on_spreadsheet(self, spreadsheet_cache_id):
        metadata_variables = ctx.cache[spreadsheet_cache_id]["files"].metadata["variables"]  # type: ignore
        self.metadata_variables = metadata_variables
        spreadsheet_path = ctx.cache[spreadsheet_cache_id]["files"].path  # type: ignore
        self.spreadsheet_df = read_spreadsheet(spreadsheet_path)

        sub_panels = []
        self.variables = []
        # self.is_new
        # continue from here ...

        for metadata_item in metadata_variables:
            # for f in self.model_dict['filters']

            print("nnnnnnnnnnnnnn", metadata_item)
            variable_name = metadata_item["name"]
            if metadata_item["type"] != "id":
                self.variables.append(variable_name)
            if metadata_item["type"] == "categorical":
                # The 'metadata_item["levels"]' is list containing all possible levels, if 'self.model_dict' was empty an init,
                # i.e., no duplicate or load, then all level values are set to True. In the load/duplicate case, we first find
                # the particular dictionary in the self.model_dict['filters'] corresponding to the particular variable that
                # is now in the loop, and for all elements from this list we set the selection value to True, for not present
                # elements (in compare to list from metadata_item["levels"]) to False.
                # metadata_item["levels"]
                # selection_variable_dict = {}
                # if v in
                # for v in metadata_item["levels"]:
                filter_identifier = {"type": "group", "action": "include", "variable": variable_name}
                filt_dict = self.extract_from_existing_filters(filter_identifier)
                print("filt_dictfilt_dictfilt_dictfilt_dict", filt_dict)
                sub_panels.append(
                    Vertical(
                        Static(variable_name, classes="level_labels"),
                        SelectionList[str](
                            *[
                                Selection(
                                    str(v),
                                    str(v),
                                    True
                                    if (filt_dict is None or v in filt_dict["levels"] or (self.is_new is True))
                                    else False,
                                )
                                for v in metadata_item["levels"]
                            ],
                            classes="level_selection",
                            id=variable_name + "_panel",
                        ),
                        classes="level_sub_panels",
                    )
                )
                self.model_dict["filters"].append(
                    {
                        "type": "group",
                        "action": "include",
                        "variable": variable_name,
                        "levels": [str(i) for i in list(set(self.spreadsheet_df.loc[:, variable_name]))],
                    }
                )
                # now set is_new flag to False
        #
        # if self.is_mounted('top_levels_panel'):
        #     await self.remove('top_levels_panel')
        if widget_exists(self, "top_levels_panel") is True:
            await self.get_widget_by_id("top_levels_panel").remove()
        if widget_exists(self, "top_model_variables_panel") is True:
            await self.get_widget_by_id("top_model_variables_panel").remove()
        if widget_exists(self, "top_interaction_panel") is True:
            await self.get_widget_by_id("top_interaction_panel").remove()
        if widget_exists(self, "top_contrast_panel") is True:
            await self.get_widget_by_id("top_contrast_panel").remove()
        # what is on goes  to contrast as                 {
        #                     "type": "infer",
        #                     "variable": [
        #                         "Severity"
        #                     ]
        #                 }
        # what has delete missing bla bla goes as
        # {
        #     "type": "missing",
        #     "action": "exclude",
        #     "variable": "Severity"
        # }
        # to filters
        await self.mount(
            Container(
                Static(
                    "Select the subjects to include in this analysis by their categorical variables\n\
For multiple categorical variables, the intersecion of the groups will be used.",
                    id="levels_instructions",
                    classes="instructions",
                ),
                Horizontal(
                    *sub_panels,
                    id="levels_panel",
                ),
                id="top_levels_panel",
                classes="components",
            ),
            after=self.get_widget_by_id("spreadsheet_selection_panel"),
        )

        # {
        #     "action": "exclude",
        #     "type": "missing",
        #     "variable": varname,
        # }

        # If a selection for a variable in 'Add variables to the model' is On, then in the contrast field there is a dictionary
        # with "type": "infer" and "variable": *the variable*. We use this to set up the defaults in the following widget.
        # When there is no load or duplication of the widget, i.e., we are creating a new widget, then as default we turn all
        # variables 'On'. For this we fill the mode_dict with the particular items.
        interaction_variables = set([])
        if self.is_new is True:
            for v in self.variables:
                self.model_dict["contrasts"].append({"type": "infer", "variable": [v]})
        else:
            # in case of load, we use this a bit tricky way to get a list of variables used to create the interaction terms.
            for contrast_item in self.model_dict["contrasts"]:
                if contrast_item["type"] == "infer" and len(contrast_item["variable"]) > 1:
                    interaction_variables.update(contrast_item["variable"])
        nvar = len(interaction_variables)
        terms = list(chain.from_iterable(combinations(interaction_variables, i) for i in range(2, nvar + 1)))
        term_by_str = {" * ".join(termtpl): termtpl for termtpl in terms}

        # For the second part, the 'Action for the missing values', we use presence of the dictionary
        # {"action": "exclude", "type": "missing", "variable": *the variable*} in the model_dict['filters']. If it is there
        # the default values is set to 'listwise_deletion'. If this is a new widget then there are no such entries in the
        # 'filters' hence all default values are set to 'mean_substitution'.
        await self.mount(
            Container(
                Static(
                    "Specify the variables to add to the model and action for missing values",
                    id="model_variables_instructions",
                    classes="instructions",
                ),
                *[
                    SwitchWithSelect(
                        v,
                        options=[("Listwise deletion", "listwise_deletion"), ("Mean substitution", "mean_substitution")],
                        switch_value=True
                        if self.extract_from_existing_filters({"type": "infer", "variable": [v]}, search_field="contrasts")
                        is not None
                        else False,
                        default_option="listwise_deletion"
                        if self.extract_from_existing_filters({"action": "exclude", "type": "missing", "variable": v})
                        is not None
                        else "mean_substitution",
                        id=v + "_model_vars",
                        classes="additional_preprocessing_settings",
                    )
                    for v in self.variables
                ],
                # SelectionList[str](
                #     *[Selection(str(v), str(v), True) for v in self.variables], classes="model_variables_selection"
                # ),
                id="top_model_variables_panel",
                classes="components",
            ),
            after=self.get_widget_by_id("top_levels_panel"),
        )

        await self.mount(
            Container(
                Static(
                    "Specify the variables for which to calculate interaction terms",
                    id="interaction_variables_instructions",
                    classes="instructions",
                ),
                SelectionList[str](
                    *[Selection(str(v), str(v), v in interaction_variables) for v in self.variables],
                    # classes="level_selection",
                    id="interaction_variables_selection_panel",
                ),
                Static(
                    "Select which interaction terms to add to the model",
                    id="interaction_terms_instructions",
                    classes="instructions",
                ),
                SelectionList[str](
                    *[Selection(key, term_by_str[key], True) for key in term_by_str.keys()],
                    # classes="level_selection",
                    id="interaction_terms_selection_panel",
                ),
                id="top_interaction_panel",
                classes="components",
            ),
            after=self.get_widget_by_id("top_model_variables_panel"),
        )

        # In the TextSwitch we use hardcoded False but on the other hand, we use the flag self.has_type_t to toggle the switch
        # if there is some content for the contrast tables (load, duplication case). Doing this in such a two step way will
        # automatically trigger the function _on_contrast_switch_changed same as when the user toggles the button.
        await self.mount(
            Container(
                Static(
                    "Contrasts for the mean across all subjects, and for all variables will be generated automatically",
                    classes="instructions",
                ),
                Grid(
                    Static("Add additional contrasts for categorical variables", id="contrast_switch_label", classes="label"),
                    TextSwitch(value=False, id="contrast_switch"),
                    id="contrast_switch_panel",
                ),
                id="top_contrast_panel",
                classes="components",
            ),
            after=self.get_widget_by_id("top_interaction_panel"),
        )
        # Scan whether there are some values for the contrast tables (in case of load or duplication.
        self.has_type_t = any(item.get("type") == "t" for item in self.model_dict["contrasts"])
        if self.has_type_t is True:
            self.get_widget_by_id("contrast_switch").toggle()

        # Here we set the flat to False, because in any case after this point it should always be False.
        self.is_new = False

        self.get_widget_by_id("top_levels_panel").border_title = "Subjects to include by their categorical variables"
        self.get_widget_by_id("top_model_variables_panel").border_title = "Model variables"
        self.get_widget_by_id("top_interaction_panel").border_title = "Interaction terms"
        self.get_widget_by_id("top_contrast_panel").border_title = "Additional contrasts"

    @on(SwitchWithSelect.SwitchChanged)
    def _on_switch_with_select_switch_changed(self, message):
        print("qqqqqqqqqqqqqqq", message.control.id, message.switch_value)
        contrast_item = {"type": "infer", "variable": [message.control.id[:-11]]}
        if message.switch_value is True:
            self.model_dict["contrasts"].append(contrast_item)
        elif contrast_item in self.model_dict["contrasts"]:
            self.model_dict["contrasts"].remove(contrast_item)
        print("cccccccccccccccc", ctx.cache)

    @on(SwitchWithSelect.Changed)
    def _on_switch_with_select_changed(self, message):
        print("qqqqqqqqqqqqqqq", message.control.id, message.value)
        filter_item = {"type": "missing", "action": "exclude", "variable": message.control.id[:-11]}
        if message.value == "listwise_deletion":
            self.model_dict["filters"].append(filter_item)
        elif filter_item in self.model_dict["filters"]:
            self.model_dict["filters"].remove(filter_item)
        print("cccccccccccccccc", ctx.cache)

    @on(SelectionList.SelectedChanged, ".level_selection")
    def _on_level_sub_panels_selection_list_changed(self, message):
        print("qqqqqqqqqqq", message.control.id)
        print("qqqqqqqqqqq", message.control.selected)
        variable_name = message.control.id[:-6]
        filter_type_identifier = {
            "type": "group",
            "action": "include",
            "variable": variable_name,
        }
        filter_dict = self.extract_from_existing_filters(filter_type_identifier)
        filter_dict["levels"] = sorted(message.control.selected)
        print("cccccccccccccccc", ctx.cache)

        # When we change selection of the categorical variables, we need to close the contrast tables (if are opened)
        # This is because the tables need an update because the rows of the tables depends on the choices from the
        # level_selection widget.
        self.get_widget_by_id("contrast_switch").value = False

    @on(SelectionList.SelectedChanged, "#interaction_variables_selection_panel")
    def _on_interaction_variables_selection_list_changed(self, message):
        print("qqqqqqqqqqq", message.control.id)
        print("qqqqqqqqqqq", message.control.selected)
        nvar = len(message.control.selected)
        terms = list(chain.from_iterable(combinations(message.control.selected, i) for i in range(2, nvar + 1)))
        term_by_str = {" * ".join(termtpl): termtpl for termtpl in terms}
        self.get_widget_by_id("interaction_terms_selection_panel").clear_options()
        # Also delete every interaction term in the ctx.cache
        for contrast_item in self.model_dict["contrasts"]:
            if contrast_item["type"] == "infer" and len(contrast_item["variable"]) > 1:
                self.model_dict["contrasts"].remove(contrast_item)

        self.get_widget_by_id("interaction_terms_selection_panel").add_options(
            [Selection(key, term_by_str[key], False) for key in term_by_str.keys()]
        )
        print("termstermstermstermstermsterms", term_by_str)

    @on(SelectionList.SelectedChanged, "#interaction_terms_selection_panel")
    def _on_interaction_terms_selection_list_changed(self, message):
        print("qqqqqqqqqqq", message.control.id)
        print("qqqqqqqqqqq", message.control.selected)
        # first remove all interaction terms
        print("0vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv", self.model_dict["contrasts"])

        # for contrast_item in self.model_dict["contrasts"][:]:
        #     if contrast_item["type"] == "infer" and len(contrast_item["variable"]) > 1:
        #         self.model_dict["contrasts"].remove(contrast_item)
        self.model_dict["contrasts"] = list(
            filter(
                lambda contrast_item: not (contrast_item["type"] == "infer" and len(contrast_item["variable"]) > 1),
                self.model_dict["contrasts"],
            )
        )

        print("1vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv", self.model_dict["contrasts"])

        # Now add every terms that is currently selected in the widget to the cache

        for interaction_term in message.control.selected:
            self.model_dict["contrasts"].append({"type": "infer", "variable": interaction_term})
        print("2vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv", self.model_dict["contrasts"])

        # filter_item = {
        #     "type": "infer",
        #     "variable": message.control.id[:-11]
        # # }
        # if message.value == 'listwise_deletion':
        #     self.model_dict["filters"].append(filter_item)
        # elif filter_item in self.model_dict["filters"]:
        #     self.model_dict["filters"].remove(filter_item)

    @on(TextSwitch.Changed, "#contrast_switch")
    async def _on_contrast_switch_changed(self, message):
        # metadata_variables = ctx.cache[spreadsheet_cache_id]["files"].metadata["variables"]  # type: ignore
        # spreadsheet_path = ctx.cache[spreadsheet_cache_id]["files"].path  # type: ignore
        # self.spreadsheet_df = read_spreadsheet(spreadsheet_path)
        # self.is_new
        # continue from here ...

        only_categorical_metadata = list(filter(lambda item: item["type"] == "categorical", self.metadata_variables))
        self.categorical_variables_list = [element["name"] for element in only_categorical_metadata]

        if message.value is True:
            for categorical_metadata_item in only_categorical_metadata:
                categorical_contrast_items = list(
                    filter(
                        lambda contrast_item: contrast_item["type"] == "t"
                        and contrast_item["variable"] == [categorical_metadata_item["name"]],
                        self.model_dict["contrasts"],
                    )
                )
                print("categorical_contrast_itemscategorical_contrast_items", categorical_contrast_items)
                contrast_table_widget = AdditionalContrastsCategoricalVariablesTable(
                    all_possible_conditions=categorical_metadata_item["levels"],
                    feature_contrasts_dict=categorical_contrast_items,
                    feature_conditions_list=self.get_widget_by_id(categorical_metadata_item["name"] + "_panel").selected,
                    id=categorical_metadata_item["name"] + "_contrast_panel",
                    classes="components model_conditions_and_constrasts",
                )
                contrast_table_widget.border_title = categorical_metadata_item["name"]
                await self.get_widget_by_id("top_contrast_panel").mount(contrast_table_widget)
        elif widget_exists(self, "top_contrast_panel") is True:
            for child in self.get_widget_by_id("top_contrast_panel").walk_children(
                AdditionalContrastsCategoricalVariablesTable
            ):
                child.remove()

    @on(AdditionalContrastsCategoricalVariablesTable.Changed)
    def _on_additional_contrasts_categorical_variables_table_changed(self, message):
        print("AdditionalContrastsCategoricalVariablesTable mmmmmmmmmmmmmmmmmmmmmmmmmmm", message.value)

        # this will delete all previous contrasts type 't' of the particular contraste variable. This is done because
        # in the next line we fill it again based on what is actually in the table.
        self.model_dict["contrasts"] = [
            item
            for item in self.model_dict["contrasts"]
            if not (item.get("type") == "t" and item.get("variable") == [message.control.id[:-15]])
        ]
        for contrast_item in message.value:
            self.model_dict["contrasts"].append(contrast_item)


class AddSpreadsheetModal(DraggableModalScreen):
    """
    SelectionModal(options=None, title="", instructions="Select", id=None, classes=None)

    Parameters
    ----------
    options : dict, optional
        A dictionary containing the options for the radio buttons,
        where keys are the option identifiers and values are the
        display text for each option. If not provided, defaults to
        {"a": "A", "b": "B"}.
    title : str, optional
        The title of the modal window, by default an empty string.
    instructions : str, optional
        Instructions or description to be displayed at the top of
        the modal window, by default "Select".
    id : str, optional
        An optional identifier for the modal window, by default None.
    classes : str, optional
        An optional string of classes for applying styles to the
        modal window, by default None.

    Attributes
    ----------
    title_bar.title : str
        Sets the title of the modal window.
    instructions : str
        Holds the instruction text for the modal window.
    widgets_to_mount : list
        A list of widgets to be mounted on the modal window, including
        title, radio buttons, and OK/Cancel buttons.
    choice : str or list
        The selected choice from the radio buttons, defaults to a
        placeholder "default_choice???todo".

    Methods
    -------
    on_mount()
        Called when the window is mounted. Mounts the content widgets.
    _on_ok_button_pressed()
        Handles the OK button press event, dismissing the modal window
        with the current choice.
    _on_cancel_button_pressed()
        Handles the Cancel button press event, dismissing the modal
        window with None value.
    _on_radio_set_changed(event)
        Handles the event when the radio button selection changes.
        Updates the choice attribute with the selected option key.
    """

    instance_count = 0

    def __init__(
        self,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.title_bar.title = "Path to the spreadsheet"
        self.instructions = "Select or add path of the covariates/group data spreadsheet file"
        filepaths = ctx.database.get(datatype="spreadsheet")
        # filepaths = ctx.get_spreadsheet_paths
        self.cache_name = "__spreadsheet_file_" + str(self.instance_count)
        self.instance_count += 1
        self.filedict: dict[str, str | list] = {}
        self.metadata: list[Dict[str, Any]] = []

        print("fffffffffffffffffff", filepaths)
        # self.options: dict = {f: (f, True if f == filepaths[-1] else False) for f in filepaths} if filepaths else {}
        self.last_selected = list(filepaths)[-1] if filepaths != set() else None

        # In some cases the user just must made some choice in the selection. In particular this is the case when one is
        # some of the Meta classes (CheckMeta...) are in action. Returning from this stage by hitting the cancel button would
        # not make sense.
        button_panel = Horizontal(
            Button("OK", id="ok"), Button("Cancel", id="cancel"), id="button_panel", classes="components"
        )

        self.widgets_to_mount = [
            ScrollableContainer(
                Container(
                    Static(self.instructions, id="title"),
                    Horizontal(
                        Button("Browse", id="browse"),
                        Static("No spreadsheet selected!", id="spreadsheet_path_label"),
                    ),
                    id="spreadsheet_path_panel",
                    classes="components",
                ),
                button_panel,
                id="top_container",
            )
        ]

        # self.choice: str | list = self.options.keys()[0]

    async def on_mount(self) -> None:
        """Called when the window is mounted."""
        await self.content.mount(*self.widgets_to_mount)
        self.get_widget_by_id("spreadsheet_path_panel").border_title = "Spreadsheet path"

    async def update_spreadsheet_list(self, spreadsheet_path: str | bool):
        if spreadsheet_path != "" and isinstance(spreadsheet_path, str):
            self.get_widget_by_id("spreadsheet_path_label").update(spreadsheet_path)
            self.spreadsheet_df = read_spreadsheet(spreadsheet_path)
            print("file_name")
            self.filedict = {"datatype": "spreadsheet", "path": spreadsheet_path}

            # ctx.cache[self.cache_name]["files"] = {"datatype": "spreadsheet", "path": spreadsheet_path, "metadata": []}

            for i, col_label in enumerate(self.spreadsheet_df.columns):
                type = "id" if i == 0 else "continuous"
                # ctx.cache[self.cache_name]["files"]["metadata"].append({"name": col_label, "type": type})
                # self.filedict["metadata"].append({"name": col_label, "type": type})
                self.metadata.append({"name": col_label, "type": type})
            print("ccccccccccccccccccccc", ctx.cache)

            await self.mount(
                Container(
                    Static("Specify the column data types", id="column_assignement_label"),
                    MultipleRadioSet(
                        horizontal_label_set=["id", "continuous", "categorical"],
                        vertical_label_set=list(self.spreadsheet_df.columns.values),
                        default_value_column=1,
                        unique_first_column=True,
                        id="column_assignement",
                    ),
                    id="column_assignement_top_container",
                    classes="components",
                ),
                after=self.get_widget_by_id("spreadsheet_path_panel"),
            )
            self.get_widget_by_id("column_assignement_top_container").border_title = "Column data types"

    @on(MultipleRadioSet.Changed)
    def on_radio_set_changed(self, message):
        # Extract the row number and column label
        row_number = int(message.row.replace("row_radio_sets_", ""))
        col_label = self.spreadsheet_df.columns[row_number]

        # Get unique levels from the selected column
        levels = list(self.spreadsheet_df.iloc[:, row_number].unique())
        # ensure that all are strings
        levels = [str(i) for i in levels]

        # Filter out existing metadata for the column
        # metadata = ctx.cache[self.cache_name]["files"]["metadata"]
        # metadata = self.metadata
        self.metadata = [item for item in self.metadata if item.get("name") != col_label]

        # Determine the metadata type based on the column
        metadata_entry = {"name": col_label}
        if message.column == 1:
            metadata_entry["type"] = "id"
        elif message.column == 2:
            metadata_entry["type"] = "categorical"
            metadata_entry["levels"] = levels
        elif message.column == 3:
            metadata_entry["type"] = "continuous"

        # Append the updated metadata entry
        self.metadata.append(metadata_entry)
        # ctx.cache[self.cache_name]["files"]["metadata"] = metadata
        # self.filedict["metadata"] = metadata

    @on(Button.Pressed, "#browse")
    async def _on_add_button_pressed(self):
        await self.app.push_screen(
            FileBrowserModal(title="Select spreadsheet", path_test_function=path_test_with_isfile_true),
            self.update_spreadsheet_list,
        )

    @on(Button.Pressed, "#ok")
    def _on_ok_button_pressed(self):
        # create new file item
        # dismiss some identification of it
        print("cccccccccccccccc", ctx.cache)
        fileobj = SpreadsheetFileSchema().load(self.filedict)
        if not hasattr(fileobj, "metadata") or fileobj.metadata is None:
            fileobj.metadata = dict()

        if fileobj.metadata.get("variables") is None:
            fileobj.metadata["variables"] = []

        print("sdaaaaaaaself.metadataself.metadataself.metadata", self.metadata)
        for vardict in self.metadata:
            fileobj.metadata["variables"].append(VariableSchema().load(vardict))

        ctx.cache[self.cache_name]["files"] = fileobj

        # self.dismiss((self.cache_name, ctx.cache[self.cache_name]["files"]["path"]))
        self.dismiss((self.cache_name, self.filedict["path"]))
        # selected = self.get_widget_by_id("selection_set").selected
        # if selected != []:
        #     self.dismiss(selected[0])
        # else:
        #     self.dismiss(False)

    @on(Button.Pressed, "#cancel")
    def _on_cancel_button_pressed(self):
        self.dismiss(False)

    def request_close(self):
        self.dismiss(False)

    #
    # @on(SelectionList.SelectionToggled, "#selection_set")
    # def _on_selection_set_toggled(self, message):
    #     selected_value = message.selection
    #     message.control.deselect(self.last_selected)
    #     self.last_selected = selected_value
