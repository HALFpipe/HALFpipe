# -*- coding: utf-8 -*-

from textual import on
from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Button, Static

from .draggable_modal_screen import DraggableModalScreen


class ListOfFiles(DraggableModalScreen):
    """
    Displays a modal screen with a list of files matching a certain pattern.

    This class extends `DraggableModalScreen` to create a modal window
    that displays a list of files that match a specified pattern. It
    includes a message describing the pattern match results and a
    scrollable list of the matching files.

    Attributes
    ----------
    pattern_match_results : dict[str, str | list[str]]
        A dictionary containing the pattern match results.
        It should have the following keys:
        - "message": A string describing the pattern match results.
        - "files": A list of strings, where each string is a file path
          that matches the pattern.

    Methods
    -------
    __init__(pattern_match_results, id, classes)
        Initializes the `ListOfFiles` modal screen.
    on_mount()
        Mounts the content of the modal screen, including the message,
        the scrollable list of files, and the close button.
    _on_close_button_pressed()
        Handles the event when the close button is pressed, dismissing
        the modal screen.
    """

    def __init__(self, pattern_match_results, **kwargs) -> None:
        """
        Initializes the ListOfFiles modal screen.

        Parameters
        ----------
        pattern_match_results : dict[str, str | list[str]]
            A dictionary containing the pattern match results.
            It should have the following keys:
            - "message": A string describing the pattern match results.
            - "files": A list of strings, where each string is a file path
              that matches the pattern.
        id : str | None, optional
            The ID of the widget, by default None.
        classes : str | None, optional
            CSS classes for the widget, by default None.
        """
        super().__init__(**kwargs)
        self.pattern_match_results = pattern_match_results
        self.title_bar.title = "List of matching files"

    def on_mount(self) -> None:
        self.content.mount(
            Static(self.pattern_match_results["message"], id="message"),
            ScrollableContainer(Static("\n".join(sorted(self.pattern_match_results["files"])), id="file_list")),
            Horizontal(Button("Close", id="close_button"), id="close_button_container"),
        )

    @on(Button.Pressed, "#close_button")
    def _on_close_button_pressed(self):
        self.app.pop_screen()
