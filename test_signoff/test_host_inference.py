"""Observe complete compiled inference through chip pins, at RTL or gates."""
import hashlib,json,os,pathlib
import cocotb
from cocotb.triggers import Timer
ROOT=pathlib.Path(__file__).resolve().parents[1]

@cocotb.test()
async def compiled_inference_through_pins(d):
    fixture=json.loads(pathlib.Path(os.environ['SIGNOFF_FIXTURE']).read_text())
    for step in range(8000):
        await Timer(1,unit='ms')
        if int(d.fault.value):raise AssertionError('CPU trap, host address fault or driven host-input pins')
        if int(d.finished.value):break
        if step%500==0:d._log.info('SIGNOFF_HOST_PROGRESS cycles=%d',int(d.cycles.value))
    else:raise AssertionError('Pin-host compiled inference exceeded 160 million clocks')
    def word(address):return int(d.mem[address//4].value)
    def vector(address,count):
        result=[]
        for a in range(address,address+count):
            v=(word(a&~3)>>(8*(a&3)))&255;result.append(v-256 if v&128 else v)
        return result
    assert word(0x30004)>=4 and word(0x30008)==0
    assert word(0x3000c)==fixture['prediction']
    for off,key in [(16,'expected_a'),(24,'expected_b'),(32,'expected_scores')]:
        address=word(0x30000+off);count=word(0x30000+off+4)
        assert count==len(fixture[key])
        assert vector(address,count)==fixture[key],key
    sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
    record={'result':'PASS','scope':'Compiled frozen firmware, full synthetic inference through actual chip pins; functional simulation, no SDF','model':os.environ.get('SIGNOFF_MODEL','synthetic'),'simulator':cocotb.SIM_NAME,'tensor_counts':[338,50,10],'cycles':int(d.cycles.value),'external_reads':int(d.reads.value),'external_writes':int(d.writes.value),'firmware_sha256':sha(os.environ['SIGNOFF_FIRMWARE']),'fixture_sha256':sha(os.environ['SIGNOFF_FIXTURE']),'physical_timing_qualified':False}
    if os.environ.get('SIGNOFF_NETLIST'):record['netlist_sha256']=sha(os.environ['SIGNOFF_NETLIST'])
    pathlib.Path(os.environ['SIGNOFF_RESULT']).write_text(json.dumps(record,indent=2)+'\n')
    d._log.info('SIGNOFF_PIN_INFERENCE_PASS %s',record['model'])
