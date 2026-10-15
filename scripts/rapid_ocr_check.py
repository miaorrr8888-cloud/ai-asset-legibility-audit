"""Run a local RapidOCR ONNX engine and compare the recognized text."""
import argparse,csv,io,json,math
from pathlib import Path
from ocr_check import compare

def report_from_rows(rows,expected,minimum=80):
    if rows is None:rows=[]
    if not isinstance(rows,list):raise ValueError('OCR rows must be an array')
    stream=io.StringIO();writer=csv.writer(stream,delimiter='\t');writer.writerow(['level','conf','text']);boxes=[]
    for row in rows:
        if not isinstance(row,(tuple,list)) or len(row)!=3 or not isinstance(row[1],str):raise ValueError('invalid OCR row')
        score=float(row[2])
        if not math.isfinite(score) or not 0<=score<=1:raise ValueError('invalid engine score')
        writer.writerow([5,score*100,row[1]])
        box=row[0].tolist() if hasattr(row[0],'tolist') else row[0]
        boxes.append({'box':box,'text':row[1],'confidence':score})
    r=compare(stream.getvalue(),expected,minimum)
    return {**r,'origin':'RAPIDOCR_LOCAL_ENGINE','detections':boxes}

def recognize(image,expected,minimum=80):
    image=Path(image).resolve()
    if not image.is_file():raise ValueError('image does not exist')
    if image.stat().st_size>30_000_000:raise ValueError('image exceeds 30 MB limit')
    from rapidocr_onnxruntime import RapidOCR
    # Bound thread use; the bundled models run locally without image uploads.
    engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1)
    rows,elapsed=engine(str(image))
    return {**report_from_rows(rows,expected,minimum),'runtime_seconds':elapsed}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image');p.add_argument('--expected',required=True);p.add_argument('--minimum-confidence',type=float,default=80);a=p.parse_args()
    try:r=recognize(a.image,a.expected,a.minimum_confidence)
    except ImportError:p.exit(2,'Install optional requirements-ocr.txt into your Python environment.\n')
    except Exception as e:p.exit(2,'Local OCR failed: '+type(e).__name__+'; check dependencies and input image.\n')
    print(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False));return 0 if r['status']=='TEXT_MATCH' else 1
if __name__=='__main__':raise SystemExit(main())
