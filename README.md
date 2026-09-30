# Syphon for Python

[![Documentation](https://img.shields.io/badge/read-documentation-blue)](https://cansik.github.io/syphon-python/)
[![Build](https://github.com/cansik/syphon-python/actions/workflows/build.yml/badge.svg)](https://github.com/cansik/syphon-python/actions/workflows/build.yml)
[![PyPI](https://img.shields.io/pypi/v/syphon-python)](https://pypi.org/project/syphon-python/)

Python wrapper for the Syphon GPU texture sharing framework. This library was created to support both the Metal backend
and the deprecated OpenGL backend. It requires **macOS 12 or above** and **Python 3.10 or above**.

Supported Python versions are **3.10–3.14**, including the **3.13t and 3.14t** free-threaded builds.
Prerelease Python versions are outside the support and CI test matrix.

The implementation is based on [PyObjC](https://github.com/ronaldoussoren/pyobjc) to wrap the
[Syphon framework](https://github.com/Syphon/Syphon-Framework) directly from Python. This approach eliminates
the native wrapper layer and allows Python developers to extend the library as needed.

## State of Development

- [x] Syphon Server Discovery
- [x] Metal Server
- [x] Metal Client
- [x] OpenGL Server
- [x] OpenGL Client
- [x] Syphon Client On Frame Callback
- [x] Async frame waiting and lifecycle context managers
- [x] Private servers and live output names
- [x] Direct OpenGL framebuffer rendering

## Usage
To install `syphon-python` it is recommended to use a prebuilt binary from PyPI:

```bash
pip install syphon-python
```

The default installation supports Metal without PyOpenGL. For OpenGL clients and servers, install the extra:

```bash
pip install 'syphon-python[opengl]'
```

Starting with 0.2.0, OpenGL users must explicitly request this extra. Existing Python class names and import paths
are unchanged. The native Syphon framework retains support for both rendering backends.

For NumPy texture helpers and the following example, install the NumPy extra:

```bash
pip install 'syphon-python[numpy]'
```

The following code snippet is a basic example showing how to share `numpy` images as `MTLTexture` with a `SyphonMetalServer`. There are more examples in [examples](https://github.com/cansik/syphon-python/tree/main/examples).

```python
import time

import numpy as np

import syphon
from syphon.utils.numpy import copy_image_to_mtl_texture
from syphon.utils.raw import create_mtl_texture

# Create the server; the context manager stops it when we exit.
with syphon.SyphonMetalServer("Demo") as server, syphon.SyphonServerDirectory() as directory:
    directory.run_loop_interval = 0.001

    # Create a texture on the server's Metal device.
    texture = create_mtl_texture(server.device, 512, 512)

    # Create an opaque red RGBA image.
    texture_data = np.zeros((512, 512, 4), dtype=np.uint8)
    texture_data[:, :, 0] = 255  # fill red
    texture_data[:, :, 3] = 255  # fill alpha

    try:
        while True:
            # Copy the image onto the texture and publish it.
            copy_image_to_mtl_texture(texture_data, texture)
            server.publish_frame_texture(texture)

            # Process discovery requests even though there is no window.
            directory.update_run_loop()
            time.sleep(1 / 60)
    except KeyboardInterrupt:
        pass
```

Headless servers must process Cocoa events to respond to discovery requests from clients started
later. Call `directory.update_run_loop()` regularly on the main thread; no window is required.
Sleeping alone does not process those events.

## Development

Development uses [uv](https://docs.astral.sh/uv/) and Python 3.14. Building from source requires
full Xcode, including its Metal toolchain; Command Line Tools alone are not sufficient.
Installing a prebuilt wheel does not require Xcode.

### Installation

```bash
# clone the repository and its submodules
git clone --recurse-submodules https://github.com/cansik/syphon-python.git
cd syphon-python

# install the project in editable mode and its development/test dependencies
uv sync --locked
```

For an existing checkout, run `git submodule update --init --recursive` before `uv sync`.
The editable installation compiles Syphon automatically. Python edits are immediately available;
after native source changes, run `uv sync --locked --reinstall-package syphon-python` to rebuild.

The build uses your selected Xcode installation automatically. If Command Line Tools are selected,
it finds Xcode at `/Applications/Xcode.app`; no environment export or system setting change is needed.
If Xcode reports a missing Metal toolchain, install **Metal Toolchain** in **Xcode > Settings > Components**
and retry. Complete any first-launch setup requested by Xcode.

For an Xcode installation in a custom location, you can override the selection for one command:

```bash
DEVELOPER_DIR=/path/to/Xcode.app/Contents/Developer uv build
```

To install example dependencies and run a Metal example:

```bash
uv sync --locked --group examples
uv run --group examples python -m examples.MetalServerExampleMini
```

For the OpenGL examples, also enable the OpenGL extra:

```bash
uv run --group examples --extra opengl python -m examples.OpenGLServerExample
```

### Build distributions

From the repository root:

```bash
uv build
```

This creates a source archive and builds a wheel from that archive in `dist/`:

- `syphon_python-0.2.0.tar.gz`
- `syphon_python-0.2.0-py3-none-macosx_12_0_universal2.whl`

The wheel contains the compiled Syphon framework for both Apple Silicon and Intel, targets macOS 12,
and can be installed across supported Python versions without rebuilding Syphon.
The source archive includes the vendored Syphon sources, so it can be built without Git or submodules.

To install the local source archive into an activated virtual environment:

```bash
python -m pip install ./dist/syphon_python-0.2.0.tar.gz
```

### Tests and formatting

```bash
uv run pytest

# validate packaged resources, metadata, and both native architectures
uv build
uv run pytest --dist-dir dist

# check Python code without changing it
uv run ruff check .
uv run ruff format --check .

# apply formatting locally
uv run ruff format .
```

Run optional NumPy and OpenGL tests with `uv run --extra numpy --extra opengl pytest`.
Metal and OpenGL integration tests run when their devices/contexts are available.
Use `-m 'not metal and not opengl'` to exclude native rendering tests.
Free-threaded test runs fail if a dependency enables the GIL. Distribution checks skip unless
`--dist-dir` is supplied, and optional-dependency tests skip when their extra is not installed.

To test a different interpreter, specify it explicitly, for example:

```bash
uv run --python 3.14t --extra numpy --extra opengl pytest
```

### Generate Documentation

```bash
# generate HTML into docs/
uv run --group docs --extra numpy python scripts/generate_doc.py

# launch the local documentation server
uv run --group docs --extra numpy python scripts/generate_doc.py --serve
```

CI checks builds, tests, formatting, and documentation on pushes and pull requests.
For publishing instructions, see the [maintainer guide](https://github.com/cansik/syphon-python/blob/main/.github/RELEASING.md).

## Citation

If you use syphon-python in research, please cite it using the metadata in
[CITATION.cff](https://github.com/cansik/syphon-python/blob/main/CITATION.cff).

## About

MIT License - Copyright (c) 2026 Florian Bruggisser
