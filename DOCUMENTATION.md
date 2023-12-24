# Documentation
The syphon-python library is a wrapper for the [Syphon framework](https://github.com/Syphon/Syphon-Framework) for the Python language. It exposes the Objective-C API to the Python world and adds helper methods to easily interoperate with Syphon. Syphon is an open source Mac OS X technology that allows applications to share video and still images with each other in real time.

## Why a new library?
There are already wrappers like [syphonpy](https://github.com/njazz/syphonpy) that do the same thing as syphon-python. There are two main reasons why syphon-python was implemented:

### Modern Graphics Pipeline
Most existing Python wrappers for Syphon only support the OpenGL framework. Even though OpenGL is still available in modern MacOS versions, as of MacOS Mojave 10.14 the framework is marked as deprecated and should be avoided. And while many applications are switching to the Metal graphics backend, Syphon needs to do the same.

The Syphon framework already supports the Metal graphics backend, but the wrappers usually do not. Syphon Python adds support for Metal and retains OpenGL.

### Objective-C to Python
To add support for the new Metal graphics backend, the existing wrappers could be extended. However, many of them use an intermediate wrapper in C to expose the Objective-C API to Python. For Python developers it can be difficult to extend existing C code, so syphon-python uses [PyObjC](https://pyobjc.readthedocs.io/en/latest/), a Python to Objective-C bridge.

## Syphon Server
To share graphic textures with other applications, a syphon server has to be created. All server implementations are based on the `syphon.server.BaseSyphonServer` and share the same interface, except the constructor.

### Metal

### OpenGL

## Shared Directory

## Syphon Client

### Metal

### OpenGL

## Utilities

### Raw

### Numpy

## Python Binding

