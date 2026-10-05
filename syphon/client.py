"""Syphon clients with native notifications and asyncio frame availability."""

import asyncio
import inspect
import logging
import math
import threading
import weakref
from abc import ABC
from typing import Any, Callable, Optional

import Metal
import objc

from syphon import _native
from syphon.server_directory import SyphonServerDescription
from syphon.utils import opengl

_logger = logging.getLogger(__name__)
_native_callback = threading.local()
_callback_condition = threading.Condition()
_active_native_callbacks = {}


class BaseSyphonClient(ABC):
    """Common client API. Notifications signal availability, not a queue of every frame.

    Handlers receive this Python client. Unless ``callback_loop`` is supplied, they run
    on Syphon's background thread and must be short, synchronous, and avoid UI/OpenGL
    work. Use ``stop()`` or a context manager for deterministic cleanup.
    """

    def __init__(self, description, *, new_frame_handler=None, callback_loop=None):
        if new_frame_handler is not None and (
            not callable(new_frame_handler) or inspect.iscoroutinefunction(new_frame_handler)
        ):
            raise TypeError("new_frame_handler must be a synchronous callable")
        if callback_loop is not None and callback_loop.is_closed():
            raise ValueError("callback_loop must not be closed")
        self._description = description
        self._queue_key = getattr(description, "uuid", None)
        self._state_lock = threading.Lock()
        self._stopped = False
        self._ready = False
        self._handler = new_frame_handler
        self._callback_loop = callback_loop
        self._callback_scheduled = False
        self._waiters = set()
        self.context = None
        reference = weakref.ref(self)
        queue_key = self._queue_key

        def native_handler(_native_client):
            with _callback_condition:
                _active_native_callbacks[queue_key] = _active_native_callbacks.get(queue_key, 0) + 1
            previous = getattr(_native_callback, "active", False)
            _native_callback.active = True
            try:
                client = reference()
                if client is not None:
                    client._receive_frame()
            except BaseException:
                # Python exceptions must never unwind through an Objective-C block.
                _logger.exception("Syphon frame notification failed")
            finally:
                _native_callback.active = previous
                with _callback_condition:
                    _active_native_callbacks[queue_key] -= 1
                    if not _active_native_callbacks[queue_key]:
                        del _active_native_callbacks[queue_key]
                    _callback_condition.notify_all()

        self._native_handler = native_handler

    def _finish_initialization(self, context):
        with self._state_lock:
            self.context = context
            self._ready = context is not None
            self._stopped = context is None
        if context is None:
            raise RuntimeError("Syphon could not create the client")

    @property
    def is_valid(self) -> bool:
        """Whether this client has a working connection and has not been stopped."""
        with self._state_lock:
            context = None if self._stopped else self.context
        return context is not None and bool(context.isValid())

    @property
    def has_new_frame(self) -> bool:
        """Whether a frame is available since the last ``new_frame_image`` access."""
        with self._state_lock:
            context = None if self._stopped else self.context
        return context is not None and bool(context.hasNewFrame())

    @property
    def new_frame_image(self) -> Any:
        """Fetch the latest native texture/image, or None. This consumes the new-frame flag.

        Keep the returned object alive during use; PyObjC manages its native ownership.
        OpenGL access must happen with the appropriate context on the application's thread.
        """
        with self._state_lock:
            context = None if self._stopped else self.context
        return None if context is None else context.newFrameImage()

    @property
    def server_description(self) -> SyphonServerDescription:
        """The native server description, including updates observed by Syphon."""
        with self._state_lock:
            if self._stopped or self.context is None:
                return self._description
            context = self.context
        return SyphonServerDescription.from_native(context.serverDescription())

    @staticmethod
    def _resolve_waiter(future, error=None):
        if not future.done():
            if error is None:
                future.set_result(None)
            else:
                future.set_exception(error)

    def _notify_waiters(self, waiters, error=None):
        for loop, future in waiters:
            try:
                loop.call_soon_threadsafe(self._resolve_waiter, future, error)
            except RuntimeError:
                # The application's event loop has already closed.
                pass

    def _receive_frame(self):
        with self._state_lock:
            if self._stopped or not self._ready:
                return
            waiters = tuple(self._waiters)
            self._waiters.clear()
            handler = self._handler
            loop = self._callback_loop
            schedule = handler is not None and (loop is None or not self._callback_scheduled)
            if schedule and loop is not None:
                self._callback_scheduled = True
        self._notify_waiters(waiters)
        if schedule:
            if loop is None:
                self._deliver_callback()
            else:
                try:
                    loop.call_soon_threadsafe(self._deliver_callback)
                except RuntimeError:
                    with self._state_lock:
                        self._callback_scheduled = False
                    _logger.warning("Cannot deliver Syphon callback: callback_loop is closed")

    def _deliver_callback(self):
        with self._state_lock:
            self._callback_scheduled = False
            handler = None if self._stopped else self._handler
            loop = self._callback_loop
        if handler is None:
            return
        try:
            result = handler(self)
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise TypeError("Frame handlers must be synchronous; schedule coroutine work on an asyncio loop")
        except BaseException as error:
            if loop is None:
                _logger.exception("Syphon frame handler failed")
            else:
                loop.call_exception_handler(
                    {"message": "Syphon frame handler failed", "exception": error, "client": self}
                )

    async def wait_for_frame(self, timeout: Optional[float] = None) -> None:
        """Wait for availability without fetching a frame; supports concurrent waiters.

        Raises asyncio.TimeoutError on timeout, ConnectionError on disconnect, and
        RuntimeError on stop. Cancellation only removes the cancelling waiter's registration.
        Notifications may coalesce, and another consumer may fetch the frame first.
        """
        if timeout is not None and (not math.isfinite(timeout) or timeout < 0):
            raise ValueError("timeout must be a finite nonnegative number or None")
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        waiter = (loop, future)
        deadline = None if timeout is None else loop.time() + timeout
        with self._state_lock:
            if self._stopped:
                raise RuntimeError("Syphon client is stopped")
            # Register before checking the native flag to avoid lost wakeups.
            self._waiters.add(waiter)
        try:
            while True:
                with self._state_lock:
                    if self._stopped:
                        raise RuntimeError("Syphon client is stopped")
                if not self.is_valid:
                    raise ConnectionError("Syphon server disconnected")
                if self.has_new_frame:
                    return
                if future.done():
                    return future.result()
                remaining = None if deadline is None else deadline - loop.time()
                if remaining is not None and remaining <= 0:
                    raise asyncio.TimeoutError()
                # Syphon has no disconnect block; check validity only during active waits.
                await asyncio.wait({future}, timeout=0.1 if remaining is None else min(0.1, remaining))
        finally:
            with self._state_lock:
                self._waiters.discard(waiter)
            if future.done() and not future.cancelled():
                future.exception()  # Retrieve shutdown errors even if another check raised first.
            else:
                future.cancel()

    def stop(self):
        """Stop once and wake pending waits. Never call from a native frame callback."""
        if getattr(_native_callback, "active", False):
            raise RuntimeError(
                "Cannot stop a client from a native frame callback; use the application thread or asyncio"
            )
        with self._state_lock:
            if self._stopped:
                return
            self._stopped = True
            self._handler = None
            waiters = tuple(self._waiters)
            self._waiters.clear()
            context = self.context
        self._notify_waiters(waiters, RuntimeError("Syphon client is stopped"))
        # Native stop holds its own lock while synchronously draining the frame queue.
        # An in-flight callback (including a peer's callback on that queue) might be
        # reading this client's native properties. Drain Python callbacks first to
        # avoid a native lock/queue inversion. New callbacks see the stopped flag.
        with _callback_condition:
            _callback_condition.wait_for(lambda: _active_native_callbacks.get(self._queue_key, 0) == 0)
        # Never hold a Python state lock across native shutdown.
        if context is not None:
            context.stop()

    def __enter__(self):
        with self._state_lock:
            if self._stopped:
                raise RuntimeError("Syphon client is stopped")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


