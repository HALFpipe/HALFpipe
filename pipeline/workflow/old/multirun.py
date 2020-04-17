#
#
#
#
#
# run_wfs = []
# outnamesset = set()
# outfieldsset = set()
#
# for run, bold_file in value1.items():
#     run_wf = pe.Workflow(name="run-" + run)
#     run_wfs.append(run_wf)
#
#     run_inputnode = pe.Node(niu.IdentityInterface(
#         fields=_func_inputnode_fields,
#     ), name="inputnode")
#     run_wf.add_nodes((inputnode,))
#
#     scan_wf.connect([
#         (inputnode, run_wf, [
#             (f, "inputnode.%s" % f)
#             for f in _func_inputnode_fields
#         ])
#     ])
#     run_outnames, run_fields = init_func_wf(
#         run_wf, run_inputnode, bold_file, metadata,
#         fmriprep_reportlets_dir, fmriprep_output_dir,
#         output_dir, run=run,
#         subject=subject
#     )
#     outnamesset.update(run_outnames)
#     outfieldsset.update(run_fields)
#
# outnames[name] = outnamesset
# outputnode_fields = \
#     sum([["%s_%s" % (outname, field) for field in outfieldsset]
#         for outname in outnamesset], [])
# outputnode_fields.append("keep")
#
# outputnode = pe.Node(niu.IdentityInterface(
#     fields=outputnode_fields
# ), name="outputnode")
#
# for outname in outnamesset:
#     outmerge = {}
#     for field in outfieldsset:
#         outmerge[field] = pe.Node(
#             interface=niu.Merge(len(run_wfs)),
#             name="%s_%s_merge" % (outname, field)
#         )
#
#         for i, wf in enumerate(run_wfs):
#             scan_wf.connect([
#                 (wf, outmerge[field], [
#                     ("outputnode.%s_cope" % outname,
#                         "in%i" % (i + 1))
#                 ])
#             ])
#
#     # aggregate stats from multiple runs in fixed-effects
#     # model
#     fe_wf, _ = init_higherlevel_wf(run_mode="fe",
#                                    name="%s_fe" % outname,
#                                    outname=outname,
#                                    workdir=workdir)
#
#     get_first_cope = pe.Node(
#         name="%s_get_first_cope" % outname,
#         interface=niu.Function(input_names=["in"],
#                                output_names=["out"],
#                                function=get_first)
#     )
#     get_first_varcope = pe.Node(
#         name="%s_get_first_varcope" % outname,
#         interface=niu.Function(input_names=["in"],
#                                output_names=["out"],
#                                function=get_first)
#     )
#     get_first_doffile = pe.Node(
#         name="%s_get_first_doffile" % outname,
#         interface=niu.Function(input_names=["in"],
#                                output_names=["out"],
#                                function=get_first)
#     )
#
#     scan_wf.connect([
#         (mergecopes, fe_wf, [
#             ("out", "inputnode.copes")
#         ]),
#         (mergevarcopes, fe_wf, [
#             ("out", "inputnode.varcopes")
#         ]),
#         (mergedoffiles, fe_wf, [
#             ("out", "inputnode.dof_files")
#         ]),
#         (mergemaskfiles, fe_wf, [
#             ("out", "inputnode.mask_files")
#         ]),
#
#         (fe_wf, get_first_cope, [
#             ("outputnode.copes", "in")
#         ]),
#         (fe_wf, get_first_varcope, [
#             ("outputnode.varcopes", "in")
#         ]),
#         (fe_wf, get_first_doffile, [
#             ("outputnode.dof_files", "in")
#         ]),
#
#         (get_first_cope, outputnode, [
#             ("out", "%s_cope" % outname)
#         ]),
#         (get_first_varcope, outputnode, [
#             ("out", "%s_varcope" % outname)
#         ]),
#         (get_first_doffile, outputnode, [
#             ("out", "%s_dof_file" % outname)
#         ]),
#         (fe_wf, outputnode, [
#             ("outputnode.mask_file", "%s_mask_file" % outname)
#         ])
#     ])
#
# # aggregate motioncutoff_keep
#
# logicaland = pe.Node(
#     name="logicaland",
#     interface=LogicalAnd(numinputs=(len(run_wfs) + 1))
# )
#
# for i, wf in enumerate(run_wfs):
#     scan_wf.connect([
#         (wf, logicaland, [
#             ("motioncutoff.keep", "in%i" % (i + 1))
#         ])
#     ])
#
# qualitycheck = pe.Node(
#     name="qualitycheck",
#     interface=QualityCheck(base_directory=workdir,
#                            subject=subject, task=name)
# )
#
# scan_wf.connect(qualitycheck, "keep", logicaland, "in%i" % (len(run_wfs) + 1))
#
# scan_wf.connect(logicaland, "out", outputnode, "keep")
