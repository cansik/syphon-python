"""Build the bundled Syphon framework without introducing a Python ABI dependency."""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

DEPLOYMENT_TARGET = "12.0"
WHEEL_TAG = "py3-none-macosx_12_0_universal2"
ARCHITECTURES = {"arm64", "x86_64"}
DEFAULT_XCODE = Path("/Applications/Xcode.app/Contents/Developer")


def xcode_environment() -> dict[str, str]:
    """Use the user's selection, falling back to the standard Xcode installation."""
    environment = os.environ.copy()
    if "DEVELOPER_DIR" in environment:
        return environment
    try:
        selected = subprocess.check_output(["xcode-select", "-p"], text=True, stderr=subprocess.PIPE).strip()
    except (OSError, subprocess.CalledProcessError):
        selected = ""
    if selected and (Path(selected) / "usr/bin/xcodebuild").is_file():
        environment["DEVELOPER_DIR"] = selected
    elif (DEFAULT_XCODE / "usr/bin/xcodebuild").is_file():
        environment["DEVELOPER_DIR"] = str(DEFAULT_XCODE)
    else:
        raise RuntimeError(
            "Building Syphon requires full Xcode. Install Xcode in /Applications, or set "
            "DEVELOPER_DIR to the Contents/Developer directory of your Xcode installation."
        )
    return environment


def validate_framework(framework: Path, environment: dict[str, str] | None = None) -> None:
    """Reject a missing, incomplete, or incorrectly targeted framework."""
    binary = framework / "Syphon"
    if not binary.is_file():
        raise RuntimeError(f"Xcode did not produce the framework binary: {binary}")
    architectures = set(subprocess.check_output(["lipo", "-archs", str(binary)], text=True, env=environment).split())
    if architectures != ARCHITECTURES:
        raise RuntimeError(f"Expected universal2 framework, found architectures: {sorted(architectures)}")
    for architecture in sorted(ARCHITECTURES):
        load_commands = subprocess.check_output(
            ["otool", "-arch", architecture, "-l", str(binary)], text=True, env=environment
        )
        versions = []
        for command in re.split(r"Load command \d+", load_commands):
            if re.search(r"\bcmd LC_(?:BUILD_VERSION|VERSION_MIN_MACOSX)\b", command):
                field = "minos" if "LC_BUILD_VERSION" in command else "version"
                versions.extend(re.findall(rf"^\s*{field}\s+(\d+\.\d+(?:\.\d+)?)\s*$", command, re.MULTILINE))
        if not versions or any(tuple(map(int, value.split(".")[:2])) > (12, 0) for value in versions):
            raise RuntimeError(f"Framework deployment target exceeds macOS {DEPLOYMENT_TARGET}: {versions}")
        dependencies = subprocess.check_output(
            ["otool", "-arch", architecture, "-L", str(binary)], text=True, env=environment
        )
        for line in dependencies.splitlines()[1:]:
            dependency = line.strip().split(" (", 1)[0]
            if not dependency.startswith(("@rpath/", "@loader_path/", "/System/Library/", "/usr/lib/")):
                raise RuntimeError(f"Framework contains a non-portable library path: {dependency}")
    if not (framework / "Resources" / "Info.plist").is_file():
        raise RuntimeError("Framework is missing Resources/Info.plist")


def build_framework(root: Path) -> Path:
    if sys.platform != "darwin":
        raise RuntimeError("syphon-python requires macOS 12 or later; its native framework cannot be built here.")
    project = root / "vendor" / "Syphon" / "Syphon.xcodeproj"
    if not (project / "project.pbxproj").is_file():
        raise RuntimeError(
            "Syphon source is missing. Run git submodule update --init --recursive, or use the PyPI sdist."
        )
    environment = xcode_environment()
    try:
        subprocess.run(["xcodebuild", "-version"], check=True, capture_output=True, text=True, env=environment)
        subprocess.run(["xcrun", "metal", "--version"], check=True, capture_output=True, text=True, env=environment)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            f"Cannot use Xcode and its Metal toolchain with DEVELOPER_DIR={environment.get('DEVELOPER_DIR')!r}. "
            "Check this Xcode installation and complete its first-launch setup. If Metal is missing, "
            "install Metal Toolchain in Xcode > Settings > Components, or run "
            "xcodebuild -downloadComponent MetalToolchain with that developer directory selected."
        ) from exc

    output = root / "build" / "syphon-framework"
    subprocess.run(
        [
            "xcodebuild",
            "-project",
            str(project),
            "-target",
            "Syphon",
            "-configuration",
            "Release",
            "-sdk",
            "macosx",
            "ARCHS=arm64 x86_64",
            "ONLY_ACTIVE_ARCH=NO",
            f"MACOSX_DEPLOYMENT_TARGET={DEPLOYMENT_TARGET}",
            "CODE_SIGNING_ALLOWED=NO",
            f"SYMROOT={root / 'build' / 'syphon-products'}",
            f"CONFIGURATION_BUILD_DIR={output}",
            f"OBJROOT={root / 'build' / 'syphon-objects'}",
        ],
        cwd=root,
        check=True,
        env=environment,
    )
    framework = output / "Syphon.framework"
    validate_framework(framework, environment)
    return framework


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        root = Path(self.root)
        framework = build_framework(root)
        # Wheels do not preserve framework symlinks. Materialize their targets so
        # the installed bundle retains both its public and versioned paths.
        staged = root / "build" / "syphon-staging" / "Syphon.framework"
        if staged.exists():
            shutil.rmtree(staged)
        shutil.copytree(framework, staged, symlinks=False)
        shutil.copy2(root / "vendor" / "Syphon" / "License.txt", staged / "Resources" / "License.txt")
        build_data["pure_python"] = False
        build_data["tag"] = WHEEL_TAG
        build_data["force_include"][str(staged)] = "syphon/libs/Syphon.framework"
        if version == "editable":
            # Editable imports resolve into the checkout, not site-packages.
            editable_framework = root / "syphon" / "libs" / "Syphon.framework"
            if editable_framework.exists():
                shutil.rmtree(editable_framework)
            shutil.copytree(staged, editable_framework)
