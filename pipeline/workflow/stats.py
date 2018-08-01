


# def init_secondlevel_wf(name = "secondlevel"):
    


# def init_first_level_workflow():
# 
# 
#     copemerge = pe.MapNode(
#     interface=fsl.Merge(dimension="t"),
#     iterfield=["in_files"],
#     name="copemerge")
# 
# varcopemerge = pe.MapNode(
#     interface=fsl.Merge(dimension="t"),
#     iterfield=["in_files"],
#     name="varcopemerge")
# 
#     level2model = pe.Node(interface=fsl.L2Model(), name="l2model")
# 
#     flameo = pe.MapNode(
#     interface=fsl.FLAMEO(run_mode="fe"),
#     name="flameo",
#     iterfield=["cope_file", "var_cope_file"])
# 
# fixed_fx.connect([
#     (copemerge, flameo, [("merged_file", "cope_file")]),
#     (varcopemerge, flameo, [("merged_file", "var_cope_file")]),
#     (level2model, flameo, [("design_mat", "design_file"),
#                            ("design_con", "t_con_file"), ("design_grp",
#                                                           "cov_split_file")]),
# ]
# 
# modelfit.connect([
#     (modelspec, level1design, [("session_info", "session_info")]),
#     (level1design, modelgen, [("fsf_files", "fsf_file"), ("ev_files",
#                                                           "ev_files")]),
#     (modelgen, modelestimate, [("design_file", "design_file")]),
#     (modelgen, conestimate, [("con_file", "tcon_file")]),
#     (modelestimate, conestimate,
#      [("param_estimates", "param_estimates"), ("sigmasquareds",
#                                                "sigmasquareds"),
#       ("corrections", "corrections"), ("dof_file", "dof_file")]),
# ])