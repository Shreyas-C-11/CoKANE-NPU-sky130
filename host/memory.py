"""Bounded, zero-initialized paged RAM for CPython and MicroPython."""

class Memory:
    def __init__(self, size=0x40000, page_size=1024):
        if size <= 0 or page_size <= 0 or size % page_size:
            raise ValueError('Invalid memory dimensions')
        self.size, self.page_size, self.pages = size, page_size, {}

    def _check(self, address, count=1):
        if address < 0 or count < 0 or address + count > self.size:
            raise ValueError('External address out of range: 0x%x' % address)

    def byte(self, address):
        self._check(address)
        page = self.pages.get(address // self.page_size)
        return 0 if page is None else page[address % self.page_size]

    def write_byte(self, address, value):
        self._check(address)
        if not 0 <= value <= 255:
            raise ValueError('Not a byte')
        index = address // self.page_size
        page = self.pages.get(index)
        if page is None:
            if value == 0:
                return
            page = bytearray(self.page_size)
            self.pages[index] = page
        page[address % self.page_size] = value

    def word(self, address):
        address &= ~3
        self._check(address, 4)
        return sum(self.byte(address + i) << (8*i) for i in range(4))

    def write_word(self, address, value, select=15):
        address &= ~3
        self._check(address, 4)
        if not 0 <= select <= 15 or not 0 <= value <= 0xffffffff:
            raise ValueError('Invalid word or byte enables')
        for i in range(4):
            if select & (1 << i):
                self.write_byte(address + i, (value >> (8*i)) & 255)

    def load_hex(self, path):
        # The frozen objcopy image is one little-endian 32-bit word per line.
        # Clear pages first so a reload cannot retain previous program state.
        self.pages.clear()
        address = 0
        with open(path) as stream:
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                if len(line) != 8:
                    raise ValueError('Expected one 8-digit word per line')
                self.write_word(address, int(line, 16))
                address += 4
        if address == 0:
            raise ValueError('Empty firmware image')
        return address

    def signed_bytes(self, address, count):
        self._check(address, count)
        values = [self.byte(address+i) for i in range(count)]
        return [v-256 if v & 128 else v for v in values]
