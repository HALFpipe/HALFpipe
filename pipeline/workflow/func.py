
from nipype.pipeline import engine as pe
from nipype.interfaces import utility as niu
from nipype.interfaces import fsl

from nipype.algorithms import confounds as nac

from mriqc.interfaces import viz

def init_temporalfilter_wf(temporal_filter_width, repetition_time, name = "temporalfilter"):
    workflow = pe.Workflow(name=name)
    
    inputnode = pe.Node(niu.IdentityInterface(
        fields = ["bold_file", ""]), 
        name = "inputnode"
    )
    
    outputnode = pe.Node(niu.IdentityInterface(
        fields = ["filtered_file"]), 
        name = "outputnode"
    )
    
    highpass_operand = "-bptf %.10f -1" % \
        (temporal_filter_width / (2.0 * repetition_time))
    
    highpass = pe.Node(
        interface=fsl.ImageMaths(
            op_string = highpass_operand, suffix = "_tempfilt"),
        name="highpass"
    )
    
    meanfunc = pe.Node(
        interface = fsl.ImageMaths(
            op_string = "-Tmean", suffix = "_mean"),
        name = "meanfunc"
    )
    
    addmean = pe.Node(
        interface = fsl.BinaryMaths(
            operation = "add"), 
        name = "addmean"
    )
    
    workflow.connect([
        (inputnode, highpass, [
            ("bold_file", "in_file")
        ]),
        (inputnode, meanfunc, [
            ("bold_file", "in_file")
        ]),
        (highpass, addmean, [
            ("out_file", "in_file")
        ]),
        (meanfunc, addmean, [
            ("out_file", "operand_file")
        ]),
        (addmean, outputnode, [
            ("out_file", "filtered_file")
        ])
    ])
    
    return workflow

def init_tsnr_wf(name = "tsnr"):
    workflow = pe.Workflow(name=name)
    
    inputnode = pe.Node(niu.IdentityInterface(
        fields = ["bold_file"]), 
        name = "inputnode"
    )
    
    outputnode = pe.Node(niu.IdentityInterface(
        fields = ["report_file"]), 
        name = "outputnode"
    )
    
    tsnr = pe.Node(
        interface = nac.TSNR(), 
        name = "compute_tsnr")
        
    mosaic_stddev = pe.Node(
        interface = viz.PlotMosaic(
            out_file = "plot_func_stddev_mosaic2_stddev.svg",
            cmap = "viridis"), 
        name="plot_mosaic")
        
    workflow.connect([
        (inputnode, tsnr, [
            ("bold_file", "in_file")
        ]),
        (tsnr, mosaic_stddev, [
            ("tsnr_file", "in_file")
        ]),
        (mosaic_stddev, outputnode, [
            ("out_file", "report_file")
        ])
    ])
    
    return workflow
    