#!/usr/bin/env python3
import sys
from unicorn import *
from unicorn.x86_const import *
from elftools.elf.elffile import ELFFile

PAGE = 0x1000

def align_down(x, a=PAGE):
    return x & ~(a - 1)

def align_up(x, a=PAGE):
    return (x + a - 1) & ~(a - 1)

def load_elf(mu, path):
    with open(path, "rb") as f:
        elf = ELFFile(f)
        entry = elf.header["e_entry"]

        for seg in elf.iter_segments():
            if seg["p_type"] != "PT_LOAD":
                continue

            vaddr = seg["p_vaddr"]
            memsz = seg["p_memsz"]
            filesz = seg["p_filesz"]
            data = seg.data()

            start = align_down(vaddr)
            end = align_up(vaddr + memsz)
            size = end - start

            flags = seg["p_flags"]
            perms = 0
            if flags & 4:
                perms |= UC_PROT_READ
            if flags & 2:
                perms |= UC_PROT_WRITE
            if flags & 1:
                perms |= UC_PROT_EXEC

            mu.mem_map(start, size, perms)
            if filesz:
                mu.mem_write(vaddr, data)

        return entry

def hook_syscall(mu, user_data):
    rax = mu.reg_read(UC_X86_REG_RAX)

    if rax == 1:  # write(fd, buf, count)
        fd = mu.reg_read(UC_X86_REG_RDI)
        buf = mu.reg_read(UC_X86_REG_RSI)
        cnt = mu.reg_read(UC_X86_REG_RDX)
        try:
            data = bytes(mu.mem_read(buf, cnt))
        except UcError:
            data = b"<unmapped buffer>"
        print(f"[sys_write fd={fd}] {data!r}")
        mu.reg_write(UC_X86_REG_RAX, cnt)
        return

    if rax == 60:  # exit(status)
        status = mu.reg_read(UC_X86_REG_RDI)
        print(f"[sys_exit] status={status}")
        user_data["exit_status"] = status
        mu.emu_stop()
        return

    print(f"[syscall] unsupported rax={rax}")
    user_data["unsupported_syscall"] = rax
    mu.emu_stop()

def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} ./fprem-anti-emu.exe")
        return 1

    mu = Uc(UC_ARCH_X86, UC_MODE_64)

    # stack
    stack_base = 0x70000000
    stack_size = 0x20000
    mu.mem_map(stack_base, stack_size, UC_PROT_READ | UC_PROT_WRITE)
    mu.reg_write(UC_X86_REG_RSP, stack_base + stack_size - 8)

    entry = load_elf(mu, sys.argv[1])
    print(f"[+] entry point: {hex(entry)}")

    state = {"exit_status": None, "unsupported_syscall": None}

    # intercept x86 SYSCALL instruction
    mu.hook_add(UC_HOOK_INSN, hook_syscall, state, 1, 0, UC_X86_INS_SYSCALL)

    try:
        mu.emu_start(entry, 0)
    except UcError as e:
        print(f"[!] Unicorn error: {e}")
        return 2

    if state["exit_status"] is None:
        print("[!] program did not exit cleanly under emulation")
        return 3

    print(f"[+] clean emulated exit status = {state['exit_status']}")
    if state["exit_status"] == 0:
        print("=> took the real_x87 path")
    elif state["exit_status"] == 1:
        print("=> took the simplified_emulation path")
    else:
        print("=> unexpected path")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())