class SyphonMetalClient(BaseSyphonClient):
    """Receive Metal textures; optional callbacks follow ``BaseSyphonClient`` threading rules."""

    def __init__(
        self,
        description: SyphonServerDescription,
        device: Optional[Any] = None,
        *,
        new_frame_handler: Optional[Callable[[BaseSyphonClient], None]] = None,
        callback_loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        super().__init__(description, new_frame_handler=new_frame_handler, callback_loop=callback_loop)
        self.device = device if device is not None else Metal.MTLCreateSystemDefaultDevice()
        if self.device is None:
            raise RuntimeError("No Metal device is available")
        native = objc.lookUpClass("SyphonMetalClient")
        self._finish_initialization(
            native.alloc().initWithServerDescription_device_options_newFrameHandler_(
                description.raw, self.device, None, self._native_handler
            )
        )


class SyphonOpenGLClient(BaseSyphonClient):
    """Receive OpenGL images. The caller must ensure exclusive access to the CGL context."""

    def __init__(
        self,
        description: SyphonServerDescription,
        cgl_context_obj: Optional[Any] = None,
        *,
        new_frame_handler: Optional[Callable[[BaseSyphonClient], None]] = None,
        callback_loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        super().__init__(description, new_frame_handler=new_frame_handler, callback_loop=callback_loop)
        opengl._require_pyopengl()
        self.cgl_context_obj = opengl.get_current_cgl_context_obj() if cgl_context_obj is None else cgl_context_obj
        native = objc.lookUpClass("SyphonOpenGLClient")
        self._finish_initialization(
            native.alloc().initWithServerDescription_context_options_newFrameHandler_(
                description.raw, _native.cgl_context(self.cgl_context_obj), None, self._native_handler
            )
        )
