from dataclasses import dataclass

from rich.text import Text
from textual import on
from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button

from ..data_analyzers.file_pattern_steps import (
    MatEventsStep,
    TsvEventsStep,
    TxtEventsStep,
)
from ...specialized_widgets.non_bids_file_itemization import FileItem


class FilePanelTemplate(Widget):
    """
    A template class for creating panels that manage a collection of files.

    This class provides a base structure for creating panels that allow
    users to add, manage, and interact with a list of files. It includes
    functionality for adding new file items, handling file item deletion,
    and updating the panel's state.

    Attributes
    ----------
    _counter : ClassVar[int]
        A class-level counter to keep track of the number of file patterns.
    class_name : ClassVar[str | None]
        The name of the class, used for identification.
    id_string : ClassVar[str]
        The ID string used to identify the panel in the UI.
    file_item_id_base : ClassVar[str]
        The base ID used for generating unique IDs for file items.
    the_class : ClassVar[Type["FilePanelTemplate"] | None]
        A reference to the class itself.
    pattern_class : ClassVar[Type[Any] | None]
        The class used for creating file pattern steps.
    current_file_pattern_id : str | None
        The ID of the currently active file pattern.
    value : reactive[bool]
        A reactive attribute that indicates whether the panel's state has changed.

    Methods
    -------
    __init__(id, classes)
        Initializes the FilePanelTemplate instance.
    callback_func(message_dict)
        Processes a message dictionary and formats text messages for callback.
    watch_value()
        Posts a message when the value changes.
    compose() -> ComposeResult
        Composes the widget's components.
    _on_button_add_file_item_pressed()
        Handles the event when the add file item button is pressed.
    add_file_item_pressed()
        Initiates the creation of a new file item.
    create_file_item(load_object, message_dict)
        Creates and mounts a new file item widget.
    on_mount()
        Handles actions upon mounting the panel to the application.
    _on_file_item_is_deleted(message)
        Handles the event when a file item is deleted.
    _on_update_all_instances(event)
        Updates instances when a file item is finished or its path pattern changes.
    reset_all_counters()
        Recursively reset counters for all subclasses.
    """

    # A class-level counter to keep track of the number of file patterns.
    _counter = 0
    # The name of the class, used for identification.
    class_name: None | str = None
    # The ID string used to identify the panel in the UI.
    id_string: str = ""
    # The base ID used for generating unique IDs for file items.
    file_item_id_base: str = ""
    # A reference to the class itself.
    the_class = None
    # The class used for creating file pattern steps.
    pattern_class: type | None = None
    # The ID of the currently active file pattern.
    current_file_pattern_id = None
    # A reactive attribute that indicates whether the panel's state has changed.
    value: reactive[bool] = reactive(None, init=False)

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

    def __init__(self, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes the FilePanelTemplate instance.

        Parameters
        ----------
        id : str, optional
            An optional identifier for the widget, by default None.
        classes : str, optional
            An optional string of classes for applying styles to the
            widget, by default None.
        """
        super().__init__(id=id, classes=classes)
        type(self).the_class = self.__class__  # Sets the_class at the class level
        self.the_app = self.app

        cls = type(self)  # Get the actual class of the instance
        if not hasattr(cls, "_counter"):  # Ensure each child class has its own counter
            cls._counter = 0
        self.file_pattern_counter = cls._counter

    def callback_func(self, message_dict):
        """
        Processes a message dictionary and formats text messages for callback.

        This method takes a dictionary of messages, formats them into a
        rich text string, and stores the result in the `callback_message`
        attribute.

        Parameters
        ----------
        message_dict : dict[str, list[str]]
            A dictionary where keys are message categories and values are
            lists of messages.
        """
        info_string = Text("")
        for key in message_dict:
            if len(message_dict[key]) <= 1:
                sep_char = ""
                separ_line = "-" * (len(key) + len(message_dict[key][0]) + 3)
            else:
                sep_char = "\n"
                separ_line = "-" * (max([len(s) for s in [key] + message_dict[key]]) + 3)
            info_string += Text(key + ": " + sep_char, style="bold green") + Text(
                " ".join(message_dict[key]) + separ_line + "\n", style="white"
            )

        self.callback_message = info_string

    def watch_value(self) -> None:
        """
        Posts a message when the value changes.

        This method is called when the `value` attribute changes. It posts
        a `Changed` message to notify other parts of the application about
        the change.
        """
        self.post_message(self.Changed(self, self.value))

    def compose(self):
        """
        Composes the widget's components.

        This method defines the layout and components of the widget,
        including a vertical scroll container and an "Add" button.

        Yields
        ------
        VerticalScroll
            The composed widgets.
        """
        yield VerticalScroll(Button("Add", id="add_file_button"), id=self.id_string)

    @on(Button.Pressed, "#add_file_button")
    async def _on_button_add_file_item_pressed(self):
        """
        Handles the event when the add file item button is pressed.

        This method is called when the user presses the "Add" button. It
        calls `add_file_item_pressed` to initiate the creation of a new
        file item.
        """
        await self.add_file_item_pressed()

    async def add_file_item_pressed(self):
        """
        Initiates the creation of a new file item.

        This method is called when the user wants to add a new file item.
        It calls `create_file_item` to create and mount the new file item
        widget.
        """
        await self.create_file_item(load_object=None)

    async def create_file_item(self, load_object=None, message_dict=None):
        """
        Creates and mounts a new file item widget.

        This method creates a new `FileItem` widget, mounts it to the
        panel, and updates the panel's state. It handles both the case
        where a new file item is being added and the case where a file
        item is being loaded from existing data.

        Parameters
        ----------
        load_object : Any, optional
            An object containing data to load into the file item, by
            default None.
        message_dict : dict[str, list[str]] | None, optional
            A dictionary of messages to display in the file item, by
            default None.

        Returns
        -------
        str | None
            The ID of the newly created file item, or None if the file
            item could not be created.
        """

        async def mount_file_item_widget():
            if self.the_class is not None and self.pattern_class is not None:
                the_file_item = FileItem(
                    id=self.file_item_id_base + str(self.file_pattern_counter),
                    classes="file_patterns",
                    pattern_class=self.pattern_class(app=self.app, callback=self.callback_func),
                )
                # regular FileItem mount when user clicks "Add" and creates the file pattern
                await self.get_widget_by_id(self.id_string).mount(the_file_item)
                self.current_file_pattern_id = self.file_item_id_base + str(self.file_pattern_counter)

                self.file_pattern_counter += 1
                self.refresh()

        if load_object is None:
            await mount_file_item_widget()
        else:
            # Mounting, for example, when loading the spec file
            if self.the_class is not None:
                # EventFilePanel has pattern_class=None by default, since when user is adding it, he/she is prompt to
                # specify the type. However, if loading from a spec file, we need to determine this by the extension of the
                # item in the spec file
                if self.pattern_class is None:
                    extension_mapping = {".tsv": TsvEventsStep, ".mat": MatEventsStep, ".txt": TxtEventsStep}
                    self.pattern_class = extension_mapping.get(load_object.__dict__["extension"])

                if self.pattern_class is not None:
                    await self.get_widget_by_id(self.id_string).mount(
                        FileItem(
                            id=self.file_item_id_base + str(self.file_pattern_counter),
                            classes="file_patterns",
                            load_object=load_object,
                            message_dict=message_dict,
                            pattern_class=self.pattern_class(app=self.app, callback=self.callback_func),
                            execute_pattern_class_on_mount=False,
                        )
                    )

                self.current_file_pattern_id = self.file_item_id_base + str(self.file_pattern_counter)
                self.file_pattern_counter += 1
        return self.current_file_pattern_id

    def on_mount(self):
        """
        Handles actions upon mounting the panel to the application.

        This method is called when the panel is mounted to the application.
        It handles the case where a new feature is added and copies the
        file items from the first feature's panel to the new panel.
        """
        # use first event file panel widget to make copies for the newly created one
        if self.app.walk_children(self.the_class) != []:
            first_file_panel_widget = self.app.walk_children(self.the_class)[0]
            # only use if it is not the first one!
            if first_file_panel_widget != self:
                for file_item_widget in first_file_panel_widget.walk_children(FileItem):
                    # mounting FileItems when a new Feature is added, this basically copies FileItems from the
                    # very first Feature
                    self.get_widget_by_id(self.id_string).mount(
                        FileItem(
                            id=file_item_widget.id,
                            classes="file_patterns",
                            load_object=file_item_widget.get_pattern_match_results,
                            callback_message=file_item_widget.get_callback_message,
                            pattern_class=file_item_widget.get_pattern_class,
                            execute_pattern_class_on_mount=False,
                        )
                    )

    @on(FileItem.IsDeleted)
    async def _on_file_item_is_deleted(self, message):
        """
        Handles the event when a file item is deleted.

        This method is called when a `FileItem.IsDeleted` message is
        received. It removes the deleted file item from the panel and
        posts a `FileItemIsDeleted` message to notify other parts of the
        application.

        Parameters
        ----------
        message : FileItem.IsDeleted
            The message object containing information about the deleted
            file item.
        """
        message.control.remove()
        self.post_message(self.FileItemIsDeleted(self, message.control.id))

    @on(FileItem.IsFinished)
    @on(FileItem.PathPatternChanged)
    async def _on_update_all_instances(self, event) -> None:
        """
        Updates instances when a file item is finished or its path pattern changes.

        This method is called when a `FileItem.IsFinished` or
        `FileItem.PathPatternChanged` message is received. It updates the
        panel's `value` attribute to indicate that the panel's state has
        changed.

        Parameters
        ----------
        event : FileItem.IsFinished | FileItem.PathPatternChanged
            The message object containing information about the event.
        """
        self.value = event.value

    @classmethod
    def reset_all_counters(cls):
        """
        Recursively reset counters for all subclasses.

        This method resets the `_counter` attribute for the class and all
        its subclasses. It is used to ensure that file item IDs are
        unique across different instances of the panel.
        """
        for subclass in cls.__subclasses__():
            subclass._counter = 0
            subclass.reset_all_counters()  # Reset for deeper subclasses if any
        cls._counter = 0  # Reset the parent class counter
