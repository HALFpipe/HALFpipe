# -*- coding: utf-8 -*-
from math import ceil
from typing import ClassVar, Type

from rich.color import Color
from rich.console import RenderableType
from rich.segment import Segment, Segments
from rich.style import Style
from textual.scrollbar import ScrollBarRender
from textual.widget import Widget
from textual.widgets._switch import Switch  # Make sure this import path is correct based on your project structure


class MyScrollBarRender(ScrollBarRender):
    """
    Renders the scrollbar with ON/OFF text. For more see ScrollBarRender.
    """

    @classmethod
    def render_bar(
        cls,
        size: int = 25,
        virtual_size: float = 100,
        window_size: float = 20,
        position: float = 0,
        thickness: int = 1,
        vertical: bool = True,
        back_color: Color = Color.parse("#555555"),  # noqa B008
        bar_color: Color = Color.parse("bright_magenta"),  # noqa B008
    ) -> Segments:
        if vertical:
            bars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "OK"]
        else:
            bars = ["▉", "▊", "▋", "▌", "▍", "▎", "▏", " "]

        back = back_color
        bar = bar_color

        len_bars = len(bars)

        width_thickness = thickness if vertical else 1

        _Segment = Segment  # noqa N806
        _Style = Style  # noqa N806
        blank = " " * width_thickness

        if position == 50:
            is_on = True
        else:
            is_on = False
        if position == 0:
            is_off = True
        else:
            is_off = False

        foreground_meta = {"@mouse.down": "grab"}
        if window_size and size and virtual_size and size != virtual_size:
            bar_ratio = virtual_size / size
            thumb_size = max(1, window_size / bar_ratio)

            position_ratio = position / (virtual_size - window_size)
            position = (size - thumb_size) * position_ratio

            start = int(position * len_bars)
            end = start + ceil(thumb_size * len_bars)

            start_index, start_bar = divmod(max(0, start), len_bars)
            end_index, end_bar = divmod(max(0, end), len_bars)

            upper = {"@mouse.up": "scroll_up"}
            lower = {"@mouse.up": "scroll_down"}

            upper_back_segment = Segment(blank, _Style(bgcolor=back, meta=upper))
            lower_back_segment = Segment(blank, _Style(bgcolor=back, meta=lower))
            segments = [upper_back_segment] * int(size)
            segments[end_index:] = [lower_back_segment] * (size - end_index)

            segments[start_index:end_index] = [_Segment(blank, _Style(bgcolor=bar, meta=foreground_meta))] * (
                end_index - start_index
            )
            if is_on:
                length = ((end_index - start_index) - 2) // 2

                segments[start_index:end_index] = [_Segment(" ", _Style(bgcolor=bar, meta=foreground_meta))] * (
                    end_index - start_index
                )

                segments[start_index + length : start_index + length + 2] = [
                    _Segment("ON", _Style(bgcolor=bar, meta=foreground_meta))
                ]

            if is_off:
                length = ((end_index - start_index) - 3) // 2

                segments[start_index:end_index] = [_Segment(" ", _Style(bgcolor=bar, meta=foreground_meta))] * (
                    end_index - start_index
                )

                segments[start_index + length : start_index + length + 3] = [
                    _Segment("OFF", _Style(bgcolor=bar, meta=foreground_meta))
                ]

            # Apply the smaller bar characters to head and tail of scrollbar for more "granularity"
            if start_index < len(segments):
                bar_character = bars[len_bars - 1 - start_bar]
                if bar_character != " " or bar_character != "ON":
                    segments[start_index] = _Segment(
                        bar_character * width_thickness,
                        _Style(bgcolor=back, color=bar, meta=foreground_meta)
                        if vertical
                        else _Style(bgcolor=bar, color=back, meta=foreground_meta),
                    )
            if end_index < len(segments):
                bar_character = bars[len_bars - 1 - end_bar]
                if bar_character != " " or bar_character != "OFF":
                    if is_off:
                        end_index -= 2
                    segments[end_index] = _Segment(
                        bar_character * width_thickness,
                        _Style(bgcolor=bar, color=back, meta=foreground_meta)
                        if vertical
                        else _Style(bgcolor=back, color=bar, meta=foreground_meta),
                    )
        else:
            style = _Style(bgcolor=back)
            segments = [_Segment(blank, style=style)] * int(size)
        if vertical:
            return Segments(segments, new_lines=True)
        else:
            return Segments((segments + [_Segment.line()]) * thickness, new_lines=False)


class MyScrollBar(Widget):
    """
    This is just needed so that we can provide the modified rendered. `MyScrollBarRender`
    """

    renderer: ClassVar[Type[ScrollBarRender]] = MyScrollBarRender


class TextSwitch(Switch):
    """
    TextSwitch(Switch)

    A custom switch that renders ON/OFF labels over the colored bars. Essenstially
    is the same as parent `Switch` the renderer needed small modifications. Hence
    the function `render` is here overriding the oroginal function only to reroute
    the renderer to the custom one. The `watch_value` needed different duration
    times as original, hence it is also here.

    Methods
    -------
    render() -> RenderableType
        Renders the switch component with a scrollbar UI.

    watch_value(value: bool) -> None
        Updates the slider position based on the switch value with optional animation.
    """

    DEFAULT_CSS = """
        TextSwitch {
            border: tall transparent;
            height: 3;
            width: 16;
            padding: 0 2;
        }
    """

    def render(self) -> RenderableType:
        style = self.get_component_rich_style("switch--slider")
        return MyScrollBarRender(
            virtual_size=100,
            window_size=50,
            position=self._slider_position * 50,
            style=style,
            vertical=False,
        )

    def watch_value(self, value: bool) -> None:
        target_slider_pos = 1.0 if value else 0.0
        if self._should_animate:
            self.animate("_slider_position", target_slider_pos, duration=0.3)
        else:
            self._slider_position = target_slider_pos
        self.post_message(self.Changed(self, self.value))
