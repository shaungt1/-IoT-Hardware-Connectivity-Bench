from __future__ import annotations

import asyncio
import os
import threading
import time
from ctypes import POINTER, Structure, WinDLL, WINFUNCTYPE, byref, c_int, c_void_p, sizeof
from ctypes import wintypes


WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_DEVICECHANGE = 0x0219
DBT_DEVNODES_CHANGED = 0x0007
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004
DBT_DEVTYP_DEVICEINTERFACE = 0x00000005
DEVICE_NOTIFY_WINDOW_HANDLE = 0x00000000
HWND_MESSAGE = -3


class GUID(Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]


class DEV_BROADCAST_DEVICEINTERFACE_W(Structure):
    _fields_ = [
        ("dbcc_size", wintypes.DWORD),
        ("dbcc_devicetype", wintypes.DWORD),
        ("dbcc_reserved", wintypes.DWORD),
        ("dbcc_classguid", GUID),
        ("dbcc_name", wintypes.WCHAR * 1),
    ]


WNDPROC = WINFUNCTYPE(wintypes.LPARAM, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", c_int),
        ("cbWndExtra", c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


def _guid(data1: int, data2: int, data3: int, tail: tuple[int, ...]) -> GUID:
    return GUID(data1, data2, data3, (wintypes.BYTE * 8)(*tail))


GUID_DEVINTERFACE_USB_DEVICE = _guid(0xA5DCBF10, 0x6530, 0x11D2, (0x90, 0x1F, 0x00, 0xC0, 0x4F, 0xB9, 0x51, 0xED))
GUID_DEVINTERFACE_COMPORT = _guid(0x86E0D1E0, 0x8089, 0x11D0, (0x9C, 0xE4, 0x08, 0x00, 0x3E, 0x30, 0x1F, 0x73))


def _portable_device_snapshot() -> tuple[str, ...]:
    """Return a stable, metadata-only USB/serial snapshot for portable polling."""
    identities: set[str] = set()
    try:
        from serial.tools import list_ports

        for port in list_ports.comports():
            identities.add(
                "serial:"
                + ":".join(
                    str(value or "")
                    for value in (port.device, port.vid, port.pid, port.serial_number, port.location)
                )
            )
    except Exception:
        pass
    try:
        import usb.core

        for device in usb.core.find(find_all=True) or ():
            identities.add(
                f"usb:{getattr(device, 'bus', '')}:{getattr(device, 'address', '')}:"
                f"{getattr(device, 'idVendor', '')}:{getattr(device, 'idProduct', '')}"
            )
    except Exception:
        pass
    return tuple(sorted(identities))


def current_local_device_ids() -> dict[str, set[str] | None]:
    """Return fast, descriptor-only presence for cached local interfaces.

    A ``None`` value means that provider failed and must not be used to remove
    cached devices. This keeps a transient libusb error from looking like a
    physical disconnect.
    """
    serial_ids: set[str] | None = set()
    usb_ids: set[str] | None = set()
    try:
        from serial.tools import list_ports

        serial_ids = {f"serial:{port.device}" for port in list_ports.comports()}
    except Exception:
        serial_ids = None
    try:
        import usb.core

        usb_ids = {
            f"usb:{int(device.idVendor):04X}:{int(device.idProduct):04X}:{device.bus}:{device.address}"
            for device in (usb.core.find(find_all=True) or ())
        }
    except Exception:
        usb_ids = None
    return {"serial": serial_ids, "usb_identity": usb_ids}


def filter_present_local_devices(
    inventory: list[dict[str, object]],
    presence: dict[str, set[str] | None],
) -> list[dict[str, object]]:
    """Remove only cached local interfaces that a reliable fast scan disproves."""
    return [
        item
        for item in inventory
        if item.get("kind") not in presence
        or presence[str(item.get("kind"))] is None
        or str(item.get("id")) in presence[str(item.get("kind"))]
    ]


class HostDeviceEvents:
    """Bridges native or polled host device changes into one asyncio event."""

    def __init__(self, snapshot_provider=None, poll_seconds: float = 1.0, platform_name: str | None = None) -> None:
        self._event: asyncio.Event | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._hwnd: int | None = None
        self._wndproc = None
        self._ready = threading.Event()
        self._error: str | None = None
        self._snapshot_provider = snapshot_provider or _portable_device_snapshot
        self._poll_seconds = max(0.1, poll_seconds)
        self._stop_event = threading.Event()
        self._event_count = 0
        self._last_event_at: float | None = None
        self._platform_name = platform_name or os.name

    def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._event = asyncio.Event()
        self._event.set()
        self._stop_event.clear()
        if self._platform_name != "nt":
            self._thread = threading.Thread(target=self._poll_loop, name="iot-bench-hotplug-poll", daemon=True)
            self._thread.start()
            return
        self._thread = threading.Thread(target=self._message_loop, name="iot-bench-hotplug", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2)

    async def wait(self, reconciliation_seconds: float = 2.0) -> bool:
        if self._event is None:
            raise RuntimeError("Host device event source has not been started")
        try:
            await asyncio.wait_for(self._event.wait(), timeout=reconciliation_seconds)
        except TimeoutError:
            return False
        self._event.clear()
        return True

    def stop(self) -> None:
        self._stop_event.set()
        if self._platform_name == "nt" and self._hwnd:
            user32 = WinDLL("user32", use_last_error=True)
            user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None
        self._hwnd = None

    def snapshot(self) -> dict[str, object]:
        return {
            "mode": "windows_devicechange" if self._platform_name == "nt" else "polling_snapshot",
            "active": bool(self._hwnd) if self._platform_name == "nt" else bool(self._thread and self._thread.is_alive()),
            "reconciliation_seconds": 2,
            "poll_seconds": None if self._platform_name == "nt" else self._poll_seconds,
            "event_count": self._event_count,
            "last_event_at": self._last_event_at,
            "error": self._error,
        }

    def _notify(self) -> None:
        self._event_count += 1
        self._last_event_at = time.time()
        if self._loop and self._event and not self._loop.is_closed():
            try:
                self._loop.call_soon_threadsafe(self._event.set)
            except RuntimeError:
                pass

    def _poll_loop(self) -> None:
        try:
            previous = self._snapshot_provider()
            while not self._stop_event.wait(self._poll_seconds):
                current = self._snapshot_provider()
                if current != previous:
                    previous = current
                    self._notify()
        except Exception as error:
            self._error = f"Portable device polling stopped: {error}"
            self._notify()

    def _message_loop(self) -> None:
        user32 = WinDLL("user32", use_last_error=True)
        kernel32 = WinDLL("kernel32", use_last_error=True)
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        user32.RegisterClassW.argtypes = [POINTER(WNDCLASSW)]
        user32.RegisterClassW.restype = wintypes.ATOM
        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            c_int,
            c_int,
            c_int,
            c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            c_void_p,
        ]
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.DefWindowProcW.restype = wintypes.LPARAM
        user32.DestroyWindow.argtypes = [wintypes.HWND]
        user32.DestroyWindow.restype = wintypes.BOOL
        user32.PostQuitMessage.argtypes = [c_int]
        user32.GetMessageW.argtypes = [POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user32.GetMessageW.restype = wintypes.BOOL
        user32.TranslateMessage.argtypes = [POINTER(wintypes.MSG)]
        user32.TranslateMessage.restype = wintypes.BOOL
        user32.DispatchMessageW.argtypes = [POINTER(wintypes.MSG)]
        user32.DispatchMessageW.restype = wintypes.LPARAM
        user32.RegisterDeviceNotificationW.argtypes = [wintypes.HANDLE, c_void_p, wintypes.DWORD]
        user32.RegisterDeviceNotificationW.restype = wintypes.HANDLE
        user32.UnregisterDeviceNotification.argtypes = [wintypes.HANDLE]
        user32.UnregisterDeviceNotification.restype = wintypes.BOOL
        class_name = "IoTHardwareBenchHotplugWindow"

        @WNDPROC
        def window_proc(hwnd, message, wparam, lparam):
            if message == WM_DEVICECHANGE and wparam in {DBT_DEVNODES_CHANGED, DBT_DEVICEARRIVAL, DBT_DEVICEREMOVECOMPLETE}:
                self._notify()
                return 0
            if message == WM_CLOSE:
                user32.DestroyWindow(hwnd)
                return 0
            if message == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)

        self._wndproc = window_proc
        instance = kernel32.GetModuleHandleW(None)
        window_class = WNDCLASSW(0, window_proc, 0, 0, instance, None, None, None, None, class_name)
        user32.RegisterClassW(byref(window_class))
        hwnd = user32.CreateWindowExW(0, class_name, class_name, 0, 0, 0, 0, 0, HWND_MESSAGE, None, instance, None)
        if not hwnd:
            self._error = "Unable to create the Windows device-notification message window"
            self._ready.set()
            self._notify()
            return
        self._hwnd = hwnd
        self._ready.set()
        handles: list[int] = []
        for class_guid in (GUID_DEVINTERFACE_USB_DEVICE, GUID_DEVINTERFACE_COMPORT):
            device_filter = DEV_BROADCAST_DEVICEINTERFACE_W()
            device_filter.dbcc_size = sizeof(device_filter)
            device_filter.dbcc_devicetype = DBT_DEVTYP_DEVICEINTERFACE
            device_filter.dbcc_classguid = class_guid
            handle = user32.RegisterDeviceNotificationW(hwnd, byref(device_filter), DEVICE_NOTIFY_WINDOW_HANDLE)
            if handle:
                handles.append(handle)
        message = wintypes.MSG()
        while user32.GetMessageW(byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(byref(message))
            user32.DispatchMessageW(byref(message))
        for handle in handles:
            user32.UnregisterDeviceNotification(handle)
