# Documentation
The syphon-python library is a wrapper for the [Syphon framework](https://github.com/Syphon/Syphon-Framework) for the Python language. It exposes the Objective-C API to the Python world and adds helper methods to easily interoperate with Syphon. Syphon is an open source Mac OS X technology that allows applications to share video and still images with each other in real time.

## Why a new library?
There are already wrappers like [syphonpy](https://github.com/njazz/syphonpy) that do the same thing as syphon-python. There are two main reasons why syphon-python was implemented:

### Modern Graphics Pipeline
Most existing Python wrappers for Syphon only support the OpenGL framework. Even though OpenGL is still available in modern MacOS versions, as of **MacOS Mojave 10.14**, the framework is marked as deprecated and should be avoided. And while many applications are switching to the Metal graphics backend, Syphon needs to do the same.

The Syphon framework already supports the Metal graphics backend, but the wrappers usually do not. Syphon-python adds support for Metal and retains OpenGL.

### Objective-C to Python
To add support for the new Metal graphics backend, the existing wrappers could be extended. However, many of them use an intermediate wrapper in C to expose the Objective-C API to Python. For Python developers it can be difficult to extend existing C code, so syphon-python uses [PyObjC](https://pyobjc.readthedocs.io/en/latest/), a Python to Objective-C bridge.

## Syphon Package
The main package of syphon-python is called `syphon` and contains all the necessary objects and classes of the library. To use syphon-python in a project, start with the following import statement.

```python
import syphon
```

For each Metal class there is also an OpenGL counterpart. It is worth noting that Syphon supports interopability between Metal and OpenGL. This means that it is possible to run a Metal-based Syphon server and receive it in an OpenGL client and vice versa.

## Syphon Server
To share graphic textures with other applications, a syphon server (sender) has to be created. All server implementations are based on the `syphon.server.BaseSyphonServer` and share the same interface, except the constructor. This creates either a Metal oder OpenGL based server, using the app name `Demo Server` and using the default device or context.

```python
# create a Metal based server
server = syphon.SyphonMetalServer("Demo Server")

# create an OpenGL based server
server = syphon.SyphonOpenGLServer("Demo Server")
```

To publish a texture, the method `syphon.server.BaseSyphonServer.publish_frame_texture()` can be used. We assume that the corresponding texture has already been created and is available in the `texture` variable. To see how to create and fill a MTLTexture or glTexture, please have a look at the [examples](https://github.com/cansik/syphon-python/tree/main/examples).

```python
texture = ... # MTLTexture or glTexture
server.publish_frame_texture(texture)
```

It is also possible to check if a server has connected clients with the `has_clients` property.

To clean up and release allocated resources, a server should be stopped with the `syphon.server.BaseSyphonServer.stop()` method.

```python
if not server.has_clients:
    server.stop()
```

### Metal Server
On initialisation, the `syphon.server.SyphonMetalServer` creates a new [system default Metal device](https://developer.apple.com/documentation/metal/1433401-mtlcreatesystemdefaultdevice) as well as a new [command queue](https://developer.apple.com/documentation/metal/mtlcommandqueue). It is possible to override which [MTLDevice](https://developer.apple.com/documentation/metal/mtldevice) the Syphon server is running on or which type of command queue is used. This can be done by using the additional parameters of the `syphon.server.SyphonMetalServer`.

```python
import Metal

# overwrite the mtl_device
mtl_device = Metal.MTLCreateSystemDefaultDevice()
server = syphon.SyphonMetalServer("Demo", device=mtl_device)

# or also create custom command queue
mtl_command_queue = mtl_device.newCommandQueue()
server = syphon.SyphonMetalServer("Demo", device=mtl_device, command_queue=mtl_command_queue)
```

### OpenGL Server
On initialisation, the `syphon.server.SyphonOpenGLServer` tries to find the current [cglContextObj](https://developer.apple.com/documentation/appkit/nsopenglcontext/1436158-cglcontextobj) using the current [NSOpenGLContext](https://developer.apple.com/documentation/appkit/nsopenglcontext). It is possible to override the automatic lookup by passing a valid `cglContextObj` as a parameter to the `syphon.server.SyphonOpenGLServer`.

```python
import AppKit

ns_ctx = AppKit.NSOpenGLContext.currentContext()
cgl_context = ns_ctx.CGLContextObj()

server = syphon.SyphonOpenGLServer("Demo", cgl_context_obj=cgl_context)
```

For example, if glfw is used to create an OpenGL window, it is enough to set the current context through glfw and the `syphon.server.SyphonOpenGLServer` will be able to find this context on its own.

```python
glfw.make_context_current(window)
server = syphon.SyphonOpenGLServer("Demo")
```

## Shared Directory
To get a list of active Syphon servers on the system, the `syphon.server_directory.SyphonServerDirectory` can be used. The resulting list of objects is of type `syphon.server_directory.SyphonServerDescription`.

```python
directory = syphon.SyphonServerDirectory()
servers = directory.servers

for server in servers:
    print(f"{server.app_name} ({server.uuid})")
```

It is also possible to listen for events when a server changes its status. However, it is important to update the NSRunLoop to receive messages. This can be done by repeatedly calling `directory.update_run_loop()`.

```python
def handler(event):
    print("A new server has been announced.")


directory.add_observer(syphon.SyphonServerNotification.Announce, handler)

while True:
    directory.update_run_loop()
    time.sleep(1.0)
```

## Syphon Client

### Metal Client

### OpenGL Client

## Utilities

### Raw

### Numpy

## Python Binding

