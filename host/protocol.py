"""One host sequencer shared by the real board adapter and RTL co-simulation.

Yields reset, sample and tick operations. Only tick produces a rising edge.
The driver holds the clock low while choosing lanes or servicing memory.
"""
STATUS, CAPTURE, ACK, WRITE_DATA = 32, 4, 8, 16

def reset_sequence():
    yield ('reset', True)
    for _ in range(8):
        yield ('tick', STATUS, 0)
    yield ('reset', False)

def read_host_word(write_data=False):
    value = 0
    for lane in range(4):
        byte = yield ('sample', lane | (WRITE_DATA if write_data else 0))
        value |= byte << (8*lane)
    return value

def serve(memory, done_address=0x1000, done_value=0x600d600d,
          cycle_limit=200000):
    cycles, reads, writes = 0, 0, 0
    while cycles < cycle_limit:
        status = yield ('sample', STATUS)
        if status & 128:
            raise RuntimeError('CPU trap asserted')
        if status & 0x60 != 0x60:
            yield ('tick', STATUS, 0)
            cycles += 1
            continue
        address = yield from read_host_word()
        memory._check(address & ~3, 4)
        if status & 16:
            value = yield from read_host_word(True)
            select = status & 15
            memory.write_word(address, value, select)
            writes += 1
            if address & ~3 in (0x1000, 0x30000) and select == 15 and value == 0xbad00bad:
                raise RuntimeError('Firmware reported failure')
            finished = address == done_address and select == 15 and value == done_value
        else:
            value = memory.word(address)
            for lane in range(4):
                yield ('tick', CAPTURE | lane, (value >> (8*lane)) & 255)
            cycles += 4
            reads += 1
            finished = False
        yield ('tick', ACK, 0)
        yield ('tick', 0, 0)
        cycles += 2
        if finished:
            return {'cycles': cycles, 'reads': reads, 'writes': writes}
    raise RuntimeError('Host cycle limit exceeded')

def check_inference(memory, expected):
    if memory.word(0x30004) < 4 or memory.word(0x30008) != 0:
        raise RuntimeError('Inference report is incomplete or failed')
    if memory.word(0x3000c) != expected['prediction']:
        raise RuntimeError('Argmax mismatch')
    for offset, name in [(16, 'expected_a'), (24, 'expected_b'), (32, 'expected_scores')]:
        address, count = memory.word(0x30000+offset), memory.word(0x30004+offset)
        if count != len(expected[name]) or memory.signed_bytes(address, count) != expected[name]:
            raise RuntimeError('Tensor mismatch: '+name)
    return True
