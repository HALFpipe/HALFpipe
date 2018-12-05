
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl


def gen_merge_op_str(files):
    out = []
    for file in files:
        with open(file) as f:
            text = f.read()
        out.append("-abs -bin -mul %f" % float(text))
    return out


def get_first(l):
    if isinstance(l, str):
        return l
    else:
        return get_first(l[0])


def get_len(x):
    return len(x)


def init_higherlevel_wf(run_mode = "flame1", name = "higherlevel"):
    workflow = pe.Workflow(name=name)

    inputnode = pe.Node(
        interface = niu.IdentityInterface(
            fields = ["copes", "varcopes", "dof_files", "mask_files"]
        ), 
        name = "inputnode"
    )

    outputnode = pe.Node(
        interface = niu.IdentityInterface(
            fields = ["cope", "varcope", "zstat", "dof_file", "mask_file"]
        ), 
        name = "outputnode"
    )
    
    maskmerge = pe.Node(
        interface = fsl.Merge(dimension = "t"),
        name = "maskmerge"
    )
    maskagg = pe.Node(
        interface = fsl.ImageMaths(
            op_string = "-Tmean -thr 1 -bin"
        ),
        name = "maskagg"
    )
    
    gendofimage = pe.MapNode(
        interface = fsl.ImageMaths(),
        iterfield = ["in_file", "op_string"],
        name = "gendofimage"
    )

    copemerge = pe.Node(
        interface = fsl.Merge(dimension = "t"),
        name = "copemerge"
    )

    varcopemerge = pe.Node(
        interface = fsl.Merge(dimension = "t"),
        name = "varcopemerge"
    )
    
    dofmerge = pe.Node(
        interface = fsl.Merge(dimension = "t"),
        name = "dofmerge"
    )
    
    level2model = pe.Node(
        interface = fsl.L2Model(), 
        name = "l2model"
    )

    flameo = pe.MapNode(
        interface=fsl.FLAMEO(
            run_mode = run_mode
        ),
        name="flameo",
        iterfield=["cope_file", "var_cope_file"]
    )
    
    workflow.connect([
        (inputnode, copemerge, [
            ("copes", "in_files")
        ]),
        (inputnode, varcopemerge, [
            ("varcopes", "in_files")
        ]),
        
        (inputnode, maskmerge, [
            ("mask_files", "in_files")
        ]),
        (maskmerge, maskagg, [
            ("merged_file", "in_file")
        ]),
        
        (inputnode, gendofimage, [
            ("copes", "in_file"),
            (("dof_files", gen_merge_op_str), "op_string")
        ]),
        (gendofimage, dofmerge, [
            ("out_file", "in_files")
        ]),
        
        (copemerge, flameo, [
            ("merged_file", "cope_file")
        ]),
        (varcopemerge, flameo, [
            ("merged_file", "var_cope_file")
        ]),
        (dofmerge, flameo, [
            ("merged_file", "dof_var_cope_file")
        ]),
        (maskagg, flameo, [
            ("out_file", "mask_file")
        ]),
        (inputnode, level2model, [
            (("copes", get_len), "num_copes")
        ]),
        (level2model, flameo, [
            ("design_mat", "design_file"),
            ("design_con", "t_con_file"), 
            ("design_grp", "cov_split_file")
        ]),
        
        (flameo, outputnode, [
            (("copes", get_first), "cope"),
            (("var_copes", get_first), "varcope"), 
            (("zstats", get_first), "zstat"),
            (("tdof", get_first), "dof_file")
        ]),
        (maskagg, outputnode, [
            ("out_file", "mask_file")
        ])
    ])
    
    return workflow
