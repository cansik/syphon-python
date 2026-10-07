#!/usr/bin/env bash
# Exercise installed artifacts outside the checkout, including a clean source build.
set -euo pipefail

: "${TEST_PYTHON:?Set TEST_PYTHON to the interpreter executable}"
: "${TEST_VARIANT:?Set TEST_VARIANT to standard or free-threaded}"
: "${TEST_PYTHON_VERSION:?Set TEST_PYTHON_VERSION to the expected Python version}"
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
test_dir="$(mktemp -d "${TMPDIR:-/tmp}/syphon-ci.XXXXXX")"
trap 'rm -rf "$test_dir"' EXIT

cd "$repo_dir"
uv export --python "$TEST_PYTHON" --locked --only-group test --format requirements-txt --output-file "$test_dir/requirements.txt" > /dev/null
wheel_files=("$repo_dir"/dist/*.whl)
source_files=("$repo_dir"/dist/*.tar.gz)
test "${#wheel_files[@]}" -eq 1 && test -f "${wheel_files[0]}"
test "${#source_files[@]}" -eq 1 && test -f "${source_files[0]}"
uv venv --python "$TEST_PYTHON" "$test_dir/wheel-env"
test_python="$test_dir/wheel-env/bin/python"
"$test_python" -c 'import platform, sys; print("Test interpreter:", sys.executable, sys.version, platform.machine())'
uv pip install --python "$test_python" --only-binary :all: -r "$test_dir/requirements.txt" "${wheel_files[0]}"

# Avoid importing syphon from the working tree, including in subprocess tests.
unset PYTHONPATH
cd "$test_dir"
"$test_python" -c 'import importlib.util, syphon; assert "site-packages" in syphon.__file__; assert importlib.util.find_spec("OpenGL") is None; assert importlib.util.find_spec("numpy") is None'
pytest_args=(--import-mode=importlib --python-variant "$TEST_VARIANT" --python-version "$TEST_PYTHON_VERSION" -ra)
"$test_python" -m pytest "$repo_dir/tests" "${pytest_args[@]}" -m 'not metal and not opengl'
uv pip install --python "$test_python" --only-binary :all: "${wheel_files[0]}[numpy,opengl]"
if [[ "${TEST_NATIVE:-true}" == true ]]; then
    "$test_python" -m pytest "$repo_dir/tests" "${pytest_args[@]}"
else
    "$test_python" -m pytest "$repo_dir/tests" "${pytest_args[@]}" -m 'not metal and not opengl'
fi

if [[ "${TEST_SOURCE:-false}" == true ]]; then
    uv venv --python "$TEST_PYTHON" "$test_dir/source-env"
    source_python="$test_dir/source-env/bin/python"
    uv pip install --no-cache --python "$source_python" -r "$test_dir/requirements.txt" "${source_files[0]}[numpy,opengl]"
    "$source_python" -c 'import syphon; assert "site-packages" in syphon.__file__'
    "$source_python" -m pytest "$repo_dir/tests" "${pytest_args[@]}" -m 'not metal and not opengl'
fi
