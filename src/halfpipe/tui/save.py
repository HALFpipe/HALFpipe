import copy

from ..model.feature import Feature
from ..model.file.bids import BidsFileSchema
from ..model.model import Model
from ..model.setting import SettingSchema
from ..utils.copy import deepcopy
from .data_analyzers.context import ctx
from .specialized_widgets.confirm_screen import Confirm


def dump_dict_to_contex(self, save=False):
    """
    Converts the cached data to the spec json format.

    This method converts the cached data to the context format, which
    includes features, settings, models, and files. It handles
    specific cases for BIDS and non-BIDS files.

    Parameters
    ----------
    save : bool, optional
        A flag indicating whether to save the data, by default False.
    """
    # the cache key logic goes like this: first it is the particular name of the main item, for example a feature called
    # 'foo' will produce a key "foo" this is the "name". Second, it is the main group type of the item, if it is the
    # feature then the group type is feature, if it is for example bold file pattern then it is the bold file pattern,
    # and third are the various own items of the group type, thus these vary from group to group
    # The reason why this goes name-group type-items is that it is easier to delete the particular main item if its name
    # is at the first level

    # clear the whole database and all other entries in the context object
    ctx.database.filepaths_by_tags = dict()
    ctx.database.tags_by_filepaths = dict()
    ctx.spec.features.clear()
    ctx.spec.settings.clear()
    ctx.spec.models.clear()
    ctx.spec.files.clear()
    # iterate now over the whole cache and fill the context object
    # the "name" is widget name carying the particular user choices, either a feature or file pattern
    for name in list(ctx.cache.keys()):  # Copy keys into a list to avoid changing dict size during iteration
        # skip whole entry if in the feature there were no selected tasks
        if (
            ctx.cache[name]["settings"].get("filters", [])
            and name != "bids"
            and ctx.cache[name]["settings"]["filters"][0].get("values", []) == []
        ):
            self.app.push_screen(
                Confirm(
                    f"Feature {name} is missing a task! Select at least one task!",
                    left_button_text=False,
                    right_button_text="OK",
                    #  left_button_variant=None,
                    right_button_variant="default",
                    title="Feature incomplete warning",
                    # id="association_modal",
                    classes="confirm_warning",
                )
            )
            continue

        if ctx.cache[name]["features"] != {}:
            featureobj = Feature(name=name, type=ctx.cache[name]["features"]["type"])
            ctx.spec.features.append(featureobj)
            for key, value in ctx.cache[name]["features"].items():
                # for reho and falff smoothing is in features
                if key == "smoothing" and value.get("fwhm") is None:
                    continue
                setattr(ctx.spec.features[-1], key, value)

        if ctx.cache[name]["settings"] != {}:
            ctx.spec.settings.append(SettingSchema().load({}, partial=True))
            for key, value in ctx.cache[name]["settings"].items():
                # Skip keys based on specific conditions
                if (
                    (key == "bandpass_filter" and value.get("type") is None)
                    or (key == "smoothing" and value.get("fwhm") is None)
                    or (key == "grand_mean_scaling" and value.get("mean") is None)
                ):
                    continue

                # Special handling for "filters", if there are no filters, than put there just empty list
                if key == "filters":
                    # filters = value
                    filter_list_for_spec_file = []
                    # we need to loop over the filter list
                    if not value:  # Filters is empty
                        value = []
                    else:
                        for f in value:
                            images = ctx.get_available_images[f["entity"]]
                            if (
                                # If the filter contains all possible values, then we set it to empty list. This is done
                                # by coparing the filter with the all possible images of the data.
                                set(f.get("values", [])) == set(images)
                                # Or the filter dict has empty "values", then we do not include the filter in the final
                                # spec file.
                                or isinstance(f, dict)
                                and not f.get("values")
                            ):
                                # do not append
                                # value = []  # Overwrite filters value with an empty list
                                continue
                            else:
                                # append
                                filter_list_for_spec_file.append(f)
                        # Variable 'value' is sent to the spec file, so we override it with the modified filter list based
                        # on what passed the above 'if' conditions.
                        value = filter_list_for_spec_file

                # Apply the value to the settings object
                setattr(ctx.spec.settings[-1], key, value)

            # this is for the case of falff
            if "unfiltered_setting" in ctx.cache[name]:
                unfiltered_setting = deepcopy(ctx.spec.settings[-1])
                unfiltered_setting["name"] = ctx.cache[name]["unfiltered_setting"]["name"]
                unfiltered_setting["bandpass_filter"] = None  # remove bandpass filter, keep everything else
                ctx.spec.settings.append(unfiltered_setting)
        if ctx.cache[name]["models"] != {}:
            # In case of the aggregate models, we need to loop over a list of models. The standard models such as Linear
            # or InterceptOnly are linked to a widget, however the aggregate models do not have their own widgets, they
            # are created within the Linear model and so they belong implicitly to those widgets. This connection is made
            # by suffix '__aggregate_models_list'. When this suffix is present, we know that we are dealing with a list
            # of models, hence we need to iterate of it. This solution is done in this way because otherwise keeping track
            # of which aggregate models belong to which Linear models would be not possible. We need this connection so
            # that for example when a Linear models is deleted, we need to know which aggregate models we need to also
            # delete. There are also other instances why we need this, for example loading from a spec file, duplicating.

            if name.endswith("__aggregate_models_list"):
                "aggregate_models"
                models_list = ctx.cache[name]["models"]["aggregate_models_list"]
            else:
                models_list = [ctx.cache[name]["models"]]  # Ensure it's iterable

            for model in models_list:
                modelobj = Model(
                    name=model["name"],
                    type=model["type"],
                    across="sub" if not name.endswith("__aggregate_models_list") else model["across"],
                )
                if modelobj.name not in [m.__dict__["name"] for m in ctx.spec.models]:
                    ctx.spec.models.append(modelobj)
                    for key, value in model.items():
                        setattr(ctx.spec.models[-1], key, value)

        if ctx.cache["bids"]["files"] != {} and name == "bids":
            ctx.put(BidsFileSchema().load({"datatype": "bids", "path": ctx.cache["bids"]["files"]}))

        if ctx.cache[name]["files"] != {} and name != "bids":
            ctx.spec.files.append(ctx.cache[name]["files"])
            ctx.database.put(ctx.spec.files[-1])  # we've got all tags, so we can add the fileobj to the index
    self.old_cache = copy.deepcopy(ctx.cache)
    # refresh at the end available images
    ctx.refresh_available_images()
