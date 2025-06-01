"""
Elevator module for Windows applications
Provides functionality to check for and obtain admin privileges

author: AI Assistant
prompted by: pjaako

This module can be used by any Python script that needs to run with administrative privileges on Windows.
It provides two main functions:
- is_admin(): Check if the current process has admin privileges
- elevate(): Re-run the current script with admin privileges if it doesn't have them already

Features:
- Preserves command-line arguments when elevating privileges
- Uses Windows UAC for secure privilege elevation
- Works with any Python script regardless of how it's invoked

Example usage:
```python
from elevator import is_admin, elevate
import sys

if __name__ == "__main__":
    if not is_admin():
        print("This program requires administrative privileges.")
        elevate()  # This will re-run the script with admin rights, preserving any command-line arguments
        sys.exit(0)

    # Rest of your code that requires admin privileges
```
"""

import os
import sys
import ctypes


def is_admin():
    """Check if the current process has admin privileges.

    Uses the Windows API to determine if the current process is running with
    administrative privileges.

    Returns:
        bool: True if the process has admin privileges, False otherwise.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def elevate():
    """Re-run the current script with administrative privileges.

    This function uses the Windows API to launch a new instance of the current script
    with elevated privileges (via the UAC prompt). After launching the new instance,
    the current (non-elevated) instance will exit.

    Note:
        This function should only be called if is_admin() returns False.
        It will automatically exit the current process after launching the elevated instance.

    Raises:
        SystemExit: Always exits the current process after attempting to elevate.
        Exception: If elevation fails, an error message is printed and the process exits with code 1.
    """
    if not is_admin():
        # Get the full path to the Python interpreter in the virtual environment
        python_exe = sys.executable
        script_path = os.path.abspath(sys.argv[0])  # Use sys.argv[0] instead of __file__ for more flexibility

        # Preserve command-line arguments when elevating
        args = ' '.join([f'"{arg}"' for arg in sys.argv[1:]]) if len(sys.argv) > 1 else ''
        params = f'"{script_path}" {args}'.strip()

        try:
            # Run the script again with elevated privileges
            ctypes.windll.shell32.ShellExecuteW(
                None,  # parent window handle
                "runas",  # operation: run as admin
                python_exe,  # program
                params,  # parameters: the script path and arguments in quotes
                None,  # working directory: use default
                1  # show window normally
            )
            # Exit the non-elevated instance
            sys.exit()
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
            sys.exit(1)
