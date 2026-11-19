#!/usr/bin/env python3
import hashlib,json,pathlib,re,sys,xml.etree.ElementTree as ET
root=pathlib.Path(__file__).resolve().parent.parent;tag=sys.argv[1]
xml=root/f'evidence/gl-{tag}-results.xml';log=root/f'evidence/gl-{tag}.log';netlist=root/f'runs/{tag}/final/pnl/tt_um_cokane_soc.pnl.v'
r=ET.parse(xml).getroot();cases=r.findall('.//testcase');text=log.read_text(errors='replace')
rc=int((root/f'evidence/gl-{tag}-exit-code.txt').read_text())
boots=re.findall(r'Firmware PASS seed=(\d+) transactions=(\d+) reset=(\w+)',text)
passed=rc==0 and bool(cases) and not r.findall('.//failure') and not r.findall('.//error') and not r.findall('.//skipped') and len(boots)==2 and 'NEGATIVE_CONTROL_PASS' in text
result={'run':tag,'result':'PASS' if passed else 'FAIL','type':'functional_gate_level','process_exit':rc,'testcases':len(cases),'boots':[{'seed':int(s),'transactions':int(n),'reset':mode} for s,n,mode in boots],'netlist_sha256':hashlib.sha256(netlist.read_bytes()).hexdigest(),'sdf_annotated':False,'wrong_expected_value_negative_control':'NEGATIVE_CONTROL_PASS' in text}
(root/f'evidence/gl-{tag}-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(0 if passed else 1)
