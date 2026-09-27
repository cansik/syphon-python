"""Regression checks for native wheel compatibility and build diagnostics."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("hatch_build", Path(__file__).resolve().parents[1] / "hatch_build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


@pytest.fixture
def framework(tmp_path):
    bundle = tmp_path / "Syphon.framework"
    (bundle / "Resources").mkdir(parents=True)
    (bundle / "Syphon").touch()
    (bundle / "Resources" / "Info.plist").touch()
    return bundle


def mock_binary_tools(
    monkeypatch, architectures="arm64 x86_64", minimum="12.0", dependency="@rpath/Syphon.framework/Syphon"
):
    def output(command, **kwargs):
        if command[0] == "lipo":
            return architectures
        if "-l" in command:
            return (
                f"Load command 0\n      cmd LC_BUILD_VERSION\n    minos {minimum}\n      sdk 27.0\n"
                "    tool LD\n version 27037.1\n"
                "Load command 1\n      cmd LC_SOURCE_VERSION\n  version 27037.1\n"
            )
        return f"Syphon:\n\t{dependency} (compatibility version 1.0.0, current version 1.0.0)\n"

    monkeypatch.setattr(build.subprocess, "check_output", output)


def test_universal_framework(framework, monkeypatch):
    mock_binary_tools(monkeypatch)
    build.validate_framework(framework)


@pytest.mark.parametrize(
    "options, message",
    [
        ({"architectures": "arm64"}, "Expected universal2"),
        ({"minimum": "14.0"}, "deployment target"),
        ({"dependency": "/Users/builder/Syphon.framework/Syphon"}, "non-portable"),
    ],
)
def test_reject_incompatible_framework(framework, monkeypatch, options, message):
    mock_binary_tools(monkeypatch, **options)
    with pytest.raises(RuntimeError, match=message):
        build.validate_framework(framework)


def test_missing_framework(tmp_path):
    with pytest.raises(RuntimeError, match="did not produce"):
        build.validate_framework(tmp_path)


def test_missing_submodule(tmp_path, monkeypatch):
    monkeypatch.setattr(build.sys, "platform", "darwin")
    with pytest.raises(RuntimeError, match="git submodule update"):
        build.build_framework(tmp_path)


def test_unsupported_platform(tmp_path, monkeypatch):
    monkeypatch.setattr(build.sys, "platform", "linux")
    with pytest.raises(RuntimeError, match="requires macOS"):
        build.build_framework(tmp_path)


def test_missing_metal_toolchain(tmp_path, monkeypatch):
    monkeypatch.setattr(build.sys, "platform", "darwin")
    monkeypatch.setattr(build, "xcode_environment", lambda: {"DEVELOPER_DIR": "/custom/Xcode"})
    project = tmp_path / "vendor" / "Syphon" / "Syphon.xcodeproj"
    project.mkdir(parents=True)
    (project / "project.pbxproj").touch()

    def run(command, **kwargs):
        if command[0] == "xcrun":
            raise build.subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(build.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="downloadComponent MetalToolchain"):
        build.build_framework(tmp_path)


def test_explicit_xcode_is_respected(monkeypatch):
    monkeypatch.setenv("DEVELOPER_DIR", "/custom/Xcode.app/Contents/Developer")
    monkeypatch.setattr(
        build.subprocess, "check_output", lambda *a, **kw: pytest.fail("Must respect explicit selection")
    )
    assert build.xcode_environment()["DEVELOPER_DIR"] == "/custom/Xcode.app/Contents/Developer"


@pytest.mark.parametrize("selected_xcode", [True, False])
def test_xcode_selection(tmp_path, monkeypatch, selected_xcode):
    monkeypatch.delenv("DEVELOPER_DIR", raising=False)
    selected = tmp_path / "selected"
    fallback = tmp_path / "Xcode.app/Contents/Developer"
    (fallback / "usr/bin").mkdir(parents=True)
    (fallback / "usr/bin/xcodebuild").touch()
    if selected_xcode:
        (selected / "usr/bin").mkdir(parents=True)
        (selected / "usr/bin/xcodebuild").touch()
    monkeypatch.setattr(build, "DEFAULT_XCODE", fallback)
    monkeypatch.setattr(build.subprocess, "check_output", lambda *a, **kw: str(selected))
    expected = selected if selected_xcode else fallback
    assert build.xcode_environment()["DEVELOPER_DIR"] == str(expected)
    assert "DEVELOPER_DIR" not in build.os.environ


def test_xcode_not_installed(tmp_path, monkeypatch):
    monkeypatch.delenv("DEVELOPER_DIR", raising=False)
    monkeypatch.setattr(build, "DEFAULT_XCODE", tmp_path / "missing")
    monkeypatch.setattr(build.subprocess, "check_output", lambda *a, **kw: str(tmp_path / "CommandLineTools"))
    with pytest.raises(RuntimeError, match="Install Xcode"):
        build.xcode_environment()
