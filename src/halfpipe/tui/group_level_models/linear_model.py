# -*- coding: utf-8 -*-

from itertools import chain, combinations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Select, SelectionList, Static
from textual.widgets._select import BLANK
from textual.widgets.selection_list import Selection

from ...ingest.spreadsheet import read_spreadsheet
from ..data_analyzers.context import ctx
from ..general_widgets.custom_general_widgets import SwitchWithSelect
from ..general_widgets.custom_switch import TextSwitch
from ..help_functions import widget_exists
from ..templates.model_template import ModelTemplate
from .utils.add_spreadsheet_modal import AddSpreadsheetModal
from .utils.additional_contrasts_table import AdditionalContrastsCategoricalVariablesTable


class LinearModel(ModelTemplate):
    """
    A model representing a linear group-level model.

    This class extends `ModelTemplate` to provide a specific type of
    group-level model that includes an intercept term and allows for
    the inclusion of additional variables and interaction terms. It
    allows users to select tasks to use, set aggregation levels, define
    cutoff values, and specify a spreadsheet file for covariates and
    group data.

    Attributes
    ----------
    type : str
        The type of the model, set to "lme" for linear model.
    spreadsheet_filepaths : dict[str, str]
        A dictionary mapping spreadsheet cache IDs to their file paths.
    model_dict : dict[str, Any]
        A dictionary containing the model's configuration, including
        contrasts, filters, and the selected spreadsheet.
    spreadsheet_panel : Vertical
        A panel containing widgets for selecting and managing the
        spreadsheet file.
    metadata_variables : list[dict[str, Any]]
        A list of metadata dictionaries for the variables in the
        selected spreadsheet.
    spreadsheet_df : pd.DataFrame
        A pandas DataFrame containing the data from the selected
        spreadsheet.
    variables : list[str]
        A list of variable names from the selected spreadsheet.
    is_new : bool
        A flag indicating whether the model is newly created or loaded
        from existing data.
    has_type_t : bool
        A flag indicating whether the model has type 't' contrasts.

    Methods
    -------
    __init__(this_user_selection_dict, id, classes)
        Initializes the model with optional user selections, ID, and classes.
    compose() -> ComposeResult
        Composes the widget's components.
    _on_button_select_spreadsheet_pressed()
        Handles the event when the "Add" button for the spreadsheet is pressed.
    _on_spreadsheet_selection_changed(message)
        Handles changes in the selected spreadsheet.
    _on_switch_with_select_switch_changed(message)
        Handles changes in the switch state of a SwitchWithSelect widget.
    _on_switch_with_select_changed(message)
        Handles changes in the selected option of a SwitchWithSelect widget.
    _on_level_sub_panels_selection_list_changed(message)
        Handles changes in the selection of levels for a categorical variable.
    _on_interaction_variables_selection_list_changed(message)
        Handles changes in the selected interaction variables.
    _on_interaction_terms_selection_list_changed(message)
        Handles changes in the selected interaction terms.
    _on_contrast_switch_changed(message)
        Handles changes in the state of the contrast switch.
    _on_additional_contrasts_categorical_variables_table_changed(message)
        Handles changes in the additional contrasts table.
    """

    # Type of the model, set to "lme" for linear model.
    type = "lme"

    def __init__(self, this_user_selection_dict=None, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the model with optional user selections, ID, and classes.

        Parameters
        ----------
        this_user_selection_dict : dict | None, optional
            A dictionary containing user-specified selections for the model,
            by default None.
        id : str | None, optional
            An optional identifier for the model, by default None.
        classes : str | None, optional
            An optional string of classes for applying styles to the model,
            by default None.
        """
        super().__init__(this_user_selection_dict=this_user_selection_dict, id=id, classes=classes)
        # A dictionary mapping spreadsheet cache IDs to their file paths.
        self.spreadsheet_filepaths: dict[str, str] = {}
        self.model_dict.setdefault("contrasts", [])
        self.model_dict.setdefault("filters", [])
        self.model_dict.setdefault("spreadsheet", None)
        # In case loading or duplicating, the spreadsheet field is not None. So we need to find matching fileobject in the
        # ctx.cache and assign it in this widget.
        for key in ctx.cache:
            if key.startswith("__spreadsheet_file_"):
                self.spreadsheet_filepaths[key] = ctx.cache[key]["files"].path  # type: ignore

        # there has to be button to Add new spreadsheet
        spreadsheet_selection = Select(
            [(i[1], i[0]) for i in self.spreadsheet_filepaths.items()],
            value=next(
                (key for key, value in self.spreadsheet_filepaths.items() if value == self.model_dict["spreadsheet"]), BLANK
            )
            if self.model_dict["spreadsheet"] is not None
            else BLANK,
            id="spreadsheet_selection",
        )

        self.spreadsheet_panel = Vertical(
            # Static('No spreadsheet selected!', id='spreadsheet_path_label'),
            spreadsheet_selection,
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
                yield self.aggregate_panel
            yield self.cutoff_panel
            yield self.spreadsheet_panel

    @on(Button.Pressed, "#add_spreadsheet")
    async def _on_button_select_spreadsheet_pressed(self):
        """
        Handles the event when the "Add" button for the spreadsheet is pressed.

        This method pushes the `AddSpreadsheetModal` onto the screen to
        allow the user to select a spreadsheet file. It then updates the
        spreadsheet selection widget with the newly selected file.
        """

        def update_spreadsheet_label(new_spreadsheet_selection):
            if new_spreadsheet_selection is not False:
                self.spreadsheet_filepaths[new_spreadsheet_selection[0]] = new_spreadsheet_selection[1]
                self.get_widget_by_id("spreadsheet_selection").set_options(
                    [(i[1], i[0]) for i in self.spreadsheet_filepaths.items()]
                )
                self.get_widget_by_id("spreadsheet_selection").value = new_spreadsheet_selection[0]
                self.model_dict["spreadsheet"] = new_spreadsheet_selection[1]

        await self.app.push_screen(AddSpreadsheetModal(), update_spreadsheet_label)

    @on(Select.Changed, "#spreadsheet_selection")
    async def _on_spreadsheet_selection_changed(self, message):
        """
        Handles changes in the selected spreadsheet.

        This method is called when the user selects a different
        spreadsheet from the `Select` widget. It updates the model's
        configuration based on the selected spreadsheet, including
        loading metadata, setting up filters, and creating widgets for
        variable selection and interaction terms.

        Parameters
        ----------
        message : Select.Changed
            The message object containing information about the selection
            change.
        """
        # First remove and deleting everything to start fresh. If there is not value selected, nothing will load.
        if widget_exists(self, "top_levels_panel") is True:
            await self.get_widget_by_id("top_levels_panel").remove()
        if widget_exists(self, "top_model_variables_panel") is True:
            await self.get_widget_by_id("top_model_variables_panel").remove()
        if widget_exists(self, "top_interaction_panel") is True:
            await self.get_widget_by_id("top_interaction_panel").remove()
        if widget_exists(self, "top_contrast_panel") is True:
            await self.get_widget_by_id("top_contrast_panel").remove()

        if message.value == BLANK:
            self.model_dict.pop("spreadsheet", None)
            self.model_dict["contrasts"] = []
            self.model_dict["filters"] = [
                f for f in self.model_dict["filters"] if f["type"] != "group" or f["type"] != "missing"
            ]
            # Pretend that it is a new model because this is what happens when we switch off the spreadsheet file.
            self.is_new = True

        if message.value != BLANK:
            spreadsheet_cache_id = message.value
            metadata_variables = ctx.cache[spreadsheet_cache_id]["files"].metadata["variables"]  # type: ignore
            self.metadata_variables = metadata_variables
            spreadsheet_path = ctx.cache[spreadsheet_cache_id]["files"].path  # type: ignore
            self.spreadsheet_df = read_spreadsheet(spreadsheet_path)
            self.model_dict["spreadsheet"] = spreadsheet_path

            sub_panels = []
            self.variables = []
            # self.is_new
            # continue from here ...

            for metadata_item in metadata_variables:
                variable_name = metadata_item["name"]
                if metadata_item["type"] != "id":
                    self.variables.append(variable_name)
                if metadata_item["type"] == "categorical":
                    filt_dict = next(
                        (
                            f
                            for f in self.model_dict["filters"]
                            if f.get("type") == "group" and f.get("variable") == variable_name
                        ),
                        None,
                    )
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
                    # To avoid duplicate entries in the filters, use this if. This can happened when we are loading or
                    # duplicating the model.
                    # if filt_dict is None:
                    #     filt_dict = {
                    #         "type": "group",
                    #         "action": "include",
                    #         "variable": variable_name,
                    #         "levels": [str(i) for i in list(set(self.spreadsheet_df.loc[:, variable_name]))],
                    #     }
                    #     self.model_dict["filters"].append(filt_dict)

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

            # If a selection for a variable in 'Add variables to the model' is On, then in the contrast field there is a
            # dictionary with "type": "infer" and "variable": *the variable*. We use this to set up the defaults in the
            # following widget. When there is no load or duplication of the widget, i.e., we are creating a new widget,
            # then as default we turn all variables 'On'. For this we fill the mode_dict with the particular items.
            interaction_variables = set([])
            if self.is_new is True:
                for v in self.variables:
                    self.model_dict["contrasts"].append({"type": "infer", "variable": [v]})
            else:
                # In case of load, we use this a bit tricky way to get a list of variables used to create the interaction terms
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
                            switch_value=bool(
                                next((f for f in self.model_dict["contrasts"] if f.get("variable") == [v]), False)
                            ),
                            default_option="listwise_deletion"
                            if next(
                                (
                                    f
                                    for f in self.model_dict["filters"]
                                    if f.get("variable") == v and f.get("type") == "missing"
                                ),
                                False,
                            )
                            or self.is_new
                            else "mean_substitution",
                            id=v + "_model_vars",
                            classes="additional_preprocessing_settings",
                        )
                        for v in self.variables
                    ],
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
                        id="interaction_variables_selection_panel",
                    ),
                    Static(
                        "Select which interaction terms to add to the model",
                        id="interaction_terms_instructions",
                        classes="instructions",
                    ),
                    SelectionList[str](
                        *[Selection(key, term_by_str[key], True) for key in term_by_str.keys()],
                        id="interaction_terms_selection_panel",
                    ),
                    id="top_interaction_panel",
                    classes="components",
                ),
                after=self.get_widget_by_id("top_model_variables_panel"),
            )

            # In the TextSwitch we use hardcoded False but on the other hand, we use the flag self.has_type_t to toggle the
            # switch if there is some content for the contrast tables (load, duplication case). Doing this in such a two step
            # way will automatically trigger the function _on_contrast_switch_changed same as when the user toggles the button.
            await self.mount(
                Container(
                    Static(
                        "Contrasts for the mean across all subjects, and for all variables will be generated automatically",
                        classes="instructions",
                    ),
                    Grid(
                        Static(
                            "Add additional contrasts for categorical variables", id="contrast_switch_label", classes="label"
                        ),
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

    @on(SwitchWithSelect.SwitchChanged, ".additional_preprocessing_settings")
    def _on_switch_with_select_switch_changed(self, message):
        """
        Handles changes in the switch state of a SwitchWithSelect widget.

        This method is called when the switch state changes in a
        `SwitchWithSelect` (Additional preprocessing settings) widget.
        It adds or removes variables from the model based on the switch state.

        Parameters
        ----------
        message : SwitchWithSelect.SwitchChanged
            The message object containing information about the switch
            state change.
        """
        contrast_item = {"type": "infer", "variable": [message.control.id[:-11]]}
        if message.switch_value is True:
            self.model_dict["contrasts"].append(contrast_item)
        elif contrast_item in self.model_dict["contrasts"]:
            self.model_dict["contrasts"].remove(contrast_item)

    @on(SwitchWithSelect.Changed, ".additional_preprocessing_settings")
    def _on_switch_with_select_changed(self, message):
        """
        Handles changes in the selected option of a SwitchWithSelect
        (Additional preprocessing settings) widget.

        This method is called when the selected option changes in a
        `SwitchWithSelect` widget. It selects am action for missing values
        based on the selected option.

        Parameters
        ----------
        message : SwitchWithSelect.Changed
            The message object containing information about the option
            change.
        """
        filter_item = {"type": "missing", "action": "exclude", "variable": message.control.id[:-11]}
        if message.value == "listwise_deletion" and filter_item not in self.model_dict["filters"]:
            self.model_dict["filters"].append(filter_item)
        elif message.value == "mean_substitution" and filter_item in self.model_dict["filters"]:
            self.model_dict["filters"].remove(filter_item)

    @on(SelectionList.SelectedChanged, ".level_selection")
    def _on_level_sub_panels_selection_list_changed(self, message):
        """
        Handles changes in the selection of subjects (types) levels for a categorical variable.

        This method is called when the selection changes in a
        `SelectionList` widget representing the levels of a categorical
        variable. It updates the model's filters to reflect the selected
        levels.

        Parameters
        ----------
        message : SelectionList.SelectedChanged
            The message object containing information about the selection
            change.
        """
        variable_name = message.control.id[:-6]
        all_possible_levels = [str(i) for i in list(set(self.spreadsheet_df.loc[:, variable_name]))]
        was_updated = False
        for f in self.model_dict["filters"]:
            if f.get("type") == "group" and f.get("variable") == variable_name:
                if sorted(message.control.selected) != sorted(all_possible_levels):
                    f["levels"] = sorted(message.control.selected)
                else:
                    # if there all options are selected then no levels are input to the 'levels' field in the spec file
                    self.model_dict["filters"].remove(f)
                was_updated = True

        # The filter was deleted before but now use requested some selections (and not selecting all of them), so we
        # must add the filter again.
        if sorted(message.control.selected) != sorted(all_possible_levels) and was_updated is False:
            filt_dict = {
                "type": "group",
                "action": "include",
                "variable": variable_name,
                "levels": sorted(message.control.selected),
            }
            self.model_dict["filters"].append(filt_dict)

        # When we change selection of the categorical variables, we need to close the contrast tables (if are opened)
        # This is because the tables need an update because the rows of the tables depends on the choices from the
        # level_selection widget.
        self.get_widget_by_id("contrast_switch").value = False

    @on(SelectionList.SelectedChanged, "#interaction_variables_selection_panel")
    def _on_interaction_variables_selection_list_changed(self, message):
        """
        Handles changes in the selected interaction variables.

        This method is called when the selection changes in the
        `SelectionList` widget for interaction variables. It updates the
        available interaction terms based on the selected variables.

        Parameters
        ----------
        message : SelectionList.SelectedChanged
            The message object containing information about the selection
            change.
        """
        nvar = len(message.control.selected)
        terms = list(chain.from_iterable(combinations(message.control.selected, i) for i in range(2, nvar + 1)))
        term_by_str = {" * ".join(termtpl): termtpl for termtpl in terms}
        self.get_widget_by_id("interaction_terms_selection_panel").clear_options()
        # Also delete every interaction term in the ctx.cache.
        for contrast_item in self.model_dict["contrasts"]:
            if contrast_item["type"] == "infer" and len(contrast_item["variable"]) > 1:
                self.model_dict["contrasts"].remove(contrast_item)

        self.get_widget_by_id("interaction_terms_selection_panel").add_options(
            [Selection(key, term_by_str[key], False) for key in term_by_str.keys()]
        )

    @on(SelectionList.SelectedChanged, "#interaction_terms_selection_panel")
    def _on_interaction_terms_selection_list_changed(self, message):
        """
        Handles changes in the selected interaction terms.

        This method is called when the selection changes in the
        `SelectionList` widget for interaction terms. It updates the
        model's contrasts to reflect the selected interaction terms.

        Parameters
        ----------
        message : SelectionList.SelectedChanged
            The message object containing information about the selection
            change.
        """
        # first remove all interaction terms
        self.model_dict["contrasts"] = list(
            filter(
                lambda contrast_item: not (contrast_item["type"] == "infer" and len(contrast_item["variable"]) > 1),
                self.model_dict["contrasts"],
            )
        )

        # Now add every terms that is currently selected in the widget to the cache
        for interaction_term in message.control.selected:
            self.model_dict["contrasts"].append({"type": "infer", "variable": interaction_term})

    @on(TextSwitch.Changed, "#contrast_switch")
    async def _on_contrast_switch_changed(self, message):
        """
        Handles changes in the state of the contrast switch.

        This method is called when the state of the contrast switch
        changes. It dynamically adds or removes `AdditionalContrastsCategoricalVariablesTable`
        widgets for each categorical variable based on the switch state.

        Parameters
        ----------
        message : TextSwitch.Changed
            The message object containing information about the switch
            state change.
        """
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
        """
        Handles changes in the additional contrasts table.

        This method is called when the `AdditionalContrastsCategoricalVariablesTable`
        widget changes. It updates the model's contrasts to reflect the
        changes made in the table.

        Parameters
        ----------
        message : AdditionalContrastsCategoricalVariablesTable.Changed
            The message object containing information about the table
            change.
        """
        # this will delete all previous contrasts type 't' of the particular contraste variable. This is done because
        # in the next line we fill it again based on what is actually in the table.
        self.model_dict["contrasts"] = [
            item
            for item in self.model_dict["contrasts"]
            if not (item.get("type") == "t" and item.get("variable") == [message.control.id[:-15]])
        ]
        for contrast_item in message.value:
            self.model_dict["contrasts"].append(contrast_item)
