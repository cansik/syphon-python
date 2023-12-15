from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any, List, Optional

import objc
from Cocoa import NSRunLoop, NSDefaultRunLoopMode, NSDate, NSImage


class SyphonServerNotification(Enum):
    Announce = "SyphonServerAnnounceNotification"
    Update = "SyphonServerUpdateNotification"
    Retire = "SyphonServerRetireNotification"


@dataclass
class SyphonServerDescription:
    uuid: str
    name: str
    app_name: str
    icon: NSImage
    raw: Any


class SyphonServerDirectory:
    def __init__(self):
        self._syphonServerDirectoryObjC = objc.lookUpClass("SyphonServerDirectory")
        self._notification_center = objc.lookUpClass("NSNotificationCenter").defaultCenter()

        self.run_loop_interval: float = 1.0

    def add_observer(self, notification: SyphonServerNotification, handler: Callable[[Any], None]):
        self._notification_center.addObserverForName_object_queue_usingBlock_(
            notification.value,
            None,
            None,
            handler
        )

    @property
    def servers(self) -> List[SyphonServerDescription]:
        self.update_run_loop()
        directory = self._syphonServerDirectoryObjC.sharedDirectory()
        servers = directory.servers()

        return [
            SyphonServerDescription(
                str(s["SyphonServerDescriptionUUIDKey"]),
                str(s["SyphonServerDescriptionNameKey"]),
                str(s["SyphonServerDescriptionAppNameKey"]),
                s["SyphonServerDescriptionIconKey"],
                s
            )
            for s in servers
        ]

    def update_run_loop(self):
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            NSDefaultRunLoopMode,
            NSDate.dateWithTimeIntervalSinceNow_(self.run_loop_interval)
        )

    def servers_matching_name(self,
                              name: Optional[str] = None,
                              app_name: Optional[str] = None) -> List[SyphonServerDescription]:
        filtered_servers = []

        for server in self.servers:
            if name is not None and name == server.name:
                filtered_servers.append(server)
                continue

            if app_name is not None and app_name == server.app_name:
                filtered_servers.append(server)
                continue

        return filtered_servers
