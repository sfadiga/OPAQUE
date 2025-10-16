# This Python file uses the following encoding: utf-8
"""
# OPAQUE Framework
#
# @copyright 2025 Sandro Fadiga
#
# This software is licensed under the MIT License.
# You should have received a copy of the MIT License along with this program.
# If not, see <https://opensource.org/licenses/MIT>.
"""

import os
import socket
import atexit
import time

from PySide6.QtCore import QObject, Signal


class SingleInstanceManager(QObject):
    """
    Ensures only one instance of the application is running.
    Uses socket binding as the primary mechanism for instance detection.
    """

    # Signal emitted when another instance is detected
    another_instance_detected = Signal()

    def __init__(self, app_name="ft_ui_tool", port=49152):
        """
        Initialize the single instance manager.

        Args:
            app_name: Name used for the lock file
            port: TCP port to bind to (default is first private port 49152)
        """
        super().__init__()
        self.app_name = app_name
        self.port = port
        self.lock_file_path = os.path.join(".", f"{app_name}.lock")
        self.lock_file = None
        self.socket = None
        self.lock_acquired = False

        # Register cleanup on exit
        atexit.register(self.release_lock)

    def try_acquire_lock(self) -> bool:
        """
        Try to acquire the application lock.

        Returns:
            bool: True if lock was acquired, False otherwise
        """
        if self.lock_acquired:
            return True

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(('127.0.0.1', self.port))
            self.socket.listen(1)
        except socket.error:
            self.socket = None
            return False

        try:
            lock_info = f"{os.getpid()}\n{time.time()}\n{self.app_name}"
            with open(self.lock_file_path, 'w', encoding='utf-8') as f:
                f.write(lock_info)
            self.lock_file = self.lock_file_path
            self.lock_acquired = True
            return True
        except IOError:
            self.release_lock()
            return False

    def release_lock(self):
        """
        Clean up lock file and socket when application exits.
        """
        if not self.lock_acquired:
            return

        # Remove lock file
        if self.lock_file and os.path.exists(self.lock_file):
            try:
                os.remove(self.lock_file)
                print(f"Lock file removed: {self.lock_file}")
            except IOError as e:
                print(f"Failed to remove lock file: {e}")

        # Close socket
        if self.socket:
            try:
                self.socket.close()
                print("Socket closed")
            except socket.error as e:
                print(f"Failed to close socket: {e}")

        self.lock_acquired = False
        self.socket = None
