"""Validate built artifacts with pytest --dist-dir dist after uv build."""

import email.parser
import subprocess
import tarfile
import zipfile

from packaging.requirements import Requirement
from packaging.utils import parse_wheel_filename


def test_source_archive_is_self_contained(dist_dir):
    archives = list(dist_dir.glob("syphon_python-*.tar.gz"))
    assert len(archives) == 1, "Expected one source archive; clean dist/ before building a new version"
    with tarfile.open(archives[0]) as archive:
        names = {name.split("/", 1)[1] for name in archive.getnames() if "/" in name}
        required = {
            "pyproject.toml",
            "conftest.py",
            "hatch_build.py",
            "README.md",
            "LICENSE",
            "syphon/__init__.py",
            "vendor/Syphon/License.txt",
            "vendor/Syphon/Syphon.xcodeproj/project.pbxproj",
            "vendor/Syphon/SyphonMetalShaders.metal",
            "vendor/Syphon/SyphonMetalServer.m",
        }
        assert required <= names, required - names
        assert not any(
            ".git" in name.split("/") or "build" in name.split("/") or ".framework/" in name for name in names
        )
        assert "scripts/benchmark.py" not in names
        assert "tests/test_benchmark.py" not in names
        assert not any(name.startswith("benchmark-results/") for name in names)


def test_wheel_metadata_and_bundled_framework(dist_dir, tmp_path):
    wheels = list(dist_dir.glob("syphon_python-*.whl"))
    assert len(wheels) == 1, "Expected one universal wheel; clean dist/ before building a new version"
    name, version, _, tags = parse_wheel_filename(wheels[0].name)
    assert name == "syphon-python"
    assert {str(tag) for tag in tags} == {"py3-none-macosx_12_0_universal2"}
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
        assert not any(name.startswith(("scripts/", "tests/", "benchmark-results/")) for name in names)
        wheel_metadata = email.parser.BytesParser().parsebytes(
            wheel.read(next(n for n in names if n.endswith("/WHEEL")))
        )
        assert wheel_metadata["Root-Is-Purelib"] == "false"
        assert wheel_metadata.get_all("Tag") == ["py3-none-macosx_12_0_universal2"]
        metadata = email.parser.BytesParser().parsebytes(wheel.read(next(n for n in names if n.endswith("/METADATA"))))
        assert metadata["Version"] == str(version)
        assert metadata["Requires-Python"] == ">=3.10"
        requirements = [Requirement(value) for value in metadata.get_all("Requires-Dist")]
        pyopengl = next(r for r in requirements if r.name.lower() == "pyopengl")
        assert not pyopengl.marker.evaluate({"extra": ""})
        assert pyopengl.marker.evaluate({"extra": "opengl"})
        prefix = "syphon/libs/Syphon.framework/"
        for resource in ("Syphon", "Resources/Info.plist", "Resources/default.metallib", "Resources/License.txt"):
            assert wheel.read(prefix + resource), resource
        binary = tmp_path / "Syphon"
        binary.write_bytes(wheel.read(prefix + "Syphon"))
        assert set(subprocess.check_output(["lipo", "-archs", str(binary)], text=True).split()) == {"arm64", "x86_64"}
