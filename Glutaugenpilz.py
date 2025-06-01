"""
Glutaugenpilz 0.1 by pjaako
Glutaugenpilz measures a CPU cooler’s max sustained heat dissipation in the following way:
It manipulates the CPUs PPT limit and then measures the stabilized temperature of the CPU
under a heavy load that makes sure the CPU is working at PPT. Current package power is tracked as well.
If the temperature stabilizes at a value below a given threshold, the CPU cooler is able to dissipate more heat than
the CPU is producing. Then the PPT limit is increased and the test is repeated.
If the temperature stays above the threshold for a given time, the CPU cooler is not able to dissipate all 
the heat produced by the CPU. The PPT limit is decreased and the test is repeated.
At the end of the test, the sweet spot package power is found where the CPU temperature is slightly below the threshold.
Given that Package power directly correlates with steady state temperature, optimum can be found with fewer steps 
Use a binary search or similar algorithm.
The script relies on ZenStates Core to manipulate the PPT limit and therefore is suitable for AMD Ryzen CPUs only.
"""

import os
import sys
import subprocess
import time
from time import sleep
from quadro import QuadroManager
from zenstates import ZenStatesManager
from elevator import is_admin, elevate

if __name__ == "__main__":
    if not is_admin():
        print("This program requires administrative privileges.")
        elevate()
        sys.exit(0)

    # Get temperatures from Quadro device
    temps = QuadroManager.get_instance().temperatures
    if None not in temps:
        print(f"Temps from QuadroManager: {temps}")
    else:
        print("No Quadro device connected")

    # Get ZenStatesManager instance
    manager = ZenStatesManager.get_instance()

    # Get current PPT limit
    ppt = manager.ppt_limit
    if ppt is not None:
        print(f"Current PPT limit: {ppt}W")
    else:
        print("Error getting PPT limit")
        sys.exit(1)

    # Set PPT limit to 222W using the property setter
    try:
        manager.ppt_limit = 222
        print("PPT limit set successfully")
    except ValueError as e:
        print(f"Error setting PPT limit: {e}")
        sys.exit(1)

    # Monitor package power and current PPT
    try:
        while True:
            # Get package power (actual power consumption)
            power = manager.package_power

            # Get current PPT value (same as package power)
            current_ppt = manager.current_ppt

            # Get PPT limit
            ppt_limit = manager.ppt_limit

            if power is not None and current_ppt is not None and ppt_limit is not None:
                print(f"Package Power: {power}W | Current PPT: {current_ppt}W | PPT Limit: {ppt_limit}W")

                # Calculate percentage of PPT limit being used
                ppt_usage_percent = (current_ppt / ppt_limit) * 100
                print(f"PPT Usage: {ppt_usage_percent:.1f}%")
            else:
                print("Error getting power values")


            sleep(1)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")

    # Wait for user input before exiting
    input("Press any key to exit...")
    sys.exit(0)
