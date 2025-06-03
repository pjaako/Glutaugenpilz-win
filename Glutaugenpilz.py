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
import argparse
from time import sleep
from quadro import QuadroManager
from zenstates import ZenStatesManager
from prime95 import Prime95Manager
from elevator import is_admin, elevate
from csv_logger import CSVLogger
from messages import display_message, ZENSTATES_INIT_FAILED, PRIME95_INIT_FAILED, CSV_LOGGING_DISABLED, PRIME95_START_FAILED, ADMIN_REQUIRED

def parse_arguments():
    """Parse command line arguments for Glutaugenpilz."""
    parser = argparse.ArgumentParser(description="Glutaugenpilz - CPU cooler heat dissipation measurement tool")

    # CSV logging options
    csv_group = parser.add_argument_group("CSV Logging Options")
    csv_group.add_argument("--csv-file", type=str, help="CSV file to log data to (default: auto-generated filename)")
    csv_group.add_argument("--log-interval", type=float, default=1.0, 
                          help="Interval in seconds between log entries (default: 1.0)")
    csv_group.add_argument("--no-csv", action="store_true", help="Disable CSV logging")

    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()

    if not is_admin():
        display_message(ADMIN_REQUIRED, is_error=True)
        elevate()
        sys.exit(0)

    quadro = QuadroManager.get_instance()
    #do we really get values from Quadro?
    if None in quadro.temperatures: quadro=None

    ryzen = ZenStatesManager.get_instance()
    #do we really get values from ryzen?
    if ryzen.temperature is None: ryzen=None

    prime95 = Prime95Manager.get_instance()
    #prime95 functional?
    if not prime95.is_functional(): prime95=None


    logger = CSVLogger(
        filename=args.csv_file,
        logging_interval=args.log_interval
    ) if not args.no_csv else None

    if ryzen is None:
        display_message(ZENSTATES_INIT_FAILED, is_error=True, exit_after=True)

    if prime95 is None:
        display_message(PRIME95_INIT_FAILED, is_error=True)

    if logger is None:
        display_message(CSV_LOGGING_DISABLED)



    if logger: logger.add_value_source("Tdie", lambda: ryzen.temperature)
    if logger: logger.add_value_source("Ppkg", lambda: ryzen.total_power)
    if logger: print (f"Logging to {logger.filename} every {logger.logging_interval} second(s)")
    input("Press any key to continue...")
    # Start Prime95 torture test
    print("Starting Prime95 torture test...")
    prime95_started = prime95.start_torture_test(test_type="Small FFTs")
    if prime95_started:
        print("Prime95 torture test started successfully.")
    else:
        display_message(PRIME95_START_FAILED, is_error=True)
    input("Press any key to continue...")

    # Monitor package power and temperature
    try:
        print("\nMonitoring CPU temperature and power...")

        while True:
            temp = ryzen.temperature
            power = ryzen.total_power

            print(f"Temperature: {temp}°C | Total power: {power}W", end="\r")

            # Log values to CSV file if logging is enabled
            if logger:
                logger.log_values()

            sleep(1.1)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        # Force one final log entry if logging is enabled
        if logger:
            logger.log_values(force=True)
    finally:
        # Stop Prime95 torture test
        if prime95_started:
            print("Stopping Prime95 torture test...")
            if prime95.stop_torture_test():
                print("Prime95 torture test stopped successfully.")
            else:
                print("Failed to stop Prime95 torture test. You may need to close it manually.")

    # Wait for user input before exiting
    input("Press any key to exit...")
    sys.exit(0)
