import syphon
import objc
from Foundation import NSAutoreleasePool, NSRunLoop, NSDate
from PyObjCTools import AppHelper


def server_announce_notification(notification):
    print("announce")
    server_description = notification.userInfo()
    print(server_description)

    SyphonServerDirectoryObjC = objc.lookUpClass("SyphonServerDirectory")

    server_directory = SyphonServerDirectoryObjC.sharedDirectory()
    servers = server_directory.servers()

    print("servers:")
    for server_info in servers:
        print(server_info)

    print(server_description)
    # Do something with server_description, e.g., instantiate a client


def main():
    pool = NSAutoreleasePool.alloc().init()

    # Add an observer for the SyphonServerAnnounceNotification
    notification_center = objc.lookUpClass('NSNotificationCenter').defaultCenter()
    notification_center.addObserverForName_object_queue_usingBlock_(
        "SyphonServerAnnounceNotification",
        None,
        None,
        server_announce_notification
    )

    quit = False
    while not quit:
        # Wake every second (you can also use AppHelper.runConsoleEventLoop() if needed)
        AppHelper.runConsoleEventLoop()

    pool.release()


if __name__ == "__main__":
    main()
