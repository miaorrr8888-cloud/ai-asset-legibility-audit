from pathlib import Path
import importlib.util,sys,unittest,tempfile,json
ROOT=Path(__file__).resolve().parents[1]
def load(path):
    sys.path.insert(0,str(ROOT/'scripts'))
    spec=importlib.util.spec_from_file_location('third',ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class RapidRows(unittest.TestCase):
    def test_empty_unknown(self):self.assertEqual(load('scripts/rapid_ocr_check.py').report_from_rows(None,'A')['status'],'REVIEW_REQUIRED')
    def test_real_format_match_and_wrong_digits(self):
        m=load('scripts/rapid_ocr_check.py');rows=[[[[0,0],[1,0],[1,1],[0,1]],'DEMO 123',.99]]
        self.assertEqual(m.report_from_rows(rows,'DEMO 123')['status'],'TEXT_MATCH');self.assertEqual(m.report_from_rows(rows,'DEMO 128')['status'],'TEXT_MISMATCH')
    def test_nan_confidence_rejected(self):
        with self.assertRaises(ValueError):load('scripts/rapid_ocr_check.py').report_from_rows([[[],'A',float('nan')]],'A')
