# -*- coding: utf-8 -*-


import copy

from rich.text import Text
from textual import events, on
from textual.containers import Grid, HorizontalScroll
from textual.widget import Widget
from textual.widgets import Button


class ColorButton(Button):
    def __init__(self, color: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color
        self.styles.background = color

    async def on_click(self, event: events.Click) -> None:
        path_widget = self.app.get_widget_by_id("path_widget")
        path_widget.highlight_color = self.color


def merge_overlapping_tuples(tuples):
    # Sort the list of tuples by the start position
    sorted_tuples = sorted(tuples, key=lambda x: x[0])

    merged: list = []
    for current in sorted_tuples:
        if not merged:
            merged.append(current)
        else:
            # Compare the current tuple with the last tuple in the merged list
            last = merged[-1]
            if current[0] <= last[1]:  # Check for overlap
                # Merge the two tuples: take the min start, max end, and keep the color
                merged[-1] = (min(last[0], current[0]), max(last[1], current[1]), last[2])
            else:
                merged.append(current)

    return merged


class SegmentHighlighting(Widget):
    def __init__(
        self,
        path: str,
        colors_and_labels: dict,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        # The path text to display.
        self.colors_and_labels = colors_and_labels
        self.path = path
        self.original_path = path

    def on_mount(self):
        # Current position of the cursor within the path, starting at 0.
        self.cursor_position = 0
        # Starting index for highlight range, None means no highlight start.
        self.highlight_start_position = None
        # Flag to indicate whether the widget is in highlighting mode.
        self.is_highlighting = False
        # List to store highlight ranges (start, end) and their colors.
        self.previous_highlights = []
        self.current_highlights = []
        self.highlight_start_direction = None
        self.highlight_color = list(self.colors_and_labels.keys())[0]  # Default highlight color, start with the first one
        print("mmmmmmmmmmmmmmmmmmmmmmmmmounring")

    # Method to set the highlight color.
    #   def set_highlight_color(self, color: str):
    #      self.highlight_color = color

    # Method to add a highlight range to the path.
    def add_highlight(self, start: int, end: int, color: str):
        # Append the new highlight range and its color to the highlights list.
        self.current_highlights.append((start, end, color))
        if self.previous_highlights != []:
            self.current_highlights += self.previous_highlights
        self.current_highlights = merge_overlapping_tuples(self.current_highlights)

    # Method to move the cursor left or right.
    def move_cursor(self, direction: int):
        # Calculate new cursor position and ensure it stays within path bounds.
        self.cursor_position = max(0, min(len(self.path), self.cursor_position + direction))
        # If in highlighting mode, update the dynamic highlight based on the new cursor position.
        if self.is_highlighting:
            if self.highlight_start_direction is None:  # User started to hold shift key here
                self.highlight_start_direction = direction
            for h in self.previous_highlights:
                # cursor is within existing highlight, remove it then
                if self.cursor_position >= h[0] and self.cursor_position < h[1]:
                    self.previous_highlights.remove(h)
                    break
            if self.highlight_start_position is None:
                self.highlight_start_position = self.cursor_position - direction

            start, end = sorted([self.highlight_start_position, self.cursor_position])

            # delete current highlights since we are going to update it, what what previously
            # already highlighted is backed up in previous_highlights
            self.current_highlights = []
            # if started from right to left always do this
            if self.highlight_start_direction < 0:
                self.add_highlight(start + 1, end + 1, self.highlight_color)
            # if started from left to right always do this
            if self.highlight_start_direction > 0:
                self.add_highlight(start, end, self.highlight_color)
        else:
            self.previous_highlights = copy.deepcopy(self.current_highlights)
            self.highlight_start_position = None
            self.highlight_start_direction = None
        self.refresh()

    def reset_highlights(self):
        # clear all highlights
        self.path = self.original_path
        self.previous_highlights.clear()
        self.current_highlights.clear()
        self.refresh()

    def submit_path(self):
        start_offset = 0
        end_offset = 0
        highlights = copy.deepcopy(self.current_highlights)
        self.reset_highlights()
        for start, end, color in sorted(highlights, reverse=False, key=lambda x: x[0]):
            label = self.colors_and_labels[color]
            # calculate by how much longer/shorter is the replacement string, this varies from label to label
            extra = len(label) + 2 - (end - start)
            self.path = self.path[: start + start_offset] + "{" + label + "}" + self.path[end + end_offset :]
            end_offset += extra
            self.add_highlight(start + start_offset, end + end_offset, color)
            start_offset += extra
        self.refresh()

    def render(self) -> Text:
        text = Text()
        last_idx = 0  # Keep track of the last index processed for inserting unhighlighted text.
        # Apply all stored highlights to the path.
        for start, end, color in sorted(self.current_highlights, key=lambda x: x[0]):
            # Add text up to the start of the current highlight.
            if start > last_idx:
                text.append(self.path[last_idx:start])
            # Add the highlighted text.
            text.append(self.path[start:end], style=f"on {color}")
            last_idx = end
        # Add any remaining unhighlighted text at the end of the path.
        if last_idx < len(self.path):
            text.append(self.path[last_idx:])
        # Append an underline style to render the cursor, adding a space if at the end.
        if self.cursor_position == len(self.path):
            text.append(" ", style="none underline")
        else:
            text.stylize("underline", self.cursor_position, self.cursor_position + 1)
        return text


class PathSegmentHighlighter(Widget):
    def __init__(
        self,
        path: str,
        highlight_colors=None,
        labels=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.path = path
        self.highlight_colors = ["red", "green", "blue", "yellow", "magenta"] if highlight_colors is None else highlight_colors
        self.labels = ["Subject", "Session", "Run", "Acquisition"] if labels is None else labels

    def compose(self):
        colors_and_labels = dict(zip(self.highlight_colors, self.labels, strict=False))
        yield Grid(
            *[
                ColorButton(label=item[1], color=item[0], id="button_" + item[1], classes="color_buttons")
                for item in colors_and_labels.items()
            ]
        )
        yield HorizontalScroll(
            SegmentHighlighting(self.path, id="path_widget", colors_and_labels=colors_and_labels), id="path_widget_container"
        )
        yield Grid(Button("Reset", id="reset_button"), Button("Submit", id="submit_button"))

    def on_mount(self):
        # active button at start
        print("mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmn")
        self.activate_pressed_button("button_" + self.labels[0])

    def deactivate_pressed_button(self):
        if self.active_button_id is not None:
            self.get_widget_by_id(self.active_button_id).remove_class("activated")

    def activate_pressed_button(self, _id):
        clicked_color_button = self.get_widget_by_id(_id)
        clicked_color_button.add_class("activated")
        self.active_button_id = _id

    def key_enter(self):
        self.get_widget_by_id("path_widget").submit_path()

    def key_escape(self):
        self.get_widget_by_id("path_widget").reset_highlights()

    @on(Button.Pressed, "#reset_button")
    def reset_highlights(self):
        self.get_widget_by_id("path_widget").reset_highlights()

    @on(Button.Pressed, "#submit_button")
    def submit_highlights(self):
        self.get_widget_by_id("path_widget").submit_path()

    @on(Button.Pressed, ".color_buttons")
    def activate_and_deactivate_press(self, event: Button.Pressed):
        self.deactivate_pressed_button()
        self.activate_pressed_button(event.button.id)

    # Handles keyboard events to move the cursor and toggle highlighting mode.
    async def on_key(self, event: events.Key):
        path_widget = self.get_widget_by_id("path_widget")
        if event.key in ["1", "2", "3", "4", "5"]:
            # Set highlight color based on key pressed.
            index = int(event.key) - 1
            path_widget.highlight_color = self.highlight_colors[index]
            self.deactivate_pressed_button()
            self.activate_pressed_button("button_" + self.labels[index])

        elif event.key == "shift+left" or event.key == "shift+right":
            # Enters highlighting mode and moves the cursor.
            path_widget.is_highlighting = True
            direction = -1 if event.key == "shift+left" else 1
            path_widget.move_cursor(direction)
            path_widget.is_highlighting = False
        elif event.key in ["left", "right"]:
            # Moves the cursor without highlighting.
            direction = -1 if event.key == "left" else 1
            path_widget.is_highlighting = False
            path_widget.move_cursor(direction)
            path_widget.is_highlighting = False


# class Main(App):
# CSS_PATH = ['./tcss/path_segment_highlighter.tcss']

# def compose(self):
# yield PathSegmentHighlighter(path="/home/tomas/github/ds002785_v2/sub-0001/anat/sub-0001_T1w.nii.gz")


# if __name__ == "__main__":
# app = Main()
# app.run()
