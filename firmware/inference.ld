OUTPUT_ARCH(riscv)
ENTRY(_start)
MEMORY { ram (rwx) : ORIGIN = 0, LENGTH = 256K }
SECTIONS {
  .text : { KEEP(*(.text.start)) *(.text*) } > ram
  .rodata : { *(.rodata*) *(.srodata*) } > ram
  .data : { *(.data*) *(.sdata*) } > ram
  .bss (NOLOAD) : {
    . = ALIGN(4); __bss_start = .;
    *(.bss*) *(.sbss*) *(COMMON)
    . = ALIGN(4); __bss_end = .;
  } > ram
  ASSERT(__bss_end < 0x2e000, "Firmware overlaps report/stack reservation")
  _stack_top = 0x3fff0;
}
