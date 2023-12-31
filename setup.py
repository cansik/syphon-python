import distutils
import os
import shutil
import subprocess
from distutils.command.install import install
from pathlib import Path
from typing import Union, Optional, List

from setuptools import Extension
from setuptools import find_packages, setup
from setuptools.command.build_ext import build_ext

NAME = "syphon-python"
PACKAGE_NAME = "syphon"
PACKAGE_VERSION = "0.1.1"
PACKAGE_URL = "https://github.com/cansik/syphon-python"
PACKAGE_DOC_MODULES = ["syphon"]

LIBS_PATH = Path(PACKAGE_NAME, "libs")

required_packages = find_packages(exclude=["examples", "playground", "scripts"])

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

        if not ext.project_path.exists():
            raise FileNotFoundError(f"There is not project at '{ext.project_path}'. "
                                    f"Did you initialize the git submodules?")

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


class GenerateDoc(distutils.cmd.Command):
    description = "generate pdoc documentation"

    user_options = install.user_options + [
        ("output=", None, "Output path for the documentation."),
        ("launch", None, "Launch webserver to display documentation.")
    ]

    def initialize_options(self):
        install.initialize_options(self)
        self.output: str = "docs"
        self.launch: bool = False

    def finalize_options(self):
        pass

    def run(self) -> None:
        from scripts.generate_doc import generate_doc
        generate_doc(PACKAGE_NAME, PACKAGE_VERSION, PACKAGE_URL, required_packages,
                     Path(self.output), PACKAGE_DOC_MODULES, launch=bool(self.launch))


def find_package_data(data_path: Union[str, os.PathLike], exclude_hidden: bool = True) -> List[str]:
    data_path = Path(data_path)
    files = list(data_path.rglob("*"))

    if exclude_hidden:
        files = [f for f in files if not f.name.startswith(".")]

    paths = [str(f.absolute()) for f in files if f.is_file()]
    return paths


package_data = {PACKAGE_NAME: find_package_data(LIBS_PATH)}

# read readme
current_dir = Path(__file__).parent
long_description = (current_dir / "README.md").read_text()

setup(
    name=NAME,
    version=PACKAGE_VERSION,
    packages=required_packages,
    package_data=package_data,
    include_package_data=True,
    url=PACKAGE_URL,
    license="MIT License",
    author="Florian Bruggisser",
    author_email="github@broox.ch",
    description="Python wrapper for the GPU texture sharing framework Syphon.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=required,
    ext_modules=[
        XcodeExtension("Syphon-Framework",
                       project_path="vendor/Syphon/Syphon.xcodeproj",
                       output_path=LIBS_PATH,
                       target_name="Syphon")
    ],
    cmdclass={
        "build_ext": XcodeBuild,
        "doc": GenerateDoc,
    },
    zip_safe=False,
)
