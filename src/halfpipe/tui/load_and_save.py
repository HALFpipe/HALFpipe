# TODO
# Try to refactor load and save logic here
# For load, the logic is now in working_directory/base.py in function load_from_spec.
# This function then fills the ctx.cache and then calls cache_file_patterns to prepare
# file objects (events, files, atlas files, etc) and then calls mount_features function
# which first fill cache with features, then creates widgets for them and then mounts them.
# Afterwards, the same logic is done for models.
# The goal is to extract these functions and make a separate load.py for them. There is a bit of
# challenge how to pass the app object there and query the widgets into which we want to mount
# loaded objects correctly.

# The save should be more straightforward as we do not mount or work with widgets here. The function
# save_spec is now in run/base.py. We want to put it into a save.py and call it from there.
