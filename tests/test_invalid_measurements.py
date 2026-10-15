from pathlib import Path
import unittest,tempfile,subprocess,sys,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]

class InvalidMeasurements(unittest.TestCase):
    def command(self,p):
        return [sys.executable,str(ROOT/'references/legibility_audit.py'),'--truth',str(p/'blank.png'),'--test',str(p/'blank.png'),'--truth-box','0,0,20,20','--test-box','0,0,20,20','--out',str(p/'out')]
    def test_empty_mask_is_unknown_not_low_similarity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); Image.new('L',(20,20),0).save(p/'blank.png')
            r=subprocess.run(self.command(p),capture_output=True)
            self.assertEqual(r.returncode,0)
            data=json.loads((p/'out/legibility_verdict.json').read_text())
            self.assertEqual(data['verdict'],'UNKNOWN'); self.assertIsNone(data['best_iou'])
    def test_invalid_threshold_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); Image.new('L',(20,20),0).save(p/'blank.png')
            r=subprocess.run(self.command(p)+['--th','nan'],capture_output=True)
            self.assertEqual(r.returncode,2); self.assertFalse((p/'out/legibility_verdict.json').exists())

if __name__=='__main__': unittest.main()
