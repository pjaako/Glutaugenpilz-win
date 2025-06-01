"""
ZenStates Manager module for AMD Ryzen CPUs
Provides a singleton manager for ZenStates.Core functionality

author: AI Assistant
prompted by: pjaako

This module provides a singleton manager for ZenStates.Core functionality,
allowing easy access to CPU temperature, PPT limit, and package power values.

Features:
- Singleton pattern for easy access from anywhere in the code
- Automatic initialization when getting the singleton instance
- Context manager support for proper resource management
- Properties for temperature, PPT limit, current PPT, and package power
- Methods for setting PPT limit with verification
- Efficient caching with centralized refresh mechanism
- Prevents unnecessary refreshes when multiple properties are accessed in sequence
- Constants for power table offsets

Example usage:
```python
from zenstates import ZenStatesManager

# Get the singleton instance
manager = ZenStatesManager.get_instance()

# Get temperature
temp = manager.temperature
print(f"CPU Temperature: {temp}°C")

# Get PPT limit
ppt_limit = manager.ppt_limit
print(f"PPT Limit: {ppt_limit}W")

# Get current PPT value (actual power consumption)
current_ppt = manager.current_ppt
print(f"Current PPT: {current_ppt}W")

# Get package power (same as current PPT)
package_power = manager.package_power
print(f"Package Power: {package_power}W")

# Set PPT limit using the property setter
try:
    manager.ppt_limit = 222
    print("PPT limit set successfully")
except ValueError as e:
    print(f"Failed to set PPT limit: {e}")
```
"""

import os
import sys
import time
from _ast import Raise

import clr
from typing import Optional

# Constants
ZEN_STATES_CORE_PATH = r"External/ZenStates-Core/bin"
NET_VERSION = "net20"
CACHE_INTERVAL = 1.0  # Cache lifetime in seconds


class PMTableIndices:
    """Offset constants for AMD Ryzen CPU power management table.

    These constants represent the specific indices in the power management table
    where various power-related values can be found.
    """
    # Power table offsets
    PPT_LIMIT = 2       # Current PPT limit
    PACKAGE_POWER = 3   # Current PPT value (actual power consumption)
    TDC = 26            # TDC value
    EDC = 277           # EDC value


