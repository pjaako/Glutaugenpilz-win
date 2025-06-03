"""
Messages module for Glutaugenpilz
Contains all user-facing messages used in the application
"""
import os
import sys

# Initialize Windows console for ANSI color support if on Windows
if sys.platform.startswith('win'):
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass  # If it fails, colors might not work, but the program will continue

# Error and status messages
ZENSTATES_INIT_FAILED = [
    "Failed to initialize ZenStates.Core. Make sure it is installed in the External/ZenStates-Core directory.",
    "You can download ZenStates-Core from: https://github.com/irusanov/ZenStates-Core",
    "Makes no sense to continue without ZenStates.Core. Press any key to exit..."
]

PRIME95_INIT_FAILED = [
    "Failed to initialize Prime95. No CPU stress-test will be performed.",
    "It is OK if you loading the CPU with another tool externally.",
    "Otherwise, the result won't make any sense"
]

CSV_LOGGING_DISABLED = [
    "CSV logging is disabled. No CSV file will be created.",
    "You can nevertheless observe the progress of the test in the console."
]

PRIME95_START_FAILED = [
    "Failed to start Prime95 torture test. Make sure Prime95 is installed in the External/Prime95 directory.",
    "You can download Prime95 from: https://www.mersenne.org/download/"
]

ADMIN_REQUIRED = [
    "This program requires administrative privileges."
]

def display_message(message_lines, is_error=False, exit_after=False):
    """Display a formatted message to the user.

    Args:
        message_lines: List of message lines to display
        is_error: Whether this is an error message
        exit_after: Whether to prompt for input and exit after displaying the message
    """
    # ANSI escape codes for colors
    RED = '\033[91m'
    RESET = '\033[0m'

    print("\n\n")  # Add spacing
    for line in message_lines:
        if is_error:
            print(f"{RED}{line}{RESET}")
        else:
            print(line)

    if exit_after:
        input("Press any key to exit...")
        import sys
        sys.exit(1)
