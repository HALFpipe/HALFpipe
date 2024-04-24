# -*- coding: utf-8 -*-


import sys

# Add your path here (replace '/path/to/directory' with the actual path)
sys.path.append("/home/tomas/github/HALFpipe/src/")

import os
from pathlib import Path
from typing import Iterable

# from textual._input import _InputRenderable
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Grid
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Input

from halfpipe.tui.utils.select_or_input_path import SelectOrInputPath, create_path_option_list


class FilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not path.name.startswith(".")]


class FileBrowserModal(ModalScreen):
    """
    Here goes docstring.
    """

    CSS_PATH = ["tcss/file_browser.tcss"]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.expanded_nodes: list = []

    def compose(self) -> ComposeResult:
        base = "/"
        yield Container(
            FilteredDirectoryTree("/", classes="browse_tree", id="dir_tree"),
            #     Input(placeholder="Set path to the " + self.path_to, id="path_input_box2"),
            SelectOrInputPath(
                [(f, f) for f in create_path_option_list(base=base, include_base=True)],
                prompt_default=base,
                top_parent=self,
                id="path_input_box2",
            ),
            Grid(
                Button("Ok", classes="button ok"),
                Button("Cancel", classes="button cancel"),
            ),
            id="file_browser_screen",
        )

    @on(SelectOrInputPath.PromptChanged)
    def _select_or_input_path_changed(self, message):
        path = message.value
        print("thisssssssssssssssssssssssssss path", path)
        # scan over already expanded nodes
        opened_node_paths = [str(node.data.path) + "/" for node in self.expanded_nodes]

        # collapsing nodes
        if opened_node_paths != []:
            path_of_last_expanded_node = str(self.expanded_nodes[-1].data.path)
            if path_of_last_expanded_node not in path:  # compare with the last one, the highest opened node
                self.expanded_nodes[-1].collapse()
                self.expanded_nodes.pop()

        if os.path.isdir(path) and path.endswith("/"):
            # scan the whole tree and find node with the particular path and expand it
            tree = self.get_widget_by_id("dir_tree")
            for t in tree._tree_nodes:
                tree_path = str(tree._tree_nodes[t].data.path) + "/"
                node = tree._tree_nodes[t]

                # expanding nodes, if path is in one of the nodes and it was not already expanded
                if tree_path == path and path not in opened_node_paths:
                    if not node.allow_expand:
                        return
                    node.expand()
                    self.expanded_nodes.append(node)

    @on(FilteredDirectoryTree.DirectorySelected, ".browse_tree")
    async def on_filtered_directory_tree_directory_selected(self, message):
        self.selected_directory = message.path
        label = self.get_widget_by_id("path_input_box2")
        label.change_prompt_from_parrent(str(self.selected_directory))

    @on(Input.Submitted, "#path_input_box2")
    def update_from_input(self):
        self.selected_directory = self.get_widget_by_id("path_input_box2").value

    @on(Button.Pressed, "#file_browser_screen .ok")
    def ok(self):
        self._confirm_window()

    @on(Button.Pressed, "#file_browser_screen .cancel")
    def cancel(self):
        self._cancel_window()

    def key_escape(self):
        self._cancel_window()

    def _confirm_window(self):
        self.update_from_input()
        self.dismiss(self.selected_directory)

    def _cancel_window(self):
        self.dismiss(None)
