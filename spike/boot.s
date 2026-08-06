# UEFI x64 boot path spike -- simplified (ConOut only)
#
# Verifies P0-1:
#   - UEFI x64 hands off in long mode (no mode switching asm needed)
#   - EFI calling convention is MS x64: RCX = first arg, RDX = SystemTable at entry
#   - ConOut function pointers work via [protocol + offset]
#   - isa-debug-exit at port 0xf4 propagates to QEMU exit code
#
# CRITICAL: ST offset for ConOut is +64, NOT +80 (+80 is StdErr, see comment below).
# StdErr in OVMF's ConSplitter is NOT registered for the graphics console, so writing
# to it reaches serial but is invisible on the GOP framebuffer.
#
# Build:
#   x86_64-w64-mingw32-gcc -nostdlib -Wl,--subsystem,10 \
#     -Wl,-e,efi_main -Wl,--image-base=0x10000 -o BOOTX64.EFI boot.s

.intel_syntax noprefix

.text
.globl efi_main
.def efi_main; .scl 2; .type 32; .endef

efi_main:
    # UEFI x64 entry convention:
    #   RCX = EFI_HANDLE ImageHandle
    #   RDX = EFI_SYSTEM_TABLE *SystemTable
    push    rbp
    mov     rbp, rsp
    push    rbx
    push    r12
    sub     rsp, 48

    mov     r12, rdx                   # r12 = ST

    # Load ConOut protocol from ST (correct offset is 64, not 80)
    mov     rax, [r12 + 64]            # ConOut (NOT StdErr at 80)
    test    rax, rax
    jz      .Lskip_all
    mov     r13, rax                   # r13 = ConOut (preserve across calls)

    # ClearScreen first (offset 48) -- wipes TianoCore splash if ConOut reaches GOP
    mov     rcx, r13
    sub     rsp, 32
    call    [r13 + 48]                 # ClearScreen
    add     rsp, 32

    # SetAttribute: white on light-red = 0xCF (offset 40)
    mov     rcx, r13
    mov     rdx, 0xCF
    sub     rsp, 32
    call    [r13 + 40]                 # SetAttribute
    add     rsp, 32

    # Print "HELLO\n"
    mov     rcx, r13
    lea     rdx, [rip + msg_hello]
    sub     rsp, 32
    call    [r13 + 8]                  # OutputString
    add     rsp, 32

    # Print "OK\n"
    mov     rcx, r13
    lea     rdx, [rip + msg_ok]
    sub     rsp, 32
    call    [r13 + 8]                  # OutputString
    add     rsp, 32

.Lskip_all:

    # Hang loop (so GUI stays up long enough to see HELLO/OK).
    # Close QEMU window manually when done viewing.
    # (For automated verification, replace with `out 0xf4, al`.)
.Lhang:
    hlt
    jmp     .Lhang

    xor     eax, eax                   # EFI_SUCCESS (unreachable)
    jmp     .Lexit

.Lexit:
    add     rsp, 48
    pop     r12
    pop     rbx
    pop     rbp
    ret

.endef

.data

msg_hello:
    .word   0x0048, 0x0045, 0x004C, 0x004C, 0x004F, 0x000A, 0x0000   # "HELLO\n"

msg_ok:
    .word   0x004F, 0x004B, 0x000A, 0x0000                            # "OK\n"