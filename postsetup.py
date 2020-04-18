from pipeline.fmriprepconfig import config as fmriprepconfig
from templateflow import api

assert len(api.get(fmriprepconfig.skull_strip_template.space)) > 0
assert all(len(api.get(space)) > 0 for space in fmriprepconfig.spaces.get_spaces())
