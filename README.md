# Syphon for Python

[![Documentation](https://img.shields.io/badge/read-documentation-blue)](https://cansik.github.io/syphon-python/)
[![Build](https://github.com/cansik/syphon-python/actions/workflows/build.yml/badge.svg)](https://github.com/cansik/syphon-python/actions/workflows/build.yml)
[![PyPI](https://img.shields.io/pypi/v/syphon-python)](https://pypi.org/project/syphon-python/)

Python wrapper for the Syphon GPU texture sharing framework. This library was created to support both the Metal backend
and the deprecated OpenGL backend. It requires **macOS 12 or above** and **Python 3.10 or above**.

The implementation is based on [PyObjC](https://github.com/ronaldoussoren/pyobjc) to wrap the
[Syphon framework](https://github.com/Syphon/Syphon-Framework) directly from Python. This approach eliminates
native wrapper and allows Python developers to extend the library as needed.

## State of Development

- [x] Syphon Server Discovery
- [x] Metal Server
- [x] Metal Client
- [x] OpenGL Server
- [x] OpenGL Client
- [ ] Syphon Client On Frame Callback

## Usage
To install `syphon-python` it is recommended to use a prebuilt binary from PyPi:

```bash
pip install syphon-python
```

The default installation supports Metal without PyOpenGL. For OpenGL clients and servers, install the extra:

```bash
pip install 'syphon-python[opengl]'
```

Starting with 0.2.0, OpenGL users must explicitly request this extra. Existing Python class names and import paths
are unchanged. The native Syphon framework retains support for both rendering backends.

To run all the examples, please also install [Numpy](https://numpy.org/) and [OpenCV](https://opencv.org/):

```bash
pip install numpy opencv-python
```

The following code snippet is a basic example showing how to share `numpy` images as `MTLTexture` with a `SyphonMetalServer`. There are more examples in [examples](/examples).

```python
import time

import numpy as np

import syphon
from syphon.utils.numpy import copy_image_to_mtl_texture
from syphon.utils.raw import create_mtl_texture

# create server and texture
server = syphon.SyphonMetalServer("Demo")
texture = create_mtl_texture(server.device, 512, 512)

# create texture data
texture_data = np.zeros((512, 512, 4), dtype=np.uint8)
texture_data[:, :, 0] = 255  # fill red
texture_data[:, :, 3] = 255  # fill alpha

while True:
    # copy texture data to texture and publish frame
    copy_image_to_mtl_texture(texture_data, texture)
    server.publish_frame_texture(texture)
    time.sleep(1)

server.stop()
```

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

# check Python code without changing it
uv run ruff check .
uv run ruff format --check .

# apply formatting locally
uv run ruff format .
```

### Generate Documentation

```bash
# generate HTML into docs/
uv run --group docs --extra numpy pdoc syphon -o docs

# launch the local documentation server
uv run --group docs --extra numpy pdoc syphon
```

## About

MIT License - Copyright (c) 2024 Florian Bruggisser
