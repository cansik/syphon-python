# Syphon for Python

[![Documentation](https://img.shields.io/badge/read-documentation-blue)](https://cansik.github.io/syphon-python/)
[![Build](https://github.com/cansik/syphon-python/actions/workflows/build.yml/badge.svg)](https://github.com/cansik/syphon-python/actions/workflows/build.yml)
[![PyPI](https://img.shields.io/pypi/v/syphon-python)](https://pypi.org/project/syphon-python/)

Python wrapper for the Syphon GPU texture sharing framework. This library was created to support both the Metal backend
and the deprecated OpenGL backend. It requires **macOS 12 or above** and supports **Python 3.10–3.14**,
including the free-threaded **3.13t and 3.14t** builds.

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
- [x] Async Frame Waiting
- [x] Context Managers
- [x] Private Servers and Server Renaming
- [x] Direct OpenGL Rendering

## Usage
To install `syphon-python` it is recommended to use a prebuilt binary from PyPI:

```bash
pip install syphon-python
```

Since version 0.2.0, PyOpenGL is optional. To use the OpenGL backend, install it with:

```bash
pip install 'syphon-python[opengl]'
```

To work with NumPy images, as shown in the following example, also install the NumPy dependency:

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

# create the server and stop it automatically when leaving the block
with syphon.SyphonMetalServer("Demo") as server, syphon.SyphonServerDirectory() as directory:
    directory.run_loop_interval = 0.001

    # create a texture on the server's Metal device
    texture = create_mtl_texture(server.device, 512, 512)

    # create an opaque red RGBA image
    texture_data = np.zeros((512, 512, 4), dtype=np.uint8)
    texture_data[:, :, 0] = 255  # fill red
    texture_data[:, :, 3] = 255  # fill alpha

    try:
        while True:
            # copy the current image onto the texture and publish it
            copy_image_to_mtl_texture(texture_data, texture)
            server.publish_frame_texture(texture)

            # process discovery requests without opening a window
            directory.update_run_loop()

            time.sleep(1 / 60)
    except KeyboardInterrupt:
        pass
```

For applications without a UI, `directory.update_run_loop()` processes Cocoa events on the main thread
so that other applications can discover the server. Calling it regularly keeps the server discoverable.

## Development

To develop or manually build the library, use [uv](https://docs.astral.sh/uv/) and Python 3.14 to set up
the local repository. Building the Syphon framework requires full Xcode with its Metal toolchain;
Command Line Tools alone are not sufficient. Installing a prebuilt wheel does not require Xcode.

### Installation

```bash
# clone the repository and its submodules
git clone --recurse-submodules https://github.com/cansik/syphon-python.git
cd syphon-python

# install the library and development dependencies
uv sync --locked
```

This builds the framework and installs the library in editable mode, so Python changes are immediately
available. For an existing checkout, run `git submodule update --init --recursive` first.

To install the additional dependencies used by the examples:

```bash
uv sync --locked --group examples

# run a Metal example
uv run --group examples python -m examples.MetalServerExampleMini

# run an OpenGL example with the optional dependency
uv run --group examples --extra opengl python -m examples.OpenGLServerExample
```

### Build

Create a source archive and a wheel package in `dist/`:

```bash
uv build
```

The wheel includes the Syphon framework for both Apple Silicon and Intel. The source archive includes
the framework sources, so it can also be built without cloning the repository:

```bash
python -m pip install ./dist/syphon_python-0.3.0.tar.gz
```

If you change the native framework sources during development, rebuild the editable installation with:

```bash
uv sync --locked --reinstall-package syphon-python
```

The build uses the selected Xcode installation or finds it at `/Applications/Xcode.app` automatically.
If the Metal toolchain is missing, install it in **Xcode > Settings > Components**. For Xcode installed
in a custom location, specify its path when building:

```bash
DEVELOPER_DIR=/path/to/Xcode.app/Contents/Developer uv build
```

### Tests

Run the tests locally with pytest:

```bash
uv run pytest

# also test the optional NumPy and OpenGL support
uv run --extra numpy --extra opengl pytest
```

After running `uv build`, use `uv run pytest --dist-dir dist` to check the generated packages as well.
Rendering tests require a Metal device or an OpenGL context; use `-m 'not metal and not opengl'` to skip them.

To test with a different Python version, for example a free-threaded build:

```bash
uv run --python 3.14t --extra numpy --extra opengl pytest
```

### Formatting

The project uses Ruff to check and format Python code:

```bash
# check the code and formatting
uv run ruff check .
uv run ruff format --check .

# apply formatting
uv run ruff format .
```

### Benchmarks

From a development checkout, save a run before changing the library and compare it with a later run:

```bash
uv run --extra numpy python -m scripts.benchmark --output benchmark-results/before.json
uv run --extra numpy python -m scripts.benchmark --compare benchmark-results/before.json --output benchmark-results/after.json
```

Results stay local. The benchmark tool is available in the repository, but is not included in release packages.
Use `--help` for backend and image-size options.

### Generate Documentation

```bash
# generate documentation into docs/
uv run --group docs --extra numpy python scripts/generate_doc.py

# launch the local documentation server
uv run --group docs --extra numpy python scripts/generate_doc.py --serve
```

For release and CI instructions, see the [maintainer guide](https://github.com/cansik/syphon-python/blob/main/.github/RELEASING.md).

## Citation

If you use syphon-python in your research, please cite it using
[CITATION.cff](https://github.com/cansik/syphon-python/blob/main/CITATION.cff).

## About

MIT License - Copyright (c) 2026 Florian Bruggisser
