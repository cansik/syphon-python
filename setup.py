import os
import shutil
import subprocess
from pathlib import Path
from typing import Union, Optional, List

from setuptools import Extension
from setuptools import find_packages, setup
from setuptools.command.build_ext import build_ext

NAME = "syphon-python"
PACKAGE_NAME = "syphon"
PACKAGE_VERSION = "0.0.1-alpha"

LIBS_PATH = Path(PACKAGE_NAME, "libs")

required_packages = find_packages(exclude=["examples"])

with open("requirements.txt") as f:
    required = [line for line in f.read().splitlines() if not line.startswith("-")]


class XcodeExtension(Extension):
    def __init__(self,
                 name: str,
                 project_path: Union[str, os.PathLike],
                 output_path: Union[str, os.PathLike],
                 target_name: Optional[str] = None,
                 configuration: str = "Release"):
        Extension.__init__(self, name, sources=[])

        self.name = name
        self.project_path = Path(project_path)
        self.project_root = self.project_path.parent
        self.output_path = Path(output_path)
        self.output_framework_path = (self.project_root
                                      .joinpath("build")
                                      .joinpath(configuration)
                                      .joinpath(f"{target_name}.framework"))
        self.target_name = self.name if target_name is None else target_name
        self.configuration = configuration


class XcodeBuild(build_ext):
    def run(self):
        try:
            _ = subprocess.check_output(["xcodebuild", "-version"])
        except OSError:
            extension_list = ", ".join(e.name for e in self.extensions)
            raise RuntimeError(f"xcodebuild must be installed to build the following extensions: {extension_list}")

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext: XcodeExtension):
        print(f"building extension {ext.target_name} in {ext.project_root}...")

        command = [
            "xcodebuild",
            "-project", f"{ext.project_path.name}",
            "-target", f"{ext.target_name}",
            "-configuration", f"{ext.configuration}"
        ]

        subprocess.check_call(command, cwd=ext.project_root)

        # copy resulting framework into output folder
        os.makedirs(ext.output_path, exist_ok=True)
        result_name = ext.output_path.joinpath(ext.output_framework_path.name)
        shutil.rmtree(result_name, ignore_errors=True)
        shutil.copytree(str(ext.output_framework_path), result_name)


def find_package_data(data_path: Union[str, os.PathLike], exclude_hidden: bool = True) -> List[str]:
    data_path = Path(data_path)
    files = list(data_path.rglob("*"))

    if exclude_hidden:
        files = [f for f in files if not f.name.startswith(".")]

    paths = [str(f.absolute()) for f in files if f.is_file()]
    return paths


package_data = {PACKAGE_NAME: find_package_data(LIBS_PATH)}

setup(
    name=NAME,
    version=PACKAGE_VERSION,
    packages=required_packages,
    package_data=package_data,
    include_package_data=True,
    url="https://github.com/cansik/syphon-python",
    license="MIT License",
    author="Florian Bruggisser",
    author_email="github@broox.ch",
    description="Python wrapper for the GPU texture sharing framework Syphon.",
    install_requires=required,
    ext_modules=[
        XcodeExtension("Syphon-Framework",
                       project_path="vendor/Syphon/Syphon.xcodeproj",
                       output_path=LIBS_PATH,
                       target_name="Syphon")
    ],
    cmdclass={"build_ext": XcodeBuild},
    zip_safe=False,
)
