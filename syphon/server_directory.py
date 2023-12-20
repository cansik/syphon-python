from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any, List, Optional

import objc
from Cocoa import NSRunLoop, NSDefaultRunLoopMode, NSDate, NSImage


class SyphonServerNotification(Enum):
    """
    Enum representing Syphon server notifications.

    Enum Values:
    - Announce: Notification for a Syphon server announcement.
    - Update: Notification for a Syphon server update.
    - Retire: Notification for retiring a Syphon server.
    """
    Announce = "SyphonServerAnnounceNotification"
    Update = "SyphonServerUpdateNotification"
    Retire = "SyphonServerRetireNotification"


@dataclass
class SyphonServerDescription:
    """
    Data class representing the description of a Syphon server.

    Attributes:
    - uuid (str): The UUID of the Syphon server.
    - name (str): The name of the Syphon server.
    - app_name (str): The name of the application associated with the Syphon server.
    - icon (NSImage): The icon image of the Syphon server.
    - raw (Any): The raw server information.
    """
    uuid: str
    name: str
    app_name: str
    icon: NSImage
    raw: Any


class SyphonServerDirectory:
    """
    Class for interacting with the Syphon server directory.

    Attributes:
    - run_loop_interval (float): The interval for the run loop in seconds.
    """

    def __init__(self):
        """
        Initialize a SyphonServerDirectory.
        """
        self._syphonServerDirectoryObjC = objc.lookUpClass("SyphonServerDirectory")
        self._notification_center = objc.lookUpClass("NSNotificationCenter").defaultCenter()

        self.run_loop_interval: float = 1.0

    def add_observer(self, notification: SyphonServerNotification, handler: Callable[[Any], None]):
        """
        Add an observer for a Syphon server notification.

        Parameters:
        - notification (SyphonServerNotification): The notification to observe.
        - handler (Callable[[Any], None]): The handler function to be called when the notification is received.
        """
        self._notification_center.addObserverForName_object_queue_usingBlock_(
            notification.value,
            None,
            None,
            handler
        )

    @property
    def servers(self) -> List[SyphonServerDescription]:
        """
        Get a list of Syphon servers in the directory.

        Returns:
        - List[SyphonServerDescription]: A list of SyphonServerDescription objects.
        """
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
        """
        Update the run loop to process events.
        """
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            NSDefaultRunLoopMode,
            NSDate.dateWithTimeIntervalSinceNow_(self.run_loop_interval)
        )

    def servers_matching_name(self,
                              name: Optional[str] = None,
                              app_name: Optional[str] = None) -> List[SyphonServerDescription]:
        """
        Get a list of Syphon servers that match the specified name or application name.

        Parameters:
        - name (Optional[str]): The name to match.
        - app_name (Optional[str]): The application name to match.

        Returns:
        - List[SyphonServerDescription]: A list of SyphonServerDescription objects that match the criteria.
        """
        filtered_servers = []

        for server in self.servers:
            if name is not None and name == server.name:
                filtered_servers.append(server)
                continue

            if app_name is not None and app_name == server.app_name:
                filtered_servers.append(server)
                continue

        return filtered_servers
