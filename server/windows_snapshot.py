"""Bounded Windows snapshots with held, no-reparse, read-sharing-only handles.

All handles stay open until the complete tree is audited. Writers, replacements,
reparse points, hard links and non-disk objects fail closed; nothing is executed.
References: Microsoft CreateFileW and GetFileInformationByHandle documentation.
"""
import ctypes
from ctypes import wintypes as w
import hashlib
import io
import os
from pathlib import Path
import stat
import zipfile
from .engineering_sessions import SessionError


def snapshot(workspace, *, excluded, max_bytes, max_files):
    if os.name != 'nt':
        raise SessionError('Windows snapshot handles require Windows')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    class Info(ctypes.Structure):
        _fields_ = [('attributes', w.DWORD), ('created', w.FILETIME),
                    ('accessed', w.FILETIME), ('written', w.FILETIME),
                    ('volume', w.DWORD), ('size_hi', w.DWORD), ('size_lo', w.DWORD),
                    ('links', w.DWORD), ('index_hi', w.DWORD), ('index_lo', w.DWORD)]
    kernel.CreateFileW.argtypes = [w.LPCWSTR,w.DWORD,w.DWORD,w.LPVOID,w.DWORD,w.DWORD,w.HANDLE]
    kernel.CreateFileW.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.CloseHandle.restype = w.BOOL
    kernel.GetFileInformationByHandle.argtypes = [w.HANDLE,ctypes.POINTER(Info)]
    kernel.GetFileInformationByHandle.restype = w.BOOL
    kernel.GetFileType.argtypes = [w.HANDLE]
    kernel.GetFileType.restype = w.DWORD
    kernel.GetFinalPathNameByHandleW.argtypes = [w.HANDLE,w.LPWSTR,w.DWORD,w.DWORD]
    kernel.GetFinalPathNameByHandleW.restype = w.DWORD
    kernel.ReadFile.argtypes = [w.HANDLE,w.LPVOID,w.DWORD,ctypes.POINTER(w.DWORD),w.LPVOID]
    kernel.ReadFile.restype = w.BOOL
    invalid = ctypes.c_void_p(-1).value
    held, entries, exclusions, observed = [], [], [], {}
    output, total = io.BytesIO(), 0
    root = Path(workspace).absolute()
    if str(root).startswith('\\\\'):
        raise SessionError('Windows capture requires a local disk workspace')
    def fail():
        raise SessionError('Artifact contains a changed, linked or unavailable Windows entry; no package was saved')
    def information(handle):
        info=Info()
        if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)):fail()
        if info.attributes & 0x400 or kernel.GetFileType(handle)!=1:fail()
        return info
    def identity(info):
        return (info.volume,info.index_hi,info.index_lo,info.attributes,info.links,
                info.size_hi,info.size_lo,info.created.dwHighDateTime,info.created.dwLowDateTime,
                info.written.dwHighDateTime,info.written.dwLowDateTime)
    def open_entry(path):
        # No FILE_SHARE_WRITE or FILE_SHARE_DELETE: retain every handle through audit.
        handle=kernel.CreateFileW('\\\\?\\'+str(path),0x80000000,1,None,3,0x02200000,None)
        if handle==invalid:fail()
        held.append(handle)
        info=information(handle)
        actual=ctypes.create_unicode_buffer(32768)
        length=kernel.GetFinalPathNameByHandleW(handle,actual,len(actual),0)
        if not length or length>=len(actual) or os.path.normcase(actual.value)!=os.path.normcase('\\\\?\\'+str(path)):fail()
        return handle,info
    def names(path):
        result=[]
        for name in sorted(os.listdir(path)):
            if name in excluded:continue
            if name in {'.','..'} or name.endswith((' ','.')) or any(ord(c)<32 or c in '\\/:"<>|?*' for c in name):fail()
            result.append(name)
        return result
    def walk(path,relative,handle,info,archive):
        nonlocal total
        observed[relative]=(path,handle,identity(info),None)
        if info.attributes & 0x10:
            children=names(path)
            observed[relative]=(path,handle,identity(info),children)
            exclusions.extend((relative+'/' if relative else '')+name for name in sorted(os.listdir(path)) if name in excluded)
            for name in children:
                child_relative=(relative+'/' if relative else '')+name
                child,child_info=open_entry(path/name)
                directory=bool(child_info.attributes & 0x10)
                if len(entries)>=max_files:raise SessionError('Artifact entry limit exceeded; no partial package was saved')
                if directory:
                    entries.append({'path':child_relative+'/','kind':'directory'})
                    item=zipfile.ZipInfo(child_relative+'/');item.external_attr=(stat.S_IFDIR|0o755)<<16
                    archive.writestr(item,b'')
                walk(path/name,child_relative,child,child_info,archive)
        else:
            size=(info.size_hi<<32)|info.size_lo
            if info.links!=1 or total+size>max_bytes:fail()
            content=bytearray()
            while True:
                buffer=ctypes.create_string_buffer(min(1_000_000,max_bytes-total-len(content)+1))
                read=w.DWORD()
                if not kernel.ReadFile(handle,buffer,len(buffer),ctypes.byref(read),None):fail()
                if not read.value:break
                content.extend(buffer.raw[:read.value])
                if total+len(content)>max_bytes:fail()
            if len(content)!=size or identity(information(handle))!=identity(info):fail()
            entries.append({'path':relative,'kind':'file','bytes':size,'sha256':hashlib.sha256(content).hexdigest()})
            item=zipfile.ZipInfo(relative);item.compress_type=zipfile.ZIP_DEFLATED
            mode=0o755 if path.suffix.lower() in {'.sh','.exe'} else 0o644
            item.external_attr=(stat.S_IFREG|mode)<<16
            archive.writestr(item,content)
            total+=size
    try:
        handle,info=open_entry(root)
        if not info.attributes & 0x10:fail()
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED)as archive:
            walk(root,'',handle,info,archive)
        for path,handle,expected,children in observed.values():
            if identity(information(handle))!=expected or children is not None and names(path)!=children:fail()
        return output.getvalue(),entries,exclusions
    except OSError:
        fail()
    finally:
        for handle in reversed(held):kernel.CloseHandle(handle)
