"""
Prime95 Manager module for CPU stress testing
Provides a singleton manager for Prime95 functionality

author: AI Assistant
prompted by: pjaako

This module provides a singleton manager for Prime95 functionality,
allowing easy control of Prime95 torture tests from Python scripts.

Features:
- Singleton pattern for easy access from anywhere in the code
- Methods for starting and stopping Prime95 torture tests
- Configuration options for different test types
- Automatic process management

Example usage:
```python
from prime95 import Prime95Manager

# Get the singleton instance
manager = Prime95Manager.get_instance()

# Start a torture test
manager.start_torture_test()

# Do something while the test is running
import time
time.sleep(60)

# Stop the torture test
manager.stop_torture_test()
```
"""

import os
import sys
import subprocess
import time
import signal
import psutil
from typing import Optional, List, Dict
import tempfile
import shutil
import ctypes
from ctypes import wintypes

# Constants
DEFAULT_PRIME95_PATH = r"External\Prime95\prime95.exe"
DEFAULT_TIMEOUT = 30  # Timeout in seconds for process operations

# Windows API constants and functions for window management
SW_HIDE = 0
SW_SHOW = 5
GW_OWNER = 4

# Function to find and hide windows by title
def find_window_by_title(title_pattern):
    """Find a window by its title pattern and return the handle."""
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
    GetWindowText = ctypes.windll.user32.GetWindowTextW
    GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible

    titles = []

    def foreach_window(hwnd, lParam):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLength(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buff, length + 1)
            titles.append((hwnd, buff.value))
        return True

    EnumWindows(EnumWindowsProc(foreach_window), 0)

    # Return windows that match the pattern
    matching_windows = [(hwnd, title) for hwnd, title in titles if title_pattern==title]
    return matching_windows

def hide_window(hwnd):
    """Hide a window by its handle."""
    ShowWindow = ctypes.windll.user32.ShowWindow
    return ShowWindow(hwnd, SW_HIDE)


