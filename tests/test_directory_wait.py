"""Discovery helpers are opt-in; existing property reads continue processing events."""

from unittest.mock import Mock

import pytest

from syphon.server_directory import SyphonServerDirectory


@pytest.fixture
def directory():
    directory = SyphonServerDirectory.__new__(SyphonServerDirectory)
    directory._syphonServerDirectoryObjC = Mock()
    directory.update_run_loop = Mock()
    return directory


def snapshots(directory, values):
    directory._syphonServerDirectoryObjC.sharedDirectory.return_value.servers.side_effect = values


def test_snapshot_does_not_process_events(directory):
    snapshots(directory, [[{"SyphonServerDescriptionNameKey": "Camera"}]])
    assert directory.server_snapshot[0].name == "Camera"
    directory.update_run_loop.assert_not_called()


def test_existing_property_still_processes_events(directory):
    snapshots(directory, [[{"SyphonServerDescriptionNameKey": "Camera"}]])
    assert directory.servers[0].name == "Camera"
    directory.update_run_loop.assert_called_once_with()


def test_wait_returns_existing_server_without_pumping(directory):
    snapshots(directory, [[{"SyphonServerDescriptionNameKey": "Camera"}]])
    assert directory.wait_for_server(timeout=0).name == "Camera"
    directory.update_run_loop.assert_not_called()


def test_wait_pumps_discovery_and_returns_matching_server(directory, monkeypatch):
    import syphon.server_directory as module

    monkeypatch.setattr(module.time, "monotonic", Mock(side_effect=[0, 0.1]))
    snapshots(directory, [[], [{"SyphonServerDescriptionNameKey": "Camera"}]])
    assert directory.wait_for_server(name="Camera").name == "Camera"
    directory.update_run_loop.assert_called_once_with(timeout=0.05)


def test_wait_caps_pump_at_deadline_and_returns_none(directory, monkeypatch):
    import syphon.server_directory as module

    monkeypatch.setattr(module.time, "monotonic", Mock(side_effect=[0, 0.99, 1.01]))
    snapshots(directory, [[], []])
    assert directory.wait_for_server(timeout=1) is None
    assert directory.update_run_loop.call_args.kwargs["timeout"] == pytest.approx(0.01)


@pytest.mark.parametrize("timeout", [-1, float("nan"), float("inf")])
def test_invalid_waits_are_rejected(directory, timeout):
    with pytest.raises(ValueError, match="finite nonnegative"):
        directory.wait_for_server(timeout)
    with pytest.raises(ValueError, match="finite nonnegative"):
        SyphonServerDirectory.update_run_loop(directory, timeout)


def test_run_loop_timeout_is_explicit_and_default_is_preserved(monkeypatch):
    import syphon.server_directory as module

    run_loop = Mock()
    monkeypatch.setattr(module, "NSRunLoop", run_loop)
    date = Mock()
    monkeypatch.setattr(module, "NSDate", date)
    directory = SyphonServerDirectory()
    directory.update_run_loop()
    directory.update_run_loop(timeout=0)
    assert [call.args[0] for call in date.dateWithTimeIntervalSinceNow_.call_args_list] == [1.0, 0]


@pytest.mark.parametrize("name,app_name", [("Camera", None), (None, "Studio"), ("Missing", "Studio")])
def test_wait_filters_match_either_field(directory, name, app_name):
    snapshots(
        directory,
        [
            [
                {"SyphonServerDescriptionNameKey": "Other", "SyphonServerDescriptionAppNameKey": "Elsewhere"},
                {"SyphonServerDescriptionNameKey": "Camera", "SyphonServerDescriptionAppNameKey": "Studio"},
            ]
        ],
    )
    assert directory.wait_for_server(timeout=0, name=name, app_name=app_name).name == "Camera"
