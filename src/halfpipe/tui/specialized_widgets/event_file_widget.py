# -*- coding: utf-8 -*-


from ..data_analyzers.file_pattern_steps import (
    AddAtlasImageStep,
    AddBinarySeedMapStep,
    AddSpatialMapStep,
    MatEventsStep,
    TsvEventsStep,
    TxtEventsStep,
)
from ..general_widgets.selection_modal import SelectionModal
from ..templates.file_panel_template import FilePanelTemplate


class EventFilePanel(FilePanelTemplate):
    """
    A panel for managing event file patterns.

    This class extends `FilePanelTemplate` to provide a panel specifically
    for managing event file patterns. It allows users to add event files
    of different types (SPM, FSL, BIDS) and configure their associated
    patterns.

    Attributes
    ----------
    class_name : ClassVar[str]
        The name of the class, set to "EventFilePanel".
    id_string : ClassVar[str]
        The ID string for the panel, set to "event_file_panel".
    file_item_id_base : ClassVar[str]
        The base ID for file items in this panel, set to
        "event_file_pattern_".
    pattern_class : ClassVar[type | None]
        The class used for creating file pattern steps, initially None.

    Methods
    -------
    add_file_item_pressed()
        Handles the event when the add file item button is pressed.
    """

    # The name of the class, set to "EventFilePanel".
    class_name = "EventFilePanel"
    # The ID string for the panel, set to "event_file_panel".
    id_string = "event_file_panel"
    # The base ID for file items in this panel, set to "event_file_pattern_".
    file_item_id_base = "event_file_pattern_"
    # The class used for creating file pattern steps, initially None.
    pattern_class = None

    async def add_file_item_pressed(self):
        """
        Handles the event when the add file item button is pressed.

        This method is called when the user wants to add a new event file
        item. It pushes a `SelectionModal` onto the screen to allow the
        user to select the type of event file (SPM, FSL, or BIDS). After
        the user makes a selection, it sets the `pattern_class` attribute
        and calls `create_file_item` to create and mount the new file item
        widget.
        """

        async def proceed_with_choice(choice):
            """
            Proceeds with the creation of a file item based on the user's choice.

            This method is called after the user has selected an event file
            type in the `SelectionModal`. It maps the user's choice to the
            appropriate `pattern_class` and then calls `create_file_item`
            to create and mount the new file item widget.

            Parameters
            ----------
            choice : str | bool
                The user's choice of event file type, or False if the
                selection was canceled.
            """
            if choice is not False:
                options_class_map = {"spm": MatEventsStep, "fsl": TxtEventsStep, "bids": TsvEventsStep}
                self.pattern_class = options_class_map[choice]
                await self.create_file_item(load_object=None)

        options = {
            "spm": "SPM multiple conditions",
            "fsl": "FSL 3-column",
            "bids": "BIDS TSV",
        }
        self.app.push_screen(
            SelectionModal(
                title="Event file type specification",
                instructions="Specify the event file type",
                options=options,
                id="event_files_type_modal",
            ),
            proceed_with_choice,
        )

    filedict = {"datatype": "func", "suffix": "events"}


class AtlasFilePanel(FilePanelTemplate):
    """
    A panel for managing atlas file patterns.

    This class extends `FilePanelTemplate` to provide a panel specifically
    for managing atlas file patterns. It allows users to add atlas files
    and configure their associated patterns.

    Attributes
    ----------
    class_name : ClassVar[str]
        The name of the class, set to "AtlasFilePanel".
    id_string : ClassVar[str]
        The ID string for the panel, set to "atlas_file_panel".
    file_item_id_base : ClassVar[str]
        The base ID for file items in this panel, set to
        "atlas_file_pattern_".
    pattern_class : ClassVar[type]
        The class used for creating file pattern steps, set to
        `AddAtlasImageStep`.
    """

    # The name of the class, set to "AtlasFilePanel".
    class_name = "AtlasFilePanel"
    # The ID string for the panel, set to "atlas_file_panel".
    id_string = "atlas_file_panel"
    # The base ID for file items in this panel, set to "atlas_file_pattern_".
    file_item_id_base = "atlas_file_pattern_"
    # The class used for creating file pattern steps, set to `AddAtlasImageStep`.
    pattern_class = AddAtlasImageStep
    filters: dict[str, str] = {"datatype": "ref", "suffix": "atlas"}


class SeedMapFilePanel(FilePanelTemplate):
    """
    A panel for managing seed map file patterns.

    This class extends `FilePanelTemplate` to provide a panel specifically
    for managing seed map file patterns. It allows users to add seed map
    files and configure their associated patterns.

    Attributes
    ----------
    class_name : ClassVar[str]
        The name of the class, set to "SeedMapFilePanel".
    id_string : ClassVar[str]
        The ID string for the panel, set to "seed_map_file_panel".
    file_item_id_base : ClassVar[str]
        The base ID for file items in this panel, set to
        "seed_map_file_pattern_".
    pattern_class : ClassVar[type]
        The class used for creating file pattern steps, set to
        `AddBinarySeedMapStep`.
    """

    # The name of the class, set to "SeedMapFilePanel".
    class_name = "SeedMapFilePanel"
    # The ID string for the panel, set to "seed_map_file_panel".
    id_string = "seed_map_file_panel"
    # The base ID for file items in this panel, set to "seed_map_file_pattern_".
    file_item_id_base = "seed_map_file_pattern_"
    # The class used for creating file pattern steps, set to `AddBinarySeedMapStep`.
    pattern_class = AddBinarySeedMapStep
    filters: dict[str, str] = {"datatype": "ref", "suffix": "seed"}


class SpatialMapFilePanel(FilePanelTemplate):
    """
    A panel for managing spatial map file patterns.

    This class extends `FilePanelTemplate` to provide a panel specifically
    for managing spatial map file patterns. It allows users to add spatial
    map files and configure their associated patterns.

    Attributes
    ----------
    class_name : ClassVar[str]
        The name of the class, set to "SpatialMapFilePanel".
    id_string : ClassVar[str]
        The ID string for the panel, set to "spatial_map_file_panel".
    file_item_id_base : ClassVar[str]
        The base ID for file items in this panel, set to
        "spatial_map_file_pattern_".
    pattern_class : ClassVar[type]
        The class used for creating file pattern steps, set to
        `AddSpatialMapStep`.
    """

    # The name of the class, set to "SpatialMapFilePanel".
    class_name = "SpatialMapFilePanel"
    # The ID string for the panel, set to "spatial_map_file_panel".
    id_string = "spatial_map_file_panel"
    # The base ID for file items in this panel, set to "spatial_map_file_pattern_".
    file_item_id_base = "spatial_map_file_pattern_"
    # The class used for creating file pattern steps, set to `AddSpatialMapStep`.
    pattern_class = AddSpatialMapStep
    filters: dict[str, str] = {"datatype": "ref", "suffix": "map"}
