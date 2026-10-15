from pathlib import Path
import importlib.util, unittest, tempfile, subprocess, sys, json, zipfile, io, os
R=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class Legibility(unittest.TestCase):
    def setUp(self): self.m=load('legibility',R/'references/legibility_audit.py')
    def test_roi_outside_image_rejected(self):
        import numpy as np
        for box in [(-1,0,2,2),(0,0,10,2),(0,0,0,2)]:
            with self.assertRaises(ValueError): self.m.crop(np.zeros((5,5)),box)
    def test_empty_and_full_masks_do_not_pass(self):
        import numpy as np
        ref=np.zeros((10,10),bool); ref[1:4,1:4]=True
        self.assertFalse(self.m._coverage_ok(np.zeros_like(ref),ref)); self.assertFalse(self.m._coverage_ok(np.ones_like(ref),ref))
    def test_nonfinite_is_unknown(self):
        for v in [float('nan'),float('inf'),-float('inf')]: self.assertEqual(self.m.verdict_from_best(v)[0],'UNKNOWN')

class TestIdenticalImagesProduceSimilarityReport(unittest.TestCase):
    def test_identical_images_produce_similarity_report(self):
        from PIL import Image,ImageDraw
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder); image=Image.new('L',(120,80),0); draw=ImageDraw.Draw(image)
            draw.rectangle((20,15,30,65),fill=255); draw.rectangle((30,15,80,25),fill=255)
            draw.rectangle((60,40,80,50),fill=255); image.save(p/'truth.png')
            command=[sys.executable,str(R/'references/legibility_audit.py'),
                     '--truth',str(p/'truth.png'),'--test',str(p/'truth.png'),
                     '--truth-box','0,0,120,80','--test-box','0,0,120,80','--out',str(p/'qa')]
            result=subprocess.run(command,capture_output=True,env={**os.environ,'PYTHONUTF8':'1'})
            self.assertEqual(result.returncode,0,result.stdout.decode('utf-8',errors='replace'))
            report=json.loads((p/'qa/legibility_verdict.json').read_text())
            self.assertEqual(report['verdict'],'HIGH_SIMILARITY')
            self.assertGreater(report['best_iou'],0.99)

class TestLowSimilarityDoesNotClaimGeneratedOrigin(unittest.TestCase):
    def test_low_similarity_does_not_claim_generated_origin(self):
        m=load('similarity',R/'references/legibility_audit.py')
        label,note=m.verdict_from_best(0.1)
        self.assertEqual(label,'LOW_SIMILARITY'); self.assertIn('unknown',note)

if __name__=="__main__": unittest.main(verbosity=2)
