# -*- coding: utf-8 -*-
from ..specialized_widgets.confirm_screen import Confirm


async def quit_modal(self):
    def quit(modal_value):
        """
        Callback function to handle the user's quit decision.

        This function is called when the confirmation modal is
        dismissed. If the user confirms, the application exits.

        Parameters
        ----------
        modal_value : bool
            True if the user confirmed, False otherwise.
        """
        if modal_value:
            self.app.exit(result=False)
        else:
            pass

    # raise the modal only once not matter what
    if "quit_modal" not in [w.id for w in self.app.walk_children()]:
        await self.app.push_screen(
            Confirm(
                "Do you really want to quit?",
                left_button_text="YES",
                right_button_text="NO",
                left_button_variant="error",
                right_button_variant="success",
                title="Quit?",
                id="quit_modal",
                classes="confirm_warning",
            ),
            quit,
        )
