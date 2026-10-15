"""OCR exact-text check using Tesseract or an explicitly supplied TSV transcript."""
import argparse,csv,io,json,shutil,subprocess,unicodedata

def compare(tsv,expected,min_confidence=80):
    if not isinstance(expected,str) or not expected.strip():raise ValueError('expected text required')
    if not 0<=min_confidence<=100:raise ValueError('confidence must be 0..100')
    reader=csv.DictReader(io.StringIO(tsv),delimiter='\t')
    if not {'level','conf','text'}.issubset(reader.fieldnames or []):raise ValueError('Tesseract TSV headers required')
    words=[];conf=[]
    for row in reader:
        if row['level']!='5' or not row['text'].strip():continue
        value=float(row['conf'])
        if not 0<=value<=100:raise ValueError('invalid OCR confidence')
        words.append(row['text']);conf.append(value)
    recognized=' '.join(words)
    def norm(x):return ''.join(unicodedata.normalize('NFKC',x).split())
    match=norm(recognized)==norm(expected); low=not conf or min(conf)<min_confidence
    return {'recognized_text':recognized,'expected_text':expected,'exact_normalized_match':match,
            'minimum_word_confidence':min(conf) if conf else None,
            'status':'REVIEW_REQUIRED' if low else ('TEXT_MATCH' if match else 'TEXT_MISMATCH'),
            'human_review_required':True,'notice':'OCR confidence is not calibrated correctness probability; compare original pixels.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--image');g.add_argument('--tsv')
    p.add_argument('--expected',required=True);p.add_argument('--lang',default='eng');p.add_argument('--engine',default='tesseract');a=p.parse_args()
    try:
        if a.tsv:
            tsv=open(a.tsv,encoding='utf-8-sig').read();origin='SUPPLIED_TSV_NOT_ENGINE_RUN'
        else:
            engine=shutil.which(a.engine)
            if not engine:raise ValueError('Tesseract unavailable; install engine and language data or provide --tsv')
            r=subprocess.run([engine,a.image,'stdout','-l',a.lang,'tsv'],capture_output=True,text=True,encoding='utf-8',timeout=60)
            if r.returncode:raise ValueError('OCR engine failed; check language data and image')
            tsv=r.stdout;origin='TESSERACT_ENGINE'
        result=compare(tsv,a.expected);result['origin']=origin
    except (OSError,ValueError,subprocess.TimeoutExpired) as e:p.exit(2,'OCR error: '+str(e)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if result['status']=='TEXT_MATCH' else 1
if __name__=='__main__':raise SystemExit(main())
