#this script gets temperature sensors values from aquacomputer Quadro
# which is a HID device with VID:PID=0x0c70:0xF00D
# written by an AI coding assistant
# prompts for AI authored by pjaako

import hid
import time
from typing import Iterator, List, Optional, Tuple


# Device constants for Aquacomputer Quadro
class QuadroConstants:
    # Device identifiers
    VENDOR_ID = 0x0c70
    PRODUCT_ID = 0xF00D

    # Temperature sensor offsets
    TEMP_1 = 52
    TEMP_2 = 54
    TEMP_3 = 56
    TEMP_4 = 58

    # Fan speed offsets
    FAN_SPEED_1 = 120
    FAN_SPEED_2 = 133
    FAN_SPEED_3 = 146
    FAN_SPEED_4 = 159

    # Fan current offsets
    FAN_CURRENT_1 = 116
    FAN_CURRENT_2 = 129
    FAN_CURRENT_3 = 142
    FAN_CURRENT_4 = 155

    #caching interval
    CACHE_INTERVAL = 1.0



class QuadroManager:
    """Singleton manager for Quadro device with persistent connection."""
    _instance = None

    @classmethod
    def get_instance(cls):
        """Get or create the singleton instance of QuadroManager."""
        if cls._instance is None:
            cls._instance = QuadroManager()
        return cls._instance

    def __init__(self):
        """Initialize the QuadroManager with a persistent device connection."""
        self.device = None
        self.quadro_device = None
        self.last_read_time = 0
        self.cache_lifetime = QuadroConstants.CACHE_INTERVAL

    def __enter__(self):
        """Context manager entry that opens the device connection."""
        if self.quadro_device is None:
            self.quadro_device = QuadroDevice()
            self.quadro_device.__enter__()
            # Check if connection was successful
            if not self.quadro_device.is_connected:
                # Connection failed, but we don't raise an exception
                # We'll handle this in the methods that need the device
                pass
        return self

    @property
    def is_connected(self):
        """Check if the device is connected."""
        return self.quadro_device is not None and self.quadro_device.is_connected

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit that properly closes the device connection."""
        if self.quadro_device:
            self.quadro_device.__exit__(exc_type, exc_val, exc_tb)
            self.quadro_device = None

    def _refresh_data_if_needed(self, force: bool = False):
        """Read fresh data if the cache has expired or if forced.

        Args:
            force: Force a refresh regardless of cache lifetime

        Returns:
            True if data was successfully refreshed or is still valid, False otherwise
        """
        current_time = time.time()
        if force or (current_time - self.last_read_time > self.cache_lifetime):
            try:
                # Ensure device is open
                if self.quadro_device is None:
                    self.__enter__()

                # Check if device is connected
                if not self.is_connected:
                    # Try to reconnect
                    if not self.reconnect():
                        # Still not connected
                        return False

                # Read one data packet
                data = next(self.quadro_device.read_data())
                self.last_read_time = current_time
                return True
            except Exception as e:
                print(f"Error reading data: {e}")
                # Try to reconnect
                self.reconnect()
                return False
        return True

    def reconnect(self):
        """Attempt to reconnect to the device.

        Returns:
            True if reconnection was successful, False otherwise
        """
        self.__exit__(None, None, None)
        self.__enter__()
        return self.is_connected

    @property
    def temperatures(self) -> List[Optional[float]]:
        """Get the temperature values from the Quadro device."""
        if self._refresh_data_if_needed():
            return self.quadro_device.parse_temperatures()
        return [None, None, None, None]

    @property
    def fan_speeds(self) -> List[Optional[int]]:
        """Get the fan speed values from the Quadro device."""
        if self._refresh_data_if_needed():
            return self.quadro_device.parse_fan_speeds()
        return [None, None, None, None]

    @property
    def fan_currents(self) -> List[Optional[float]]:
        """Get the fan current values from the Quadro device."""
        if self._refresh_data_if_needed():
            return self.quadro_device.parse_fan_currents()
        return [None, None, None, None]


class QuadroDevice:
    def __init__(self, vendor_id: int = QuadroConstants.VENDOR_ID, product_id: int = QuadroConstants.PRODUCT_ID):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.device = None
        self.raw_data = bytearray(210)  # Same size as in Quadro.cs

    def __enter__(self):
        self.is_connected = False  # Initialize connection status
        try:
            self.device = hid.device()
            self.device.open(self.vendor_id, self.product_id)
            self.device.set_nonblocking(1)
            print("Device opened successfully")
            print(f"Manufacturer: {self.device.get_manufacturer_string()}")
            print(f"Device name: {self.device.get_product_string()}")
            print(f"Serial number: {self.device.get_serial_number_string()}")
            self.is_connected = True  # Set flag to indicate successful connection
        except IOError as ex:
            print(f"Error opening device with vendor_id: {self.vendor_id} and product_id: {self.product_id}:")
            print("Check if the device is connected and the correct VID:PID is used.")
            print(ex)
            self.device = None
            # Don't raise the exception, just return self with is_connected=False

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.device:
            self.device.close()
            self.is_connected = False

    @property
    def is_connected(self):
        """Check if the device is connected and opened successfully."""
        return hasattr(self, '_is_connected') and self._is_connected

    @is_connected.setter
    def is_connected(self, value):
        """Set the connection status."""
        self._is_connected = value

    def read_data(self, size: int = 210) -> Iterator[bytearray]:
        """Read data from the HID device.

        Args:
            size: Number of bytes to read (default: 210 as in Quadro.cs)

        Returns:
            Iterator yielding the raw data from the device
        """
        if not self.is_connected:
            # Device not connected, yield empty data
            yield self.raw_data
            return

        while True:
            try:
                if self.device:
                    data = self.device.read(size)
                    if data:
                        self.raw_data = bytearray(data)
                        yield self.raw_data
            except OSError:
                # Handle read errors
                continue
            time.sleep(1)

    def get_converted_value(self, index: int) -> Optional[int]:
        """Convert raw data at the given index to a usable value.

        This is equivalent to the GetConvertedValue method in Quadro.cs.

        Args:
            index: The index in the raw data array

        Returns:
            The converted value or None if the value is invalid
        """
        if index >= len(self.raw_data) or self.raw_data[index] == 127:  # 127 is sbyte.MaxValue in C#
            return None

        # Equivalent to: Convert.ToUInt16(_rawData[index + 1] | (_rawData[index] << 8))
        return (self.raw_data[index] << 8) | self.raw_data[index + 1]

    def parse_temperatures(self) -> List[Optional[float]]:
        """Parse the temperature values from the raw data.

        Returns:
            A list of 4 temperature values in Celsius, or None for invalid values
        """
        temps = []
        for index in [QuadroConstants.TEMP_1, QuadroConstants.TEMP_2, 
                     QuadroConstants.TEMP_3, QuadroConstants.TEMP_4]:
            value = self.get_converted_value(index)
            temps.append(value / 100.0 if value is not None else None)
        return temps

    def parse_fan_speeds(self) -> List[Optional[int]]:
        """Parse the fan speed values from the raw data.

        Returns:
            A list of 4 fan speed values in RPM, or None for invalid values
        """
        speeds = []
        for index in [QuadroConstants.FAN_SPEED_1, QuadroConstants.FAN_SPEED_2, 
                     QuadroConstants.FAN_SPEED_3, QuadroConstants.FAN_SPEED_4]:
            value = self.get_converted_value(index)
            speeds.append(value if value is not None else None)
        return speeds

    def parse_fan_currents(self) -> List[Optional[float]]:
        """Parse the fan current values from the raw data.

        Returns:
            A list of 4 fan current values in Amperes, or None for invalid values
        """
        currents = []
        for index in [QuadroConstants.FAN_CURRENT_1, QuadroConstants.FAN_CURRENT_2, 
                     QuadroConstants.FAN_CURRENT_3, QuadroConstants.FAN_CURRENT_4]:
            value = self.get_converted_value(index)
            currents.append(value / 1000.0 if value is not None else None)
        return currents



if __name__ == '__main__':
    print("Quadro device test")

    # Get the singleton instance
    manager = QuadroManager.get_instance()

    # Get and print temperature values (will return None values if device is not connected)
    temps = manager.temperatures
    print(f"Temperatures: {temps}") if None not in temps else print("Device not connected or not responding.")

    # Get and print fan speed values (will return None values if device is not connected)
    speeds = manager.fan_speeds
    print(f"Fan speeds: {speeds}") if None not in speeds else print("Device not connected or not responding.")

    # Get and print fan current values (will return None values if device is not connected)
    currents = manager.fan_currents
    print(f"Fan currents: {currents}") if None not in currents else print("Device not connected or not responding.")
