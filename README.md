# Syphon for Python
[![Build](https://github.com/cansik/syphon-python/actions/workflows/build.yml/badge.svg)](https://github.com/cansik/syphon-python/actions/workflows/build.yml)

⚠️ This library is still *under development*.

Python wrapper for the GPU texture sharing framework Syphon. This library has been created to support the Metal backend instead of OpenGL. Currently, only Metal and only the Server parts are implemented. The idea is to implement OpenGL and Metal, as well as Client and Server.

The implementation is based on [PyObjC](https://github.com/ronaldoussoren/pyobjc) to wrap the [Syphon-Framework](https://github.com/Syphon/Syphon-Framework) directly from within Python. This approach removes the need of a native wrapper and allows Python developers to extend the library if needed.

## Installation

```bash
# clone the repository and it's submodules
git clone --recurse-submodules https://github.com/cansik/syphon-python.git

# install dependencies
pip install -r dev-requirements.txt
pip install -r requirements.txt
```

## Build

Build the Syphon-Framework on your machine:

```bash
python setup.py build
```

## Distribute

Create a wheel package (also runs `build` automatically)

```bash
python setup.py bdist_wheel
```

### About
Copyright (c) 2023 Florian Bruggisser