import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, List, Optional

import objc
from Cocoa import NSDate, NSDefaultRunLoopMode, NSImage, NSRunLoop


class SyphonServerNotification(Enum):
    """
    Enum representing Syphon server notifications.

    Enum Values:
    - Announce: A new SyphonServer is available on the system.
    - Update: An existing SyphonServer instance has changed its description.
    - Retire: A SyphonServer instance will no longer be available.
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
    icon: Optional[NSImage]
    raw: Any

    @classmethod
    def from_native(cls, raw):
        """Wrap a complete native description without requiring optional display metadata."""
        return cls(
            uuid=str(raw.get("SyphonServerDescriptionUUIDKey") or ""),
            name=str(raw.get("SyphonServerDescriptionNameKey") or ""),
            app_name=str(raw.get("SyphonServerDescriptionAppNameKey") or ""),
            icon=raw.get("SyphonServerDescriptionIconKey"),
            raw=raw,
        )


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
        self._observer_lock = threading.RLock()
        self._observers = []
        self._closed = False

    def add_observer(self, notification: SyphonServerNotification, handler: Callable[[Any], None]):
        """
        Add an observer for a Syphon server notification.

        Parameters:
        - notification (SyphonServerNotification): The notification to observe.
        - handler (Callable[[Any], None]): The handler function to be called when the notification is received.

        Returns the native observer token. Pass it to remove_observer(), or close this
        directory to remove all tokens it owns. Callback threading follows NSNotificationCenter.
        """
        with self._observer_lock:
            if self._closed:
                raise RuntimeError("Syphon server directory is closed")
            token = self._notification_center.addObserverForName_object_queue_usingBlock_(
                notification.value, None, None, handler
            )
            self._observers.append(token)
            return token

    def remove_observer(self, token):
        """Remove a token returned by this directory; unknown/removed tokens are ignored."""
        with self._observer_lock:
            for index, owned in enumerate(self._observers):
                if owned is token:
                    self._observers.pop(index)
                    break
            else:
                return
        self._notification_center.removeObserver_(token)

    def close(self):
        """Remove this wrapper's observers once, without stopping the shared native directory."""
        with self._observer_lock:
            self._closed = True
            tokens, self._observers = self._observers, []
        for token in tokens:
            self._notification_center.removeObserver_(token)

    def __enter__(self):
        with self._observer_lock:
            if self._closed:
                raise RuntimeError("Syphon server directory is closed")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

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

        return [SyphonServerDescription.from_native(raw) for raw in servers]

    def update_run_loop(self):
        """
        Update the run loop to process events.
        """
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            NSDefaultRunLoopMode, NSDate.dateWithTimeIntervalSinceNow_(self.run_loop_interval)
        )

    def servers_matching_name(
        self, name: Optional[str] = None, app_name: Optional[str] = None
    ) -> List[SyphonServerDescription]:
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
