"""OS credential store boundary. Tokens never enter command arguments or files.

Only native macOS Keychain has an implementation in this increment. Other hosts
fail closed; no plaintext/in-memory production fallback is provided.
"""
import ctypes
import sys
from uuid import UUID

SERVICE = 'ai.atmem.architect.infrastructure-maintenance'


class KeychainUnavailable(RuntimeError):
    pass


class MacKeychain:
    def __init__(self):
        if sys.platform != 'darwin':
            raise KeychainUnavailable('A qualified OS keychain adapter is required')
        try:
            self.cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
            self.sec = ctypes.CDLL('/System/Library/Frameworks/Security.framework/Security')
            ptr = ctypes.c_void_p
            signatures = {
                'CFStringCreateWithCString': (ptr, [ptr, ctypes.c_char_p, ctypes.c_uint32]),
                'CFDataCreate': (ptr, [ptr, ctypes.c_char_p, ctypes.c_long]),
                'CFDictionaryCreate': (ptr, [ptr, ctypes.POINTER(ptr), ctypes.POINTER(ptr), ctypes.c_long, ptr, ptr]),
                'CFRelease': (None, [ptr]), 'CFDataGetLength': (ctypes.c_long, [ptr]),
                'CFDataGetBytePtr': (ptr, [ptr]),
            }
            for name, (result, arguments) in signatures.items():
                fn = getattr(self.cf, name)
                fn.restype, fn.argtypes = result, arguments
            for name, args in [('SecItemAdd', [ptr, ptr]), ('SecItemCopyMatching', [ptr, ctypes.POINTER(ptr)]), ('SecItemDelete', [ptr])]:
                fn = getattr(self.sec, name)
                fn.restype, fn.argtypes = ctypes.c_int32, args
        except (OSError, AttributeError):
            raise KeychainUnavailable('Native Keychain services are unavailable') from None

    def constant(self, name):
        try:
            return ctypes.c_void_p.in_dll(self.sec, name).value
        except ValueError:
            raise KeychainUnavailable('Required native Keychain policy is unavailable') from None

    def query(self, account, extra=None):
        if not isinstance(account, str) or str(UUID(account)) != account:
            raise ValueError('An exact credential reference is required')
        values = {'kSecClass': self.constant('kSecClassGenericPassword'),
                  'kSecAttrService': SERVICE, 'kSecAttrAccount': account,
                  'kSecUseAuthenticationUI': self.constant('kSecUseAuthenticationUIFail'), **(extra or {})}
        allocated, keys, items = [], [], []
        try:
            for key, value in values.items():
                keys.append(self.constant(key))
                if isinstance(value, str):
                    handle = self.cf.CFStringCreateWithCString(None, value.encode('utf-8'), 0x08000100)
                    allocated.append(handle)
                elif isinstance(value, bytes):
                    handle = self.cf.CFDataCreate(None, value, len(value))
                    allocated.append(handle)
                elif isinstance(value, bool):
                    handle = ctypes.c_void_p.in_dll(self.cf, 'kCFBooleanTrue' if value else 'kCFBooleanFalse').value
                else:
                    handle = value
                if not handle:
                    raise KeychainUnavailable('Native Keychain allocation failed')
                items.append(handle)
            ptr = ctypes.c_void_p
            callbacks = lambda name: ctypes.addressof(ctypes.c_byte.in_dll(self.cf, name))
            result = self.cf.CFDictionaryCreate(None, (ptr * len(keys))(*keys), (ptr * len(items))(*items), len(keys),
                                                callbacks('kCFTypeDictionaryKeyCallBacks'), callbacks('kCFTypeDictionaryValueCallBacks'))
            if not result:
                raise KeychainUnavailable('Native Keychain query failed')
            return result
        finally:
            for handle in allocated:
                if handle:
                    self.cf.CFRelease(handle)

    def put(self, account, token):
        if not isinstance(token, str) or not 1 <= len(token) <= 1024 or not token.isascii() or any(ord(c) < 33 for c in token):
            raise ValueError('Credential must be bounded printable ASCII')
        query = self.query(account, {'kSecValueData': token.encode('ascii'), 'kSecAttrSynchronizable': False})
        try:
            status = self.sec.SecItemAdd(query, None)
            if status != 0:
                raise KeychainUnavailable('Unlock the local Keychain and retry credential registration')
        finally:
            self.cf.CFRelease(query)

    def get(self, account):
        query = self.query(account, {'kSecReturnData': True, 'kSecMatchLimit': self.constant('kSecMatchLimitOne')})
        result = ctypes.c_void_p()
        try:
            if self.sec.SecItemCopyMatching(query, ctypes.byref(result)) != 0 or not result.value:
                raise KeychainUnavailable('Credential unavailable; unlock Keychain or reconnect')
            count = self.cf.CFDataGetLength(result)
            if not 1 <= count <= 1024:
                raise KeychainUnavailable('Credential exceeds the broker bound')
            return ctypes.string_at(self.cf.CFDataGetBytePtr(result), count).decode('ascii')
        except UnicodeError:
            raise KeychainUnavailable('Credential encoding is unavailable') from None
        finally:
            if result.value:
                self.cf.CFRelease(result)
            self.cf.CFRelease(query)

    def delete(self, account):
        query = self.query(account)
        try:
            status = self.sec.SecItemDelete(query)
            if status not in {0, -25300}:  # errSecItemNotFound is already revoked locally.
                raise KeychainUnavailable('Keychain credential deletion was not confirmed')
        finally:
            self.cf.CFRelease(query)
