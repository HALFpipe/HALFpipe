from niworkflows.nipype.interfaces.base import SimpleInterface

class FakeBIDSLayout:
    def __init__(self, 
        bold_file, metadata):
        
        self.bold_file = bold_file
        self.metadata = metadata
    
    def get_metadata(self, path):
        if path == self.bold_file:
            return self.metadata
        else:
            return dict()
    
    def get_fieldmap(self, path, return_list = False):
        return []

class FakeReadSidecarJSON(SimpleInterface):
    def _run_interface(self, runtime):
        pass
    