class Prime95Manager:
    """Singleton manager for Prime95 functionality."""
    _instance = None

    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance of Prime95Manager."""
        if cls._instance is None:
            cls._instance = Prime95Manager()
        return cls._instance

    def __init__(self, prime95_path: str = DEFAULT_PRIME95_PATH):
        """Initialize the Prime95Manager.

        Args:
            prime95_path: Path to the Prime95 executable
        """
        self.prime95_path = prime95_path
        self.process = None
        self.running = False
        self.config_dir = None
        self._initialize()

    def _initialize(self):
        """Initialize the Prime95Manager."""
        # Check if Prime95 executable exists
        if not os.path.exists(self.prime95_path):
            print(f"Warning: Prime95 executable not found at {self.prime95_path}")
            print("Please download Prime95 and place it in the specified location.")
            print("You can download Prime95 from: https://www.mersenne.org/download/")
        else:
            print(f"Prime95 executable found at {self.prime95_path}")

    def is_prime95_running(self) -> bool:
        """Check if Prime95 is currently running.

        Returns:
            bool: True if Prime95 is running, False otherwise
        """
        # Check if our tracked process is running
        if self.process and self.process.poll() is None:
            return True

        # Also check if any Prime95 process is running in the system
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'prime95' in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        return False

    def is_functional(self) -> bool:
        """Check if Prime95 is properly installed and can be used.

        This method checks if the Prime95 executable exists and is accessible,
        without actually starting a torture test.

        Returns:
            bool: True if Prime95 is functional, False otherwise
        """
        # Check if Prime95 executable exists
        if not os.path.exists(self.prime95_path):
            print(f"Warning: Prime95 executable not found at {self.prime95_path}")
            print("Please download Prime95 and place it in the specified location.")
            print("You can download Prime95 from: https://www.mersenne.org/download/")
            return False

        # Check if Prime95 is already running
        if self.is_prime95_running():
            # If it's already running, we consider it functional
            return True

        # Try to run Prime95 with the -h option to check if it works
        try:
            # Run Prime95 with -h option (help) to check if it works
            # This should exit immediately without starting a torture test
            result = subprocess.run(
                [self.prime95_path, "-h"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5  # 5 seconds timeout
            )

            # Check if Prime95 exited with a success code
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError) as e:
            print(f"Error checking Prime95 functionality: {e}")
            return False

    def start_torture_test(self, 
                          test_type: str = "Small FFTs", 
                          num_threads: Optional[int] = None,
                          memory: Optional[int] = None) -> bool:
        """Start a Prime95 torture test.

        This method configures and starts a Prime95 torture test. It uses several techniques
        to suppress the GIMPS invitation dialog and run Prime95 in a windowless mode:
        1. Sets UsePrimenet=0 and QuitGIMPS=1 in the local.txt configuration file
        2. Uses the -t command line option to start the torture test directly
        3. Uses subprocess.CREATE_NO_WINDOW flag to run Prime95 without a visible window

        Args:
            test_type: Type of torture test to run. Options are:
                       "Small FFTs" (maximum heat/CPU stress)
                       "Large FFTs" (maximum power consumption)
                       "Blend" (tests both CPU and RAM)
            num_threads: Number of worker threads to use (default: all logical cores)
            memory: Amount of memory to use in MB (default: Prime95's default)

        Returns:
            bool: True if the torture test was started successfully, False otherwise
        """
        # Check if Prime95 is already running
        if self.is_prime95_running():
            print("Prime95 is already running. Stop it first before starting a new test.")
            return False

        # Validate test type
        valid_test_types = ["Small FFTs", "Large FFTs", "Blend"]
        if test_type not in valid_test_types:
            print(f"Invalid test type: {test_type}. Valid options are: {', '.join(valid_test_types)}")
            return False

        # Create a temporary directory for Prime95 configuration
        self.config_dir = tempfile.mkdtemp(prefix="prime95_config_")

        # Create Prime95 configuration file
        config_path = os.path.join(self.config_dir, "prime.txt")
        print (f"Creating Prime95 configuration file: {config_path}")
        with open(config_path, 'w') as f:
            f.write(f"TortureType={self._get_torture_type_code(test_type)}\n")
            if num_threads is not None:
                f.write(f"NumThreads={num_threads}\n")
            if memory is not None:
                f.write(f"TortureMem={memory}\n")
            f.write("CpuSupportsSSE=1\n")
            f.write("CpuSupportsSSE2=1\n")
            f.write("CpuSupportsAVX=1\n")  # Enable AVX instructions for maximum stress
            f.write("CpuSupportsAVX2=1\n")  # Enable AVX2 instructions for maximum stress
            f.write("CpuSupportsFMA3=1\n")  # Enable FMA3 instructions for maximum stress
            f.write("CpuSupportsAVX512F=1\n")



        # Create local.txt to automatically start torture test and suppress GIMPS invitation dialog
        local_path = os.path.join(self.config_dir, "local.txt")
        with open(local_path, 'w') as f:
            f.write("[PrimeNet]\n")
            f.write("StressTester=1\n")  # Enable stress testing mode
            f.write("TortureTime=6\n")   # Run indefinitely (6 = no time limit)
            f.write("UsePrimenet=0\n")   # Disable PrimeNet to avoid GIMPS invitation dialog
            f.write("QuitGIMPS=1\n")     # Quit GIMPS to avoid invitation dialog

        try:
            # Start Prime95 with the configuration directory and run torture test directly
            # No space between -W and directory path as per Prime95 documentation
            cmd = [self.prime95_path, "-W" + self.config_dir, "-t"]
            # Use CREATE_NO_WINDOW flag to run Prime95 in a windowless mode
            self.process = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)


            #check every 0.1 seconds if the process is running. If it is, break out of the loop
            #timeout is 2 seconds
            for i in range(int(2/0.1)):
                if self.process.poll() is None:
                    self.running = True
                    break
                time.sleep(0.1)
            if not self.running:
                print(f"Failed to start Prime95. Return code: {self.process.returncode}")
                return False


            prime95_windows = find_window_by_title("Prime95")
            for i in range(int(2/0.1)):
                prime95_windows = find_window_by_title("Prime95")
                #is the list empty?
                if prime95_windows:
                    for hwnd, title in prime95_windows:
                        print(f"Hiding Prime95 window: {title}")
                        hide_window(hwnd)
                    break
                time.sleep(0.1)


            print(f"Prime95 torture test ({test_type}) started successfully.")
            return True

        except Exception as e:
            print(f"Error starting Prime95: {e}")
            return False

    def stop_torture_test(self) -> bool:
        """Stop the running Prime95 torture test.

        Returns:
            bool: True if the torture test was stopped successfully, False otherwise
        """
        if not self.is_prime95_running():
            print("Prime95 is not running.")
            return True  # Already stopped

        try:
            # Try to terminate the process gracefully
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=DEFAULT_TIMEOUT)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    self.process.kill()

            # Also try to kill any other Prime95 processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'prime95' in proc.info['name'].lower():
                        psutil.Process(proc.info['pid']).terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            # Clean up the temporary configuration directory
            if self.config_dir and os.path.exists(self.config_dir):
                shutil.rmtree(self.config_dir, ignore_errors=True)
                self.config_dir = None

            self.running = False
            print("Prime95 torture test stopped successfully.")
            return True
        except Exception as e:
            print(f"Error stopping Prime95: {e}")
            return False

    @staticmethod
    def _get_torture_type_code(test_type: str) -> int:
        """Convert test type string to Prime95 code.

        Args:
            test_type: Type of torture test

        Returns:
            int: Prime95 code for the test type
        """
        if test_type == "Small FFTs":
            return 0
        elif test_type == "Large FFTs":
            return 1
        elif test_type == "Blend":
            return 2
        else:
            return 0  # Default to Small FFTs


if __name__ == "__main__":
    print("Prime95 Manager Test")

    # Get the singleton instance
    manager = Prime95Manager.get_instance()

    # Check if Prime95 is already running
    if manager.is_prime95_running():
        print("Prime95 is already running. Stopping it...")
        manager.stop_torture_test()

    # Start a torture test
    print("Starting Prime95 torture test (Small FFTs)...")
    if manager.start_torture_test(test_type="Small FFTs"):
        print("Torture test started successfully.")



    # Wait for user input before exiting
    input("Press any key to exit...")
    if manager.stop_torture_test():
        print("Torture test stopped successfully.")
    else:
        print("Failed to stop torture test.")
    sys.exit(0)
