"""Linux resource and syscall limits for a parser child, not a full VM boundary."""

import ctypes
import errno
import platform
import resource


def restrict() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 * 1024, 32 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    machine = platform.machine()
    if machine == "x86_64":
        architecture, blocked = 0xC000003E, [41, 42, 53, 56, 57, 58, 59, 322, 425, 426, 427, 435]
    elif machine in {"aarch64", "arm64"}:
        architecture, blocked = 0xC00000B7, [198, 199, 203, 220, 221, 281, 425, 426, 427, 435]
    else:
        raise RuntimeError("Unsupported sandbox architecture")

    class Filter(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte), ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]

    class Program(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ushort), ("filter", ctypes.POINTER(Filter))]

    # Validate audit architecture, then block network sockets, process spawning and exec.
    instructions = [(0x20, 0, 0, 4), (0x15, 1, 0, architecture), (0x06, 0, 0, 0x80000000), (0x20, 0, 0, 0)]
    # Reject x32 syscall numbers, and io_uring cannot be used to create sockets indirectly.
    instructions += [(0x35, 0, 1, 0x40000000), (0x06, 0, 0, 0x00050000 | errno.EPERM)]
    for syscall in blocked:
        instructions += [(0x15, 0, 1, syscall), (0x06, 0, 0, 0x00050000 | errno.EPERM)]
    instructions += [(0x06, 0, 0, 0x7FFF0000)]
    filters = (Filter * len(instructions))(*(Filter(*i) for i in instructions))
    program = Program(len(instructions), filters)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:
        raise RuntimeError("Cannot set no-new-privileges")
    if libc.prctl(22, 2, ctypes.byref(program), 0, 0) != 0:
        raise RuntimeError("Cannot enforce parser syscall policy")
