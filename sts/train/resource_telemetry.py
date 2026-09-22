"""Read-only host/process memory telemetry, independent of model semantics."""
import ctypes
import os
import psutil

class MemoryStatus(ctypes.Structure):
    _fields_ = [("length",ctypes.c_ulong),("load",ctypes.c_ulong)] + [
        (k,ctypes.c_ulonglong) for k in ("total_phys","avail_phys","total_page","avail_page","total_virtual","avail_virtual","avail_extended")]

def memory_sample():
    process = psutil.Process()
    info = process.memory_info()
    vm = psutil.virtual_memory()
    values = dict(process_rss_mb=info.rss/1024**2,
        process_private_mb=getattr(info,"private",info.vms)/1024**2,
        process_peak_rss_mb=getattr(info,"peak_wset",info.rss)/1024**2,
        available_ram_mb=vm.available/1024**2, ram_percent=vm.percent)
    if hasattr(info,"num_page_faults"):values["process_page_faults"]=info.num_page_faults
    if os.name=="nt":
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("GlobalMemoryStatusEx failed")
        values.update(commit_used_mb=(status.total_page-status.avail_page)/1024**2,
                      commit_limit_mb=status.total_page/1024**2)
    return values
