"""Windows-owned child trees and a private lifecycle lease. No DB or shell."""
from __future__ import annotations

import ctypes
from ctypes import wintypes as w
import os
from pathlib import Path
import subprocess
import time


class RuntimeLease:
    def __init__(self, path):
        self.path, self.file = Path(path), None

    def acquire(self):
        import msvcrt
        from app.services.leny_document_storage import _check_path
        if self.file is not None:
            return True
        _check_path(self.path)
        handle = self.path.open('a+b')
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            handle.close()
            return False
        self.file = handle
        if not self.path.stat().st_size:
            handle.write(b'0'); handle.flush()
        return True

    def close(self):
        import msvcrt
        handle, self.file = self.file, None
        if handle is not None:
            try:
                handle.seek(0)
                msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            finally:
                handle.close()


class WindowsChild:
    """Start suspended, join a kill-on-close Job, then resume.

    Assigning before resume also contains Windows venv redirectors and all
    Ollama/OCR descendants. Handles, not process names/PIDs, establish ownership.
    No memory/GPU/concurrency settings or existing processes are modified.
    """
    def __init__(self, command, *, cwd, env):
        if os.name != 'nt':
            raise RuntimeError('LENY_RUNTIME_WINDOWS_REQUIRED')
        self.job = self.process = None
        self.returncode = None
        self.kernel = k = ctypes.WinDLL('kernel32',use_last_error=True)

        class Basic(ctypes.Structure):
            _fields_=[('user',ctypes.c_int64),('job',ctypes.c_int64),('flags',w.DWORD),
                ('minimum',ctypes.c_size_t),('maximum',ctypes.c_size_t),('active',w.DWORD),
                ('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class Extended(ctypes.Structure):
            _fields_=[('basic',Basic),('io',ctypes.c_uint64*6),('process_memory',ctypes.c_size_t),
                ('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        class Startup(ctypes.Structure):
            _fields_=[('cb',w.DWORD),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR),
                *[(name,w.DWORD) for name in ('x','y','xsize','ysize','xchars','ychars','fill','flags')],
                ('show',w.WORD),('reserved2_size',w.WORD),('reserved2',ctypes.c_void_p),
                ('stdin',w.HANDLE),('stdout',w.HANDLE),('stderr',w.HANDLE)]
        class Info(ctypes.Structure):
            _fields_=[('process',w.HANDLE),('thread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]
        class Accounting(ctypes.Structure):
            _fields_=[('times',ctypes.c_int64*4),('faults',w.DWORD),('total',w.DWORD),
                      ('active',w.DWORD),('terminated',w.DWORD)]
        self.accounting_type = Accounting
        k.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR]; k.CreateJobObjectW.restype=w.HANDLE
        k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
        k.QueryInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.c_void_p]
        k.CreateProcessW.argtypes=[w.LPCWSTR,w.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,w.BOOL,w.DWORD,
                                  ctypes.c_void_p,w.LPCWSTR,ctypes.POINTER(Startup),ctypes.POINTER(Info)]
        k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
        k.ResumeThread.argtypes=[w.HANDLE]; k.ResumeThread.restype=w.DWORD
        k.TerminateProcess.argtypes=[w.HANDLE,w.UINT]
        k.TerminateJobObject.argtypes=[w.HANDLE,w.UINT]
        k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]; k.WaitForSingleObject.restype=w.DWORD
        k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
        k.CloseHandle.argtypes=[w.HANDLE]
        startup, info = Startup(), Info()
        startup.cb = ctypes.sizeof(startup)
        command=[str(part) for part in command]
        environment=ctypes.create_unicode_buffer('\0'.join(key+'='+value for key,value in sorted(env.items()))+'\0\0')
        try:
            self.job=k.CreateJobObjectW(None,None)
            limits=Extended(); limits.basic.flags=0x2000  # KILL_ON_JOB_CLOSE only
            if not self.job or not k.SetInformationJobObject(self.job,9,ctypes.byref(limits),ctypes.sizeof(limits)):
                raise RuntimeError('LENY_RUNTIME_JOB_FAILED')
            # No shell, inherited handles, visible console or executable code from a model.
            if not k.CreateProcessW(command[0],ctypes.create_unicode_buffer(subprocess.list2cmdline(command)),
                    None,None,False,0x08000000|0x00000400|0x00000004,environment,str(cwd),
                    ctypes.byref(startup),ctypes.byref(info)):
                raise RuntimeError('LENY_RUNTIME_PROCESS_FAILED')
            self.process, self.pid = info.process, info.pid
            if not k.AssignProcessToJobObject(self.job,self.process):
                raise RuntimeError('LENY_RUNTIME_JOB_FAILED')
            if k.ResumeThread(info.thread)==0xffffffff:
                raise RuntimeError('LENY_RUNTIME_PROCESS_FAILED')
        except BaseException:
            if self.process:
                k.TerminateProcess(self.process,1)
            self.close()
            raise
        finally:
            if info.thread:
                k.CloseHandle(info.thread)

    def poll(self):
        if self.process is None:
            return self.returncode
        state=self.kernel.WaitForSingleObject(self.process,0)
        if state==258:
            return None
        code=w.DWORD()
        if state!=0 or not self.kernel.GetExitCodeProcess(self.process,ctypes.byref(code)):
            raise RuntimeError('LENY_RUNTIME_PROCESS_STATE')
        self.returncode=code.value
        return self.returncode

    def close(self):
        job, self.job = self.job, None
        process, self.process = self.process, None
        try:
            if job:
                self.kernel.TerminateJobObject(job,1)
                deadline=time.monotonic()+5
                info=self.accounting_type()
                while self.kernel.QueryInformationJobObject(job,1,ctypes.byref(info),ctypes.sizeof(info),None) and info.active:
                    if time.monotonic()>=deadline:
                        break
                    time.sleep(0.02)
        finally:
            if job:self.kernel.CloseHandle(job)
            if process:
                self.kernel.WaitForSingleObject(process,5000)
                code=w.DWORD()
                if self.kernel.GetExitCodeProcess(process,ctypes.byref(code)):
                    self.returncode=code.value
                self.kernel.CloseHandle(process)