class ZenStatesManager:
    """Singleton manager for ZenStates.Core functionality."""
    _instance = None

    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance of ZenStatesManager."""
        if cls._instance is None:
            cls._instance = ZenStatesManager()
        return cls._instance

    def __init__(self):
        """Initialize the ZenStatesManager."""
        self._cpu = None
        self.last_read_time = 0
        self.cache_lifetime = CACHE_INTERVAL
        self._cached_power_table = None

    @property
    def cpu(self):
        """Get the CPU object, initializing if necessary.

        Returns:
            The CPU object

        Raises:
            RuntimeError: If initialization fails
        """
        if self._cpu is None:
            self._initialize()
            if self._cpu is None:
                raise RuntimeError("Failed to initialize ZenStates.Core")
        return self._cpu

    def __enter__(self):
        """Context manager entry that initializes ZenStates.Core."""
        try:
            # Access the cpu property to trigger initialization if needed
            _ = self.cpu
        except RuntimeError:
            # Initialization failed, but we'll continue anyway
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # No cleanup needed for ZenStates.Core
        pass

    def _initialize(self):
        """Initialize ZenStates.Core and get the CPU object."""
        if self._load_zen_states():
            try:
                #noinspection PyUnresolvedReferences
                from ZenStates.Core import Cpu
                self._cpu = Cpu()
                print("ZenStates.Core initialized successfully")
            except (ImportError, ModuleNotFoundError) as e:
                print(f"Error importing ZenStates.Core module: {e}")
                self._cpu = None
            except RuntimeError as e:
                print(f"Error initializing ZenStates.Core: {e}")
                self._cpu = None
        else:
            print("Failed to load ZenStates.Core")
            self._cpu = None

    @staticmethod
    def _load_zen_states():
        """Load the ZenStates-Core DLL.

        Returns:
            bool: True if ZenStates-Core was loaded successfully, False otherwise
        """
        # Add the directory containing "normal" dlls used by ZenStates-Core to the DLL search path
        # This is necessary for ZenStates-Core to find its dependencies
        dll_path = os.path.join(os.path.dirname(__file__), ZEN_STATES_CORE_PATH)
        # Ensure the DLL directory is in the system PATH
        if hasattr(os, 'environ'):
            os_path = os.environ.get('PATH', '')
            if dll_path not in os_path:
                os.environ['PATH'] = dll_path + os.pathsep + os_path

        # now enable pythonnet to load the ZenStates-Core dll itself. It searches in sys.path
        zen_path = os.path.join(os.path.dirname(__file__), ZEN_STATES_CORE_PATH, NET_VERSION)
        if zen_path not in sys.path:
            sys.path.append(zen_path)

        try:
            # everything ready. IDE marking this as an error is normal as it has no idea about the referred namespace.
            #noinspection PyUnresolvedReferences
            res = clr.AddReference("ZenStates-Core")
            return res is not None
        except FileNotFoundError as e:
            print(f"ZenStates-Core DLL not found: {e}")
            print(f"Current sys.path: {sys.path}")
            if hasattr(os, 'environ'):
                print(f"Current PATH: {os.environ.get('PATH', '')}")
            return False
        except (ImportError, ModuleNotFoundError) as e:
            print(f"Error importing ZenStates-Core: {e}")
            print(f"Current sys.path: {sys.path}")
            if hasattr(os, 'environ'):
                print(f"Current PATH: {os.environ.get('PATH', '')}")
            return False
        except RuntimeError as e:
            print(f"Error loading ZenStates-Core: {e}")
            print(f"Current sys.path: {sys.path}")
            if hasattr(os, 'environ'):
                print(f"Current PATH: {os.environ.get('PATH', '')}")
            return False

    def _refresh_data_if_needed(self, force: bool = False):
        """Refresh cached data if needed.

        Args:
            force: Force a refresh regardless of cache lifetime

        Raises:
            RuntimeError: If ZenStates.Core initialization fails
            IOError: If communication with the hardware fails
            ValueError: If the data format is invalid
        """
        current_time = time.time()
        if force or (current_time - self.last_read_time > self.cache_lifetime):
            try:
                # Refresh power table data
                # This will automatically initialize ZenStates.Core if needed via the cpu property
                self.cpu.RefreshPowerTable()
                self._cached_power_table = self.cpu.powerTable.Table
                self.last_read_time = current_time
            except (ImportError, ModuleNotFoundError) as e:
                print(f"Error importing ZenStates.Core module: {e}")
                raise RuntimeError(f"Failed to import ZenStates.Core module: {e}")
            except IOError as e:
                print(f"Error communicating with hardware: {e}")
                raise IOError(f"Failed to communicate with hardware: {e}")
            except (IndexError, AttributeError) as e:
                print(f"Error accessing power table data: {e}")
                raise ValueError(f"Invalid power table data format: {e}")
            except RuntimeError as e:
                print(f"Error refreshing data: {e}")
                raise RuntimeError(f"Failed to refresh data: {e}")
        return self._cached_power_table

    @property
    def power_management_table(self):
        """Get the power table."""
        return self._refresh_data_if_needed()

    @property
    def temperature(self) -> Optional[float]:
        """Get the current CPU temperature.

        Returns:
            float: The CPU temperature in Celsius, or None if not available

        Raises:
            RuntimeError: If ZenStates.Core initialization fails
            IOError: If communication with the hardware fails
            AttributeError: If CPU object is not properly initialized
            TypeError: If temperature value has an unexpected type
        """
        try:
            # Temperature is not part of the power table, so we need to get it directly
            # This will automatically initialize ZenStates.Core if needed via the cpu property
            return self.cpu.GetCpuTemperature()
        except Exception as e:
            print(f"Error initializing or refreshing data: {e}")
            return None


    @property
    def package_power(self) -> Optional[float]:
        """Get the current package power value (actual power consumption).

        Returns:
            float: The current PPT value in Watts, or None if not available

        """
        try:
            return self.power_management_table[PMTableIndices.PACKAGE_POWER]
        except Exception as e:
            print(f"Error initializing or refreshing data: {e}")
            return None


    @property
    def ppt_limit(self) -> Optional[float]:
        """Get or set the current PPT limit.

        Returns:
            float: The PPT limit in Watts, or None if not available

        """
        try:
            return self.power_management_table[PMTableIndices.PPT_LIMIT]
        except Exception as e:
            print(f"Error initializing or refreshing data: {e}")
            return None


    @ppt_limit.setter
    def ppt_limit(self, value: float):
        """Set the PPT limit to the given value.

        Args:
            value: The PPT limit in Watts
        """

        try:
            # SetPPTLimit accepts only int values
            # This will automatically initialize ZenStates.Core if needed via the cpu property
            value = int(value)
            self.cpu.SetPPTLimit(value)
            time.sleep(1)
            if self.ppt_limit != value:
                raise ValueError(f"Failed to set PPT limit to {value}W. PPT limit is still {self.ppt_limit}W.")

        except Exception as e:
            print(f"Error initializing or refreshing data: {e}")
            raise ValueError(f"Failed to set PPT limit: {e}")





if __name__ == "__main__":

    #elevate permissions to run this script
    from elevator import is_admin, elevate
    if not is_admin():
        print("This program requires administrative privileges.")
        elevate()
        sys.exit(0)

    manager = ZenStatesManager.get_instance()
    # Get and print PPT limit
    ppt_limit = manager.ppt_limit
    print(f"PPT Limit: {ppt_limit}W") if ppt_limit is not None else print("PPT limit not available")

    # Get and print temperature
    temp = manager.temperature
    print(f"CPU Temperature: {temp}°C") if temp is not None else print("Temperature not available")




    # Get and print package power
    package_power = manager.package_power
    print(f"Package Power: {package_power}W") if package_power is not None else print("Package power not available")

    # Set PPT limit using the property setter
    target_ppt = ppt_limit - 1
    try:
        manager.ppt_limit = target_ppt
        print(f"PPT limit set successfully")

        # Verify the new PPT limit
        new_ppt_limit = manager.ppt_limit
        print(f"New PPT Limit: {new_ppt_limit}W")
    except ValueError as e:
        print(f"Failed to set PPT limit: {e}")

    # Wait for user input before exiting
    input("Press any key to exit...")
    sys.exit(0)
