#!/usr/bin/env python3
import hashlib,json,pathlib,shutil,sys,xml.etree.ElementTree as ET
root=pathlib.Path(__file__).resolve().parent.parent;tag=sys.argv[1]
stage=root/'verification'/tag; report=stage/'precheck/reports/results.xml'
r=ET.parse(report).getroot();cases=r.findall('.//testcase');errors=r.findall('.//error');failures=r.findall('.//failure');skips=r.findall('.//skipped')
files=[stage/'tt_um_cokane_soc.gds',stage/'tt_um_cokane_soc.lef',stage/'tt_um_cokane_soc.v']
result={'run':tag,'result':'PASS' if len(cases)==15 and not(errors or failures or skips) else 'FAIL','cases':len(cases),'errors':len(errors),'failures':len(failures),'skipped':len(skips),'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(root/f'evidence/precheck-{tag}.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copy2(report,root/f'evidence/precheck-{tag}-results.xml');print(json.dumps(result,indent=2));raise SystemExit(0 if result['result']=='PASS' else 1)
