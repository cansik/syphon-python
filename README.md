# Syphon for Python

[![Documentation](https://img.shields.io/badge/read-documentation-blue)](https://cansik.github.io/syphon-python/)
[![Build](https://github.com/cansik/syphon-python/actions/workflows/build.yml/badge.svg)](https://github.com/cansik/syphon-python/actions/workflows/build.yml)
[![PyPI](https://img.shields.io/pypi/v/syphon-python)](https://pypi.org/project/syphon-python/)

⚠️ This library is still *under development*.

Python wrapper for the GPU texture sharing framework Syphon. This library has been created to support the Metal backend
as well as the deprecated OpenGL backend.

The implementation is based on [PyObjC](https://github.com/ronaldoussoren/pyobjc) to wrap
the [Syphon-Framework](https://github.com/Syphon/Syphon-Framework) directly from within Python. This approach removes
the need of a native wrapper and allows Python developers to extend the library if needed.

## State of Development

- [x] Syphon Server Discovery
- [x] Metal Server
- [x] Metal Client
- [x] OpenGL Server
- [x] OpenGL Client
- [ ] Syphon Client On Frame Callback

## Installation

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

## Generate Documentation

```bash
# create documentation into "./docs
python setup.py doc

# launch pdoc webserver
python setup.py doc --launch
```

## About

MIT License - Copyright (c) 2023 Florian Bruggisser