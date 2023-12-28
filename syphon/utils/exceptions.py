class SyphonException(Exception):
    pass


class NSOpenGLContextNotFoundException(SyphonException):
    def __init__(self):
        super(NSOpenGLContextNotFoundException, self).__init__("Could not get current NSOpenGLContext.")


class CGLContextNotFoundException(SyphonException):
    def __init__(self):
        super(CGLContextNotFoundException, self).__init__("Could not get current CGLContextObj from NSOpenGLContext.")
