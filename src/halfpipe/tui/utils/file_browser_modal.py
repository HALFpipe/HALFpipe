# -*- coding: utf-8 -*-


import sys

# Add your path here (replace '/path/to/directory' with the actual path)
sys.path.append("/home/tomas/github/HALFpipe/src/")

import os
from pathlib import Path
from typing import Iterable

# from textual._input import _InputRenderable
from textual import on
from textual.containers import Horizontal
from textual.widgets import Button, DirectoryTree, Input

from halfpipe.tui.utils.select_or_input_path import SelectOrInputPath, create_path_option_list

from .confirm_screen import Confirm
from .draggable_modal_screen import DraggableModalScreen


def path_test(path, isfile=False):
    if os.path.exists(path):
        if os.access(path, os.W_OK):
            if isfile:
                result_info = "OK" if os.path.isfile(path) else "A directory was selected instead of a file!"
            else:
                result_info = "OK" if os.path.isdir(path) else "A file was selected instead of a directory!"
        else:
            result_info = "Permission denied."
    else:
        result_info = "File not found."
    return result_info


class FilteredDirectoryTree(DirectoryTree):
    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [path for path in paths if not path.name.startswith(".")]


class FileBrowserModal(DraggableModalScreen):
    """
    Here goes docstring.
    """

    CSS_PATH = ["tcss/file_browser.tcss"]

    def __init__(self, title="Browse", path_test_function=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.expanded_nodes: list = []
        self.title_bar.title = title
        self.path_test_function = path_test if path_test_function is None else path_test_function

    def on_mount(self) -> None:
        base = "/"
        self.content.mount(
            FilteredDirectoryTree("/", classes="browse_tree", id="dir_tree"),
            #     Input(placeholder="Set path to the " + self.path_to, id="path_input_box2"),
            SelectOrInputPath(
                [(f, f) for f in create_path_option_list(base=base, include_base=True)],
                prompt_default=base,
                top_parent=self,
                id="path_input_box2",
            ),
            Horizontal(
                Button("Ok", classes="button ok"),
                Button("Cancel", classes="button cancel"),
            ),
        )

    @on(SelectOrInputPath.PromptChanged)
    def _select_or_input_path_changed(self, message):
        path = message.value
        self.selected_directory = path
        print("thisssssssssssssssssssssssssss path", path, "xxx", self.selected_directory)
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
    @on(FilteredDirectoryTree.FileSelected, ".browse_tree")
    async def on_filtered_directory_tree_directory_or_file_selected(self, message):
        self.selected_directory = message.path
        label = self.get_widget_by_id("path_input_box2")
        label.change_prompt_from_parrent(str(self.selected_directory))
        print("mmmmmmmmmmmmmmmmmmmmmmmmmm", message.path)

    @on(Input.Submitted, "#path_input_box2")
    def update_from_input(self):
        print("heeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeere???????????", self.get_widget_by_id("path_input_box2").value)
        self.selected_directory = self.get_widget_by_id("path_input_box2").value

    @on(Button.Pressed, ".ok")
    def ok(self):
        self._confirm_window()

    @on(Button.Pressed, ".cancel")
    def cancel(self):
        self._cancel_window()

    def key_escape(self):
        self._cancel_window()

    def _confirm_window(self):
        self.update_from_input()
        path_test_result = self.path_test_function(self.selected_directory)
        if path_test_result == "OK":
            self.dismiss(self.selected_directory)
        else:
            # self.app.push_screen(
            # FalseInputWarning(
            # warning_message=path_test_result,
            # title="Error - Invalid path",
            # id="invalid_path_warning_modal",
            # classes="error_modal",
            # )
            # )
            self.app.push_screen(
                Confirm(
                    path_test_result,
                    title="Error - Invalid path",
                    left_button_text=False,
                    right_button_text="OK",
                    id="invalid_path_warning_modal",
                    classes="confirm_error",
                )
            )

    def _cancel_window(self):
        self.dismiss("")
