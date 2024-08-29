
from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, ScrollableContainer, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Input, Select, SelectionList, Static, Switch
from textual.widgets.selection_list import Selection

from ...collect.events import collect_events
from ...ingest.events import ConditionFile
from ...model.filter import FilterSchema
from .custom_switch import TextSwitch
from .file_pattern_steps import EventsStep, MatEventsStep, TsvEventsStep, TxtEventsStep
from .non_bids_file_itemization import FileItem
from .selection_modal import SelectionModal
import pandas as pd
import copy

from textual.widget import Widget


class EventFilePanel(Widget):
    event_file_pattern_counter = 0


    def __init__(self, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self.current_event_file_pattern_id = None



    def compose(self):
        yield VerticalScroll(Button("Add", id="add_event_file_button"), id="event_file_panel", classes="non_bids_panels")

    @on(Button.Pressed, "#add_event_file_button")
    def _on_button_add_event_file_pressed(self):
        self.create_file_item(load_object=None)
        
    def create_file_item(self, load_object=None):
        def mount_file_item_widget(event_file_type):
            events_step_type: Type[EventsStep] | None = None  # Initialize with a default value
            if event_file_type == "bids":
                events_step_type = TsvEventsStep
            elif event_file_type == "fsl":
                events_step_type = TxtEventsStep
            elif event_file_type == "spm":
                events_step_type = MatEventsStep
            if events_step_type is not None:
                the_file_item = FileItem(
                        id="event_file_pattern_" + str(EventFilePanel.event_file_pattern_counter), 
                        classes="file_patterns", 
                        pattern_class=events_step_type()
                    )
                    
                    
                self.get_widget_by_id("event_file_panel").mount(
                    the_file_item
                )
                self.current_event_file_pattern_id = "event_file_pattern_"+str(EventFilePanel.event_file_pattern_counter)

      #          print('1the_file_item.pattern_match_resultsthe_file_item.pattern_match_results', self.get_widget_by_id("event_file_panel").query_one(FileItem).pattern_match_results)
                EventFilePanel.event_file_pattern_counter += 1
              #  print('rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr', result, dir(result))
                
           #     print('ssssssssssssssssssssssssssssssssshould append after this', the_file_item)
           #     self.app.event_widget_list.append(copy.deepcopy(the_file_item))
            #    print('self.app.event_widget_listself.app.event_widget_list', self.app.event_widget_list)
                self.refresh()
            else:
                print("isssssssssssssssssssssss none")

        if load_object is None:
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
                mount_file_item_widget,
            )
            
        else:
            print('llllllllllllllllllllllllllllllllllll load_obj', load_object.path)
            self.get_widget_by_id("event_file_panel").mount(
                FileItem(
                    id="event_file_pattern_" + str(EventFilePanel.event_file_pattern_counter), 
                    classes="file_patterns", 
                    load_object=load_object
                )
            )
            EventFilePanel.event_file_pattern_counter += 1
        
        
    def on_mount(self):
        # use first event file panel widget to make copies for the newly created one
        first_event_file_panel_widget = self.app.walk_children(EventFilePanel)[0]
        # only use if it is not the first one!
        if first_event_file_panel_widget != self:
            for file_item_widget in first_event_file_panel_widget.walk_children(FileItem):
                self.get_widget_by_id("event_file_panel").mount(
                    FileItem(
                        id=file_item_widget.id, 
                        classes="file_patterns", 
                        load_object=file_item_widget.get_pattern_match_results
                    )
                )
                
                
    @on(FileItem.PathPatternChanged)
    def _on_update_all_instances(self, event):    
        print('event.control.id, event.control.get_pattern_match_results', event.control.id, event.control.get_pattern_match_results)
        
        if event.control.id == self.current_event_file_pattern_id:
            for w in self.app.walk_children(EventFilePanel):
                if w != self:
                    w.get_widget_by_id('event_file_panel').mount(FileItem(
                        id=event.control.id,
                        classes="file_patterns", 
                        load_object=event.value
                        )
                    )













