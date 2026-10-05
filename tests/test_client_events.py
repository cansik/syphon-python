"""Threading, lifecycle and asyncio behavior without a native peer."""

import asyncio
import gc
import threading
import weakref
from unittest.mock import Mock

import pytest

from syphon.client import BaseSyphonClient, SyphonMetalClient, SyphonOpenGLClient
from syphon.server_directory import SyphonServerDescription


def make_client(handler=None, loop=None):
    client = BaseSyphonClient(None, new_frame_handler=handler, callback_loop=loop)
    native = Mock()
    native.isValid.return_value = True
    native.hasNewFrame.return_value = False
    client._finish_initialization(native)
    return client


def test_callback_receives_wrapper_and_ignores_initialization_and_stop():
    handler = Mock()
    client = BaseSyphonClient(None, new_frame_handler=handler)
    client._native_handler(None)
    handler.assert_not_called()
    client._finish_initialization(Mock())
    client._native_handler(client.context)
    handler.assert_called_once_with(client)
    client.stop()
    client._native_handler(None)
    assert handler.call_count == 1
    client.stop()
    client.context.stop.assert_called_once()


def test_native_callback_cannot_stop_any_client(caplog):
    peer = make_client()
    client = make_client(lambda _: peer.stop())
    client._native_handler(None)
    assert "Cannot stop a client from a native frame callback" in caplog.text
    peer.context.stop.assert_not_called()
    assert peer.is_valid
    peer.stop()


def test_callback_exceptions_never_escape_native_block(caplog):
    client = make_client(Mock(side_effect=KeyboardInterrupt))
    client._native_handler(None)
    assert "Syphon frame handler failed" in caplog.text


def test_native_block_does_not_retain_wrapper():
    client = make_client()
    callback = client._native_handler
    reference = weakref.ref(client)
    del client
    gc.collect()
    assert reference() is None
    callback(None)


def test_reject_coroutine_handler_and_close_accidental_coroutine(caplog):
    async def handler(client):
        pass

    with pytest.raises(TypeError, match="synchronous"):
        make_client(handler)
    client = make_client(lambda c: handler(c))
    client._native_handler(None)
    assert "must be synchronous" in caplog.text


def test_loop_dispatch_coalescing_exception_reporting_and_stop():
    async def scenario():
        loop = asyncio.get_running_loop()
        errors = []
        loop.set_exception_handler(lambda _, context: errors.append(context))
        threads = []
        client = make_client(lambda _: threads.append(threading.get_ident()), loop)
        thread = threading.Thread(target=lambda: [client._native_handler(None) for _ in range(10)])
        thread.start()
        thread.join()
        assert threads == []
        await asyncio.sleep(0)
        assert threads == [threading.get_ident()]
        client._handler = Mock(side_effect=ValueError("handler failed"))
        client._native_handler(None)
        await asyncio.sleep(0)
        assert isinstance(errors[0]["exception"], ValueError)
        client._handler = Mock()
        handler = client._handler
        client._native_handler(None)
        client.stop()
        await asyncio.sleep(0)
        handler.assert_not_called()

    asyncio.run(scenario())


def test_stop_from_loop_callback_is_safe():
    async def scenario():
        client = make_client(lambda c: c.stop(), asyncio.get_running_loop())
        client._native_handler(None)
        await asyncio.sleep(0)
        client.context.stop.assert_called_once()

    asyncio.run(scenario())


def test_closed_callback_loop(caplog):
    loop = asyncio.new_event_loop()
    client = make_client(Mock(), loop)
    loop.close()
    client._native_handler(None)
    assert "callback_loop is closed" in caplog.text
    with pytest.raises(ValueError, match="closed"):
        make_client(loop=loop)


def test_stop_does_not_hold_lock_while_native_waits_for_callback():
    client = make_client()

    def stop():
        thread = threading.Thread(target=lambda: client._native_handler(None))
        thread.start()
        thread.join(1)
        assert not thread.is_alive()

    client.context.stop.side_effect = stop
    client.stop()


def test_context_manager_stops_after_exception():
    client = make_client()
    with pytest.raises(ValueError):
        with client as entered:
            assert entered is client
            raise ValueError()
    assert not client.is_valid
    assert not client.has_new_frame
    assert client.new_frame_image is None
    with pytest.raises(RuntimeError):
        client.__enter__()


