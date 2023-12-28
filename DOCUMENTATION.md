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
To share graphic textures with other applications, a syphon server (sender) has to be created. All server implementations are based on the `syphon.server.BaseSyphonServer` and share the same interface, except the constructor. The following code example creates either a Metal oder OpenGL based server, using the app name `Demo` and using the default device or context.

```python
# create a Metal based server
server = syphon.SyphonMetalServer("Demo")

# create an OpenGL based server
server = syphon.SyphonOpenGLServer("Demo")
```

To publish a texture, the method `syphon.server.BaseSyphonServer.publish_frame_texture()` can be used. We assume that the corresponding texture has already been created and is available in the `texture` variable. To see how to create and fill a MTLTexture or glTexture, please have a look at the [examples](https://github.com/cansik/syphon-python/tree/main/examples).

```python
texture = ... # MTLTexture or glTexture
server.publish_frame_texture(texture)
```

The `syphon.server.BaseSyphonServer.publish_frame_texture()` contains a flag called `flip` to flip the texture horizontally. This can be set to `True` if the image is upside down on the receiver side.

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
To receive graphic textures from other applications, a syphon client (receiver) must be created. All client implementations are based on `syphon.client.BaseSyphonClient` and share the same interface except for the constructor. The following code example creates either a Metal or OpenGL based client, using the first found server description and the default device or context.

```python
# receive the first server description
directory = syphon.SyphonServerDirectory()
server_info = directory.servers[0]

# create a Metal client
client = syphon.SyphonMetalClient(server_info)

# create an OpenGL client
client = syphon.SyphonOpenGLClient(server_info)
```

To get textures, it is possible to first check if the server has provided a new texture using the `has_new_frame` property, and then read the new frame image using the `new_frame_image` property.

```python
if client.has_new_frame:
    texture = client.new_frame_image # either MTLTexture or glTexture
```

To stop the client and disconnect from the server, the `syphon.client.BaseSyphonClient.stop()` method can be used.

```python
client.stop()
```

### Metal Client
As with the [metal server](#metal-server), it is possible to overwrite the device which the metal client is running on. This can be done by using the additional parameters of the `syphon.client.SyphonMetalClient`.

```python
import Metal

# overwrite the mtl_device
mtl_device = Metal.MTLCreateSystemDefaultDevice()
client = syphon.SyphonMetalClient(server_info, device=mtl_device)
```

### OpenGL Client
As with the [opengl server](#opengl-server), it is possible to override the automatic lookup by passing a valid `cglContextObj` as a parameter to the `syphon.client.SyphonOpenGLClient`.

```python
import AppKit

ns_ctx = AppKit.NSOpenGLContext.currentContext()
cgl_context = ns_ctx.CGLContextObj()

client = syphon.SyphonOpenGLClient(server_info, cgl_context_obj=cgl_context)
```

## Utilities
To make sharing graphic textures as easy as possible, the library provides some utility methods to manipulate texture data.

### Raw
The `syphon.utils.raw` module contains methods to create and manipulate textures with a raw `bytes` array.

#### Create MTLTexture
To create an [MTLTexture](https://developer.apple.com/documentation/metal/mtltexture) the method `syphon.utils.raw.create_mtl_texture` can be used. It is possible to create your own default device or use a server's `syphon.server.SyphonMetalServer.device` property to get the current device.

```python
import Metal
from syphon.utils.raw import create_mtl_texture

mtl_device = Metal.MTLCreateSystemDefaultDevice()
texture = create_mtl_texture(mtl_device, 512, 512)
```

#### Manipulate MTLTexture
To write `bytes` to an [MTLTexture](https://developer.apple.com/documentation/metal/mtltexture) the method `syphon.utils.raw.copy_bytes_to_mtl_texture()` can be used.

```python
from syphon.utils.raw import copy_bytes_to_mtl_texture

data = ...  # bytes() based buffer
texture = ... # MLTTexture object

copy_bytes_to_mtl_texture(data, texture)
```

To read `bytes` from an [MTLTexture](https://developer.apple.com/documentation/metal/mtltexture) the method `syphon.utils.raw.copy_mtl_texture_to_bytes()` can be used.

```python
from syphon.utils.raw import copy_mtl_texture_to_bytes

texture = ... # MLTTexture object

data = copy_mtl_texture_to_bytes(texture) # returns bytes
```

### Numpy
If you are working with [Numpy](https://numpy.org/) arrays, the `syphon.utils.numpy` package contains helper methods for reading and writing numpy images to and from [MTLTexture](https://developer.apple.com/documentation/metal/mtltexture).

It is important to note that the `numpy` package is not installed by default, it must be installed using `pip install numpy`.

To write a numpy image to a MTLTexture, the `syphon.utils.numpy.copy_image_to_mtl_texture()` method can be used.

```python
import numpy as np
from syphon.utils.numpy import copy_image_to_mtl_texture

texture = ... # MLTTexture object

# create RGBA image
texture_data = np.zeros((512, 512, 4), dtype=np.uint8)

# copy image to texture
copy_image_to_mtl_texture(texture_data, texture)
```

To read a numpy image from a MTLTexture, the `syphon.utils.numpy.copy_mtl_texture_to_image()` method can be used.

```python
import numpy as np
from syphon.utils.numpy import copy_mtl_texture_to_image

texture = ... # MLTTexture object

texture_data = copy_mtl_texture_to_image(texture) # returns numpy array
```

## Python Binding
As described in the [Objective-C to Python](#objective-c-to-python) chapter, the syphon-python library is based on the [PyObjC](https://pyobjc.readthedocs.io/en/latest/) Python to Objective-C bridge. This means that there is no intermediate wrapper between Python and Objective-C, and it is possible to access and call Objective-C objects directly from Python. This can be useful if a method of the original Syphon framework has not yet been exposed by the wrapper.

### Access Objective-C Objects
To access the raw Objective-C object of a `syphon.server.SyphonMetalServer`, it is possible to access the `syphon.server.SyphonMetalServer.context` variable. To get a list of methods that can be called, the `dir()` method can be used.

```python
server = syphon.SyphonMetalServer("Demo")
objc_syphon_metal_server = server.context

print(dir(objc_syphon_metal_server))
```

### Raw Pointers to Python Objective-C Objects
The framework expects PyObjC pointers to be passed to the methods. Sometimes only raw ctype pointers are available. This example shows how to cast a [nanogui](https://github.com/mitsuba-renderer/nanogui) MTLTexture pointer to a PyObjC object.

```python
import ctypes
from typing import Any

import objc
from nanogui import Screen


def get_mtl_texture(texture: Any) -> Any:
    ctypes.pythonapi.PyCapsule_GetName.restype = ctypes.c_char_p
    ctypes.pythonapi.PyCapsule_GetName.argtypes = [ctypes.py_object]
    capsule_name = ctypes.pythonapi.PyCapsule_GetName(texture)
    
    ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
    ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
    result = ctypes.pythonapi.PyCapsule_GetPointer(texture, capsule_name)

    mtl_texture = objc.objc_object(c_void_p=result)
    return mtl_texture


class SimpleServerScreen(Screen):
    ...

    def send(self):
        texture = self.metal_texture()  # of type PyCapsule
        texture_pointer = get_mtl_texture(texture)
        self.syphon_server.publish_frame_texture(texture_pointer, is_flipped=True)
```
