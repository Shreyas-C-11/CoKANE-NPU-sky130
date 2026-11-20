"""Observe real compiled RV32E execution; no Python-generated CPU instructions."""
import json,pathlib
import cocotb
from cocotb.triggers import Timer

ROOT=pathlib.Path(__file__).resolve().parents[1]

def byte_array(d,address,length):
    values=[]
    for a in range(address,address+length):
        word=int(d.mem[a//4].value);v=(word>>(8*(a%4)))&255
        values.append(v-256 if v&128 else v)
    return values

@cocotb.test()
async def compiled_cpu_inference(d):
    fixture=json.loads((ROOT/'verification/inference/fixture.json').read_text())
    last_stage=-1
    for _ in range(3000):
        await Timer(1,unit='ms') # Native Verilog clock/RAM; no per-cycle Python.
        stage=int(d.mem[0x30004//4].value)
        if stage!=last_stage:
            d._log.info('CPU_INFERENCE_STAGE %d cycles=%d',stage,int(d.cycles.value));last_stage=stage
        if int(d.finished.value):break
    else:raise AssertionError('Compiled firmware exceeded 60 million clocks')
    assert not int(d.fault.value),'CPU trap or out-of-range external memory access'
    assert int(d.completion.value)==0x600d600d, f'Firmware failure at stage {stage}, error={int(d.mem[0x30008//4].value):08x}'
    words=[int(d.mem[0x30000//4+i].value) for i in range(22)]
    assert words[1]==5
    for address,count,expected in [(words[4],words[5],fixture['expected_a']),
            (words[6],words[7],fixture['expected_b']),(words[8],words[9],fixture['expected_scores'])]:
        assert count==len(expected)
        actual=byte_array(d,address,count)
        assert actual==expected, f'Intermediate tensor mismatch at {address:#x}: {actual[:20]} != {expected[:20]}'
    assert words[3]==fixture['prediction']
    for address,expected in [(words[18],fixture['expected_a']),(words[19],fixture['expected_b']),(words[20],fixture['expected_scores'])]:
        assert byte_array(d,address,len(expected))==expected, 'CPU-only reference tensor mismatch'
    assert words[21]==fixture['prediction']
    stats=dict(zip(['jobs','lut_entries','input_values','output_values','mmio_reads','mmio_writes','compute_cycles','context_cycles'],words[10:18]))
    assert stats['jobs']==206 and 0<stats['lut_entries']<86432
    assert stats['input_values']==16268 and stats['output_values']==398
    assert stats['compute_cycles']==34486
    assert int(d.npu_reads.value)==stats['mmio_reads']+1 # main's ID probe.
    assert int(d.npu_writes.value)==stats['mmio_writes']
    record={'result':'PASS','scope':'Compiled RV32E C scheduler on CPU+MAC+CoKANE RTL with simulation-only external RAM and deterministic randomized wait states','trained_model_accuracy_verified':False,'fixture_seed':fixture['seed'],'tensor_counts':[338,50,10],'scores':fixture['expected_scores'],'prediction':words[3],'simulator':cocotb.SIM_NAME,'clock_hz':20000000,'cpu_cycles':int(d.cycles.value),'external_reads_including_instruction_fetch':int(d.external_reads.value),'external_writes':int(d.external_writes.value),'external_wait_cycles':int(d.wait_cycles.value),'statistics':stats}
    record['hardware_phase_cycles']=int(d.hardware_phase_cycles.value)
    record['cpu_only_reference_cycles']=int(d.cpu_reference_cycles.value)
    record['hardware_phase_ms']=record['hardware_phase_cycles']/20000
    record['cpu_only_reference_ms']=record['cpu_only_reference_cycles']/20000
    record['comparison_scope']='Instrumented accelerator scheduler versus straightforward CPU-only arithmetic with identical signed data/tables and range scans; specified simulation RAM waits, no speedup assumption'
    record['simulation_inference_ms']=record['cpu_cycles']/20000
    record['accelerator_busy_ms']=stats['compute_cycles']/20000
    (ROOT/'evidence/cokane/inference-validation.json').write_text(json.dumps(record,indent=2)+'\n')
    d._log.info('COMPILED_CPU_INFERENCE_PASS cycles=%d compute=%d scores=%s',record['cpu_cycles'],stats['compute_cycles'],fixture['expected_scores'])
