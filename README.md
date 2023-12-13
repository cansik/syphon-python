# Syphon for Python
Python wrapper for the GPU texture sharing framework Syphon. This library has been created to support the Metal backend instead of OpenGL. Currently, only Metal and only the Server parts are implemented. The idea is to implement OpenGL and Metal, as well as Client and Server.

## Installation

```bash
# clone the repository and submodules
git clone --recurse-submodules https://github.com/cansik/syphon-python.git

# install dependencies
pip install -r requirements.txt
```

## Build

Build the Syphon-Framework on your Machine:

```bash
python setup.py build
```

## Distribute

Create a wheel package:

```bash
python setup.py bdist_wheel
```