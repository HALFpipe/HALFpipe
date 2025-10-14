# -*- coding: utf-8 -*-
from typing import Any

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container
from textual.geometry import Offset
from textual.reactive import var
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class WindowTitleBar(Container):
    """
    Represents a draggable window title bar.

    This class creates a title bar for a draggable window, including
    options for displaying a title, and close buttons. Minimize, maximize and restore
    are not available currently.

    Attributes
    ----------
    DEFAULT_CSS : str
        The default CSS styling for the `WindowTitleBar` and its child
        elements.
    MINIMIZE_ICON : str
        The Unicode icon representing the minimize button.
    MAXIMIZE_ICON : str
        The Unicode icon representing the maximize button.
    RESTORE_ICON : str
        The Unicode icon representing the restore button.
    CLOSE_ICON : str
        The Unicode icon representing the close button.
    title : var[str]
        The title text displayed on the title bar.
    ALLOW_MAXIMIZE : bool
        Flag to indicate whether a maximize button should be added.

    Methods
    -------
    __init__(title, allow_maximize, id, classes)
        Initializes the `WindowTitleBar` instance.
    compose() -> ComposeResult
        Composes the widgets to be added to the title bar.
    """

    DEFAULT_CSS = """
        WindowTitleBar {
            layout: horizontal;
            width: 100%;
            height: 3;
            background: $primary;
            color: auto;
            text-style: bold;
        }

        WindowTitleBar Button {
            max-width: 6;
            height: 3;
            padding-top: 0;
            padding-left: 0;
            background: $primary;
            border: none;
        }

        WindowTitleBar Button:hover {
            border: none;
            border-top: none;
            border-bottom: none;
            background: $primary;
            color: black;
            border: thick black;
        }

        WindowTitleBar Button:focus {
                text-style: none;
        }

        .window_title {
            width: 1fr;
            height: 100%;
            content-align: left middle;
            padding-left: 1;
        }
    """

    MINIMIZE_ICON = "🗕"
    MAXIMIZE_ICON = "🗖"
    RESTORE_ICON = "🗗"
    CLOSE_ICON = "✕"

    title = var("")

    def __init__(
        self,
        title: str = "",
        allow_maximize: bool = False,
        # allow_minimize: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Initializes the WindowTitleBar instance.

        Parameters
        ----------
        title : str, optional
            The title text to be displayed on the title bar, by default "".
        allow_maximize : bool, optional
            Flag to indicate whether a maximize button should be added,
            by default False.
        id : str | None, optional
            The ID of the widget, by default None.
        classes : str | None, optional
            CSS classes for the widget, by default None.
        **kwargs : Any
            Additional keyword arguments.
        """
        super().__init__(**kwargs)
        self.title = title
        self.ALLOW_MAXIMIZE = allow_maximize
        # self.allow_minimize = allow_minimize

    def compose(self) -> ComposeResult:
        """Add our widgets."""
        yield Static(self.title, classes="window_title")
        # if self.allow_minimize:
        #     yield Button(self.MINIMIZE_ICON, classes="window_minimize")
        if self.allow_maximize:
            yield Button(self.MAXIMIZE_ICON, classes="window_maximize")
            restore_button = Button(self.RESTORE_ICON, classes="window_restore")
            restore_button.display = False
            yield restore_button
        close_button = Button(self.CLOSE_ICON, classes="window_close")
        close_button.can_focus = False
        yield close_button


class DraggableModalScreen(ModalScreen):
    """
    Represents a draggable modal screen.

    This class creates a modal screen that can be dragged around the
    application window by the user. It includes a title bar and content
    area.

    Attributes
    ----------
    DEFAULT_CSS : str
        Default CSS styling for the draggable modal screen and its
        container.
    title_bar : WindowTitleBar
        The title bar widget for the modal screen.
    content : Container
        The container for the content of the modal screen.
    mouse_at_drag_start : Offset | None
        The mouse position at the start of a drag operation.
    offset_at_drag_start : Offset | None
        The modal's offset at the start of a drag operation.

    Methods
    -------
    __init__(id, classes)
        Initializes a new `DraggableModalScreen` instance.
    on_resize()
        Adjusts the width of the window title bar when the screen is
        resized.
    compose() -> ComposeResult
        Composes the components of the modal screen.
    on_mouse_move(event)
        Called when the user moves the mouse.
    on_mouse_down(event)
        Called when the user presses the mouse button.
    on_mouse_up(event)
        Called when the user releases the mouse button.
    windown_close()
        Handles the event when the close button is pressed.
    request_close()
        Requests the modal screen to close.
    """

    # DEFAULT_CSS = """
    #     DraggableModalScreen {
    #         align: center middle;
    #      }
    #
    #     #draggable_modal_screen_container_wrapper {
    #         width: auto;
    #         height: auto;
    #         border-left: thick $primary;
    #         border-right: thick $primary;
    #         border-bottom: thick $primary;
    #     }
    #
    # """

    def __init__(self, id: str | None = None, classes: str | None = None) -> None:
        """
        Initializes a new DraggableModalScreen instance.

        Parameters
        ----------
        id : str | None, optional
            The unique identifier for the modal screen, by default None.
        classes : str | None, optional
            One or more CSS classes to apply to the modal screen,
            by default None.
        """
        super().__init__(id=id, classes=classes)
        self.title_bar = WindowTitleBar(id="window_title_bar")
        self.content = Container(self.title_bar, id="draggable_modal_screen_container_wrapper", classes="window_content")

        # mouse_at_drag_start also servers as "is dragging"
        self.mouse_at_drag_start: Offset | None = None
        self.set_focus(None)

    def on_resize(self):
        """
        Adjusts the width of the window title bar when the screen is resized.

        This method is called when the screen is resized. It updates the
        width of the title bar to match the width of the content container.
        """
        self.get_widget_by_id("window_title_bar").styles.width = self.get_widget_by_id(
            "draggable_modal_screen_container_wrapper"
        ).container_size.width

    def compose(self) -> ComposeResult:
        yield self.content

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """
        Called when the user moves the mouse.

        This method handles the mouse move event to enable dragging of the
        modal screen. It calculates the window offset based on the current
        mouse coursor position.

        Parameters
        ----------
        event : events.MouseMove
            The event object containing details about the mouse movement.
        """
        window = self.get_widget_by_id("draggable_modal_screen_container_wrapper")
        if self.mouse_at_drag_start is not None:
            # position of the modal at the drag start + current mouse position - mouse position at drag start
            window.styles.offset = (
                self.offset_at_drag_start.x + event.screen_x - self.mouse_at_drag_start.x,
                self.offset_at_drag_start.y + event.screen_y - self.mouse_at_drag_start.y,
            )

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """
        Called when the user presses (and holds) the mouse button.

        This method handles the mouse down event to initiate dragging of
        the modal screen.

        Parameters
        ----------
        event : events.MouseDown
            The event object containing details about the mouse down action.
        """
        window = self.get_widget_by_id("draggable_modal_screen_container_wrapper")
        window.focus()

        # what widget is currently at the mouse coursor position and left mouse button is used
        widget, _ = self.screen.get_widget_at(*event.screen_offset)
        if widget != self.title_bar.query_one(".window_title") or event.button != 1:
            return

        # mouse position at drag start
        self.mouse_at_drag_start = event.screen_offset
        self.offset_at_drag_start = Offset(
            int(window.styles.offset.x.value),
            int(window.styles.offset.y.value),
        )
        self.capture_mouse()
        self.can_focus = False

    def on_mouse_up(self, event: events.MouseUp) -> None:
        """
        Called when the user releases the mouse button.

        This method handles the mouse up event to stop dragging of the
        modal screen.

        Parameters
        ----------
        event : events.MouseUp
            The event object containing details about the mouse up action.
        """
        self.mouse_at_drag_start = None
        self.release_mouse()
        self.can_focus = True

    @on(Button.Pressed, ".window_close")
    def windown_close(self):
        """
        Handles the event when the close button is pressed.

        This method is called when the close button in the title bar is
        pressed. It requests the modal screen to close.
        """
        self.request_close()

    def request_close(self):
        """
        Requests the modal screen to close.

        This method dismisses the modal screen.
        """
        self.dismiss(False)
