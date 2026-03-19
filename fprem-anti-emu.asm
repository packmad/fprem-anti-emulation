global _start

section .bss
    var_50  resb 10
    var_60  resb 10
    var_70  resb 10
    sw      resw 1

section .text
_start:
    finit

    ; Build two 80-bit values manually.
    ; We keep the same trick style:
    ; - low 64 bits written directly
    ; - top 16 bits hold sign/exponent

    mov     r13, 0x8000000000000001
    mov     rdx, 0x8000000000000000

    ; var_50 = LARGE value (this becomes ST0 before FPREM)
    mov     qword [var_50], r13
    mov     word  [var_50 + 8], 7FFEh

    ; var_60 = smaller value, using the visible bit-shaping trick
    add     r13, 2
    mov     qword [var_60], r13

    shr     rdx, 30h
    and     edx, 8000h
    or      edx, 7FBEh
    mov     word [var_60 + 8], dx

    ; Same visible sequence from the screenshot
    fld     tword [var_60]
    fld     tword [var_50]
    fprem

    fnstsw  ax
    mov     [sw], ax
    fstp    tword [var_70]

    ffree   st0
    fincstp

    ; Checking the C2 flag
    test    ax, 0400h 
    jnz     .real_like

.emu_like:
    mov     eax, 60
    mov     edi, 1
    syscall

.real_like:
    mov     eax, 60
    xor     edi, edi
    syscall
