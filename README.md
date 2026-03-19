# fprem-anti-emulation

A minimal proof-of-concept demonstrating an **anti-emulation technique
based on x87 floating-point behavior**, specifically leveraging quirks
of the `FPREM` instruction and 80-bit extended precision.

📚 Credits: I learned this technique by watching this presentation at RE//verse 2026: [Deobfuscation of a Real World Binary Obfuscator by James McGowan and Bas Zweers](https://www.youtube.com/watch?v=3LtwqJM3Qjg&t=1652s)

------------------------------------------------------------------------

## 🧠 Overview

Modern emulators often simplify or incompletely implement legacy x87
floating-point semantics. This project shows how carefully crafted
inputs combined with a **single `FPREM` instruction** can expose
differences between:

-   ✅ Real hardware (faithful x87 behavior)
-   ⚠️ Emulators (e.g., Unicorn, some QEMU configurations)

The key signal is the **C2 flag** in the x87 status word.

------------------------------------------------------------------------

## ⚙️ The Trick

This technique exploits three key properties of the x87 FPU:

1.  80-bit extended precision format
2.  Manual control over floating-point bit patterns
3.  Iterative (non-trivial) semantics of `FPREM`

------------------------------------------------------------------------

### 🧩 Step-by-step breakdown

The full code is [here](./fprem-anti-emu.asm)

#### 1. Crafting 80-bit floating-point values manually

The x87 uses 80-bit extended precision:

-   1-bit sign
-   15-bit exponent
-   64-bit significand (explicit integer bit)

Memory layout (little endian):

    [0..7]   → significand (64 bits)
    [8..9]   → sign + exponent (16 bits)

We construct values directly in memory:

    mov qword [var], r13
    mov word  [var+8], dx

This gives precise control over exponent and sign.

------------------------------------------------------------------------

#### 2. Forcing a large exponent gap

We construct two operands such that:

-   ST(0) = very large value (e.g., exponent ≈ 0x7FFE)
-   ST(1) = smaller value (e.g., exponent ≈ 0x7FBE)

This creates a large exponent difference.

------------------------------------------------------------------------

#### 3. Loading into the x87 stack

    fld tword [small]
    fld tword [large]

Now: - ST(0) = large - ST(1) = small

------------------------------------------------------------------------

#### 4. Executing a single FPREM

    fprem

`FPREM` performs iterative reduction and may not compute the final
result in one step.

------------------------------------------------------------------------

#### 5. Checking the C2 flag

    fnstsw ax
    test ax, 0x0400

-   C2 = 1 → partial reduction
-   C2 = 0 → final result

------------------------------------------------------------------------

### 🎯 Why this breaks emulators

Real hardware: - Uses full 80-bit precision - Performs iterative
reduction - Produces C2 = 1 in this setup

Some emulators: - Approximate using 64-bit floats - Skip iteration -
Produce C2 = 0

------------------------------------------------------------------------

## 🔬 Reproducibility

### Native

    nasm -felf64 fprem-anti-emu.asm -o fprem.o
    ld fprem.o -o fprem
    ./fprem ; echo $?

------------------------------------------------------------------------

### Unicorn

    pip install unicorn pyelftools
    python3 unicorn_emulate.py ./fprem

------------------------------------------------------------------------

