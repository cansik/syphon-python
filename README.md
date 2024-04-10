# Syphon for Python

[![Documentation](https://img.shields.io/badge/read-documentation-blue)](https://cansik.github.io/syphon-python/)
[![Build](https://github.com/cansik/syphon-python/actions/workflows/build.yml/badge.svg)](https://github.com/cansik/syphon-python/actions/workflows/build.yml)
[![PyPI](https://img.shields.io/pypi/v/syphon-python)](https://pypi.org/project/syphon-python/)

Python wrapper for the Syphon GPU texture sharing framework. This library was created to support both the Metal backend
and the deprecated OpenGL backend. It requires **macOS 11 or above**.

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
To develop or manually install the library, use the following commands to set up the local repository.

### Installation

```bash
# clone the repository and it's submodules
git clone --recurse-submodules https://github.com/cansik/syphon-python.git

# install dependencies
pip install -r dev-requirements.txt
pip install -r requirements.txt

# for some examples the following dependencies are needed
pip install numpy
pip install opencv-python
```

### Build

Build the Syphon framework on your machine:

```bash
python setup.py build
```

### Distribute

Create a wheel package (also runs `build` automatically)

```bash
python setup.py bdist_wheel
```

### Generate Documentation

```bash
# create documentation into "./docs
python setup.py doc

# launch pdoc webserver
python setup.py doc --launch
```

## About

MIT License - Copyright (c) 2023 Florian Bruggisser
