from pathlib import Path
import importlib.util,unittest,tempfile,json,sys,subprocess,os
ROOT=Path(__file__).resolve().parents[1]
def load(path):
    sys.path.insert(0,str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('extension',ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class OCR(unittest.TestCase):
    def test_match_and_mismatch(self):
        m=load('scripts/ocr_check.py');tsv='level\tconf\ttext\n5\t96\tDEMO\n5\t94\t123\n'
        self.assertEqual(m.compare(tsv,'DEMO 123')['status'],'TEXT_MATCH')
        self.assertEqual(m.compare(tsv,'DEMO 128')['status'],'TEXT_MISMATCH')
    def test_uncertain_is_not_pass(self):
        m=load('scripts/ocr_check.py')
        self.assertEqual(m.compare('level\tconf\ttext\n5\t25\tDEMO\n','DEMO')['status'],'REVIEW_REQUIRED')
        self.assertEqual(m.compare('level\tconf\ttext\n','DEMO')['status'],'REVIEW_REQUIRED')
    def test_invalid_confidence_rejected(self):
        with self.assertRaises(ValueError):load('scripts/ocr_check.py').compare('level\tconf\ttext\n5\tnan\tA\n','A')