def test_async_waiters_notification_does_not_fetch_image():
    async def scenario():
        client = make_client()
        tasks = [asyncio.create_task(client.wait_for_frame(1)) for _ in range(3)]
        await asyncio.sleep(0)
        thread = threading.Thread(target=lambda: client._native_handler(None))
        thread.start()
        thread.join()
        assert await asyncio.gather(*tasks) == [None] * 3
        client.context.newFrameImage.assert_not_called()
        assert not client._waiters

    asyncio.run(scenario())


def test_async_unread_frame_timeout_cancellation_disconnect_and_stop():
    async def scenario():
        client = make_client()
        client.context.hasNewFrame.return_value = True
        assert await client.wait_for_frame(0) is None
        client.context.hasNewFrame.return_value = False
        with pytest.raises(asyncio.TimeoutError):
            await client.wait_for_frame(0.01)
        with pytest.raises(ValueError):
            await client.wait_for_frame(float("nan"))
        first = asyncio.create_task(client.wait_for_frame())
        second = asyncio.create_task(client.wait_for_frame())
        await asyncio.sleep(0)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert len(client._waiters) == 1
        client.context.isValid.return_value = False
        with pytest.raises(ConnectionError):
            await asyncio.wait_for(second, 1)
        client.context.isValid.return_value = True
        last = asyncio.create_task(client.wait_for_frame())
        await asyncio.sleep(0)
        client.stop()
        with pytest.raises(RuntimeError, match="stopped"):
            await last
        with pytest.raises(RuntimeError, match="stopped"):
            await client.wait_for_frame()
        assert not client._waiters

    asyncio.run(scenario())


def test_frame_arriving_during_registration_is_not_lost():
    async def scenario():
        client = make_client()

        def check():
            client._native_handler(None)
            return False

        client.context.hasNewFrame.side_effect = check
        assert await client.wait_for_frame(1) is None

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "client_type,selector",
    [
        (SyphonMetalClient, "initWithServerDescription_device_options_newFrameHandler_"),
        (SyphonOpenGLClient, "initWithServerDescription_context_options_newFrameHandler_"),
    ],
)
def test_constructor_forwards_retained_block_and_checks_nil(monkeypatch, client_type, selector):
    import syphon.client as module

    monkeypatch.setattr(module.opengl, "_require_pyopengl", Mock())
    native_type = Mock()
    monkeypatch.setattr(module.objc, "lookUpClass", lambda name: native_type)
    description = SyphonServerDescription.from_native({"custom": "kept"})
    factory = getattr(native_type.alloc.return_value, selector)
    client = client_type(description, object())
    args = factory.call_args.args
    assert args[0] is description.raw
    assert args[-1] is client._native_handler
    client.stop()
    factory.return_value = None
    with pytest.raises(RuntimeError, match="create the client"):
        client_type(description, object())


def test_stop_drains_peer_callbacks_before_native_shutdown():
    client = make_client()
    entered = threading.Event()
    release = threading.Event()
    marked_stopped = threading.Event()
    errors = []

    def callback(_):
        entered.set()
        if not release.wait(2):
            errors.append("Callback was not released")
        # A peer on the same native queue may inspect the stopping client.
        assert not client.is_valid

    peer = make_client(callback)
    worker = threading.Thread(target=lambda: peer._native_handler(None))
    worker.start()
    assert entered.wait(1)
    client._notify_waiters = lambda *args: marked_stopped.set()
    stopper = threading.Thread(target=client.stop)
    stopper.start()
    try:
        assert marked_stopped.wait(1)
        client.context.stop.assert_not_called()
    finally:
        release.set()
        worker.join(2)
        stopper.join(2)
    assert not worker.is_alive() and not stopper.is_alive()
    assert not errors
    client.context.stop.assert_called_once()


def test_burst_notifications_schedule_each_waiter_once():
    async def scenario():
        client = make_client()
        task = asyncio.create_task(client.wait_for_frame(1))
        await asyncio.sleep(0)
        for _ in range(100):
            client._native_handler(None)
        assert not client._waiters
        assert await task is None

    asyncio.run(scenario())
