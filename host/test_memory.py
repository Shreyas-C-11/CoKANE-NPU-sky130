"""Host memory safety checks, without a board or simulator dependency."""
import tempfile
import unittest
from pathlib import Path
from host.memory import Memory
from host.protocol import serve

class MemoryTest(unittest.TestCase):
    def test_partial_write_and_sparse_stack(self):
        m = Memory()
        m.write_word(4, 0x11223344)
        m.write_word(5, 0xaabbccdd, 2)
        self.assertEqual(m.word(4), 0x1122cc44)
        m.write_word(0x3fffc, 0x600d600d)
        self.assertEqual(m.word(0x3fffc), 0x600d600d)
        self.assertEqual(m.word(0x30000), 0)
        self.assertEqual(len(m.pages), 2)

    def test_out_of_range(self):
        m = Memory()
        for action in [lambda: m.word(0x40000), lambda: m.write_word(-4, 0),
                       lambda: m.write_word(0, 0, 16)]:
            with self.assertRaises(ValueError):
                action()

    def test_bad_image(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'image.hex'
            p.write_text('not-hex\n')
            with self.assertRaises(ValueError):
                Memory().load_hex(str(p))

    def test_cpu_trap_and_idle_limit(self):
        g = serve(Memory())
        next(g)
        with self.assertRaisesRegex(RuntimeError, 'trap'):
            g.send(128)
        g = serve(Memory(), cycle_limit=1)
        self.assertEqual(next(g), ('sample', 32))
        self.assertEqual(g.send(0), ('tick', 32, 0))
        with self.assertRaisesRegex(RuntimeError, 'limit'):
            g.send(None)

if __name__ == '__main__':
    unittest.main()
