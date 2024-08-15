# -*- coding: utf-8 -*-
from typing import Any

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Grid, Horizontal
from textual.geometry import Offset
from textual.reactive import var
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class WindowTitleBar(Container):
    """A title bar widget. Taken from textual_paint"""

    DEFAULT_CSS = """
        WindowTitleBar {
            layout: horizontal;
            width: auto;
            height: 3;
            background: $accent;
            color: auto;
            text-style: bold;
        }

        WindowTitleBar Button {
            max-width: 6;
            height: 3;
            padding-top: 0;
            padding-left: 0;
            background: $accent;
            border: none;
        }

        WindowTitleBar Button:hover {
            border: none;
            border-top: none;
            border-bottom: none;
            background: $accent;
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
        allow_minimize: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize a title bar."""
        super().__init__(**kwargs)
        self.title = title
        self.allow_maximize = allow_maximize
        self.allow_minimize = allow_minimize

    def compose(self) -> ComposeResult:
        """Add our widgets."""
        yield Static(self.title, classes="window_title")
        if self.allow_minimize:
            yield Button(self.MINIMIZE_ICON, classes="window_minimize")
        if self.allow_maximize:
            yield Button(self.MAXIMIZE_ICON, classes="window_maximize")
            restore_button = Button(self.RESTORE_ICON, classes="window_restore")
            restore_button.display = False
            yield restore_button
        yield Button(self.CLOSE_ICON, classes="window_close")


class DraggableModalScreen(ModalScreen):
    """Inspired from textual_paint"""

    DEFAULT_CSS = """
        DraggableModalScreen {
            align: center middle;
         }

        #draggable_modal_screen_container_wrapper {
            width: auto;
            height: auto;
            border-left: thick $accent;
            border-right: thick $accent;
            border-bottom: thick $accent;
        }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_bar = WindowTitleBar(id="window_title_bar")
        self.content = Container(self.title_bar, id="draggable_modal_screen_container_wrapper", classes="window_content")

        # mouse_at_drag_start also servers as "is dragging"
        self.mouse_at_drag_start: Offset | None = None

    # print("IIIIIIIIIIINIT Super DraggableModalScreen")

    def on_resize(self):
        print(
            'wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww self.title_bar.query_one(".window_title").styles.width ',
            self.title_bar.query_one(".window_title").styles.width,
        )
        print(
            "wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww draggable_modal_screen_container_wrapper ",
            self.get_widget_by_id("draggable_modal_screen_container_wrapper").container_size,
        )
        self.get_widget_by_id("window_title_bar").styles.width = self.get_widget_by_id(
            "draggable_modal_screen_container_wrapper"
        ).container_size.width
        print("ssssss", self._size)

    def compose(self) -> ComposeResult:
        #  yield Container(self.title_bar, self.content, id="draggable_modal_screen_container_wrapper")
        #      yield self.title_bar
        yield self.content

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Called when the user moves the mouse."""
        window = self.get_widget_by_id("draggable_modal_screen_container_wrapper")
        if self.mouse_at_drag_start is not None:
            # position of the modal at the drag start + current mouse position - mouse position at drag start
            window.styles.offset = (
                self.offset_at_drag_start.x + event.screen_x - self.mouse_at_drag_start.x,
                self.offset_at_drag_start.y + event.screen_y - self.mouse_at_drag_start.y,
            )

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Called when the user presses the mouse button."""
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
        """Called when the user releases the mouse button."""
        self.mouse_at_drag_start = None
        self.release_mouse()
        self.can_focus = True

    @on(Button.Pressed, ".window_close")
    def request_close(self):
        self.dismiss(False)


class FalseInputWarningTest(DraggableModalScreen):
    DEFAULT_CSS = """
        FalseInputWarningTest {
            Grid {
                grid-size:1 2;
                grid-rows: 1fr 3;
                padding: 0 1;
                width: 40;
                height: 11;
                border: thick $warning;
                background: $surface;
            }
            Label {
                height: 1fr;
                width: 1fr;
                content-align: center middle;
                color: $warning;
            }
            Horizontal {
                align: center middle;
            }
            Button {
                width: 50%;
            }
        }
    """

    def __init__(self, warning_message) -> None:
        self.warning_message = warning_message
        super().__init__()

    # the self.content.mount serves now similarly as the "compose"
    def on_mount(self) -> None:
        """Called when the window is mounted."""
        self.content.mount(
            Grid(
                Label(self.warning_message),
                Horizontal(Button("Ok", variant="warning", id="ok_button")),
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok_button":
            self.dismiss(None)

    def key_escape(self):
        self.dismiss(None)
