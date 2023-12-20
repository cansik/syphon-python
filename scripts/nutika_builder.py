import argparse
import os
import shutil
import subprocess
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser("Nutika Builder")
    parser.add_argument("script_path", type=str, help="Path to the script to compile.")
    parser.add_argument("output_path", type=str, help="Path to output folder.")

    return parser.parse_args()


def main():
    args = parse_args()

    script_path = Path(args.script_path)
    output_path = Path(args.output_path)
    app_name = script_path.stem

    app_path = output_path.joinpath(f"{script_path.stem}.app")

    os.makedirs(output_path, exist_ok=True)

    # read signing identity from security
    result = subprocess.check_output([
        "security", "find-identity", "-v", "-p", "codesigning"
    ])
    sign_identity = result.splitlines()[0].decode().split(" ")[3]

    # run nuitka
    result = subprocess.run([
        "python", "-m", "nuitka",
        "--follow-imports",
        "--standalone",
        "--assume-yes-for-downloads",

        # output
        f"--output-filename={app_name}",
        f"--output-dir={output_path}",

        # plugins

        # macos specific
        "--macos-create-app-bundle",
        f"--macos-app-name={app_name}",
        f"--macos-signed-app-name=org.syphon.python.{app_name}",
        f"--macos-sign-identity={sign_identity}",

        # include extra packages
        "--include-package=socket",
        "--include-package=queue",

        # deploy
        "--deployment",

        # script
        f"{script_path}"
    ])

    if result.returncode > 0:
        print("Build was not successful.")
        exit(result)

    # add syphon framework
    app_syphon_path = app_path.joinpath("Contents", "MacOS", "syphon", "libs")
    lib_syphon_path = Path("syphon", "libs")
    os.makedirs(app_syphon_path, exist_ok=True)
    shutil.copytree(lib_syphon_path, app_syphon_path, dirs_exist_ok=True)


if __name__ == "__main__":
    main()
