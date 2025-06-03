
"""
CSV Logger module for Glutaugenpilz
Provides functionality to log test values to a CSV file with configurable:
- Logging interval
- Set of values to log
- Column names for values
"""

import csv
import os
import time
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional


class CSVLogger:
    """
    A class to handle logging of test values to a CSV file.
    """
    
    def __init__(self, 
                 filename: Optional[str] = None,
                 logging_interval: float = 1.0,
                 value_sources: Optional[Dict[str, Callable[[], Any]]] = None,
                 column_names: Optional[List[str]] = None):
        """
        Initialize the CSV Logger.
        
        Args:
            filename: Name of the CSV file to log to. If None, a default name with timestamp will be used.
            logging_interval: Interval in seconds between log entries.
            value_sources: Dictionary mapping column names to functions that return the values to log.
                           If None, an empty dictionary will be used.
            column_names: List of column names to use in the CSV file. If None, the keys from value_sources will be used.
        """
        # Set default filename if none provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"glutaugenpilz_log_{timestamp}.csv"
        
        self.filename = filename
        self.logging_interval = logging_interval
        self.value_sources = value_sources or {}
        self.column_names = column_names or list(self.value_sources.keys())
        self.last_log_time = 0
        self.file_created = False
        
    def add_value_source(self, name: str, source_function: Callable[[], Any]) -> None:
        """
        Add a new value source to log.
        
        Args:
            name: Name of the value (will be used as column name if not overridden)
            source_function: Function that returns the value to log
        """
        self.value_sources[name] = source_function
        if name not in self.column_names:
            self.column_names.append(name)
            
    def set_column_names(self, column_names: List[str]) -> None:
        """
        Set custom column names for the CSV file.
        
        Args:
            column_names: List of column names to use
        """
        self.column_names = column_names
        
    def set_logging_interval(self, interval: float) -> None:
        """
        Set the logging interval.
        
        Args:
            interval: Interval in seconds between log entries
        """
        self.logging_interval = interval
        
    def _create_file_if_needed(self) -> None:
        """
        Create the CSV file and write the header if it doesn't exist yet.
        """
        if not self.file_created:
            file_exists = os.path.exists(self.filename)
            
            with open(self.filename, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header if file is new
                if not file_exists:
                    # Add timestamp column at the beginning
                    header = ['Timestamp'] + self.column_names
                    writer.writerow(header)
            
            self.file_created = True
            print(f"CSV log file created: {self.filename}")
            
    def log_values(self, force: bool = False) -> bool:
        """
        Log current values to the CSV file if the logging interval has elapsed.
        
        Args:
            force: If True, log regardless of the elapsed time since the last log
            
        Returns:
            True if values were logged, False otherwise
        """
        current_time = time.time()
        
        # Check if it's time to log
        if not force and (current_time - self.last_log_time) < self.logging_interval:
            return False
            
        self._create_file_if_needed()
        
        # Get current values from all sources
        values = {}
        for name, source_func in self.value_sources.items():
            try:
                values[name] = source_func()
            except Exception as e:
                values[name] = f"ERROR: {str(e)}"
                
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Write values to CSV
        with open(self.filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Create row with timestamp and values in the correct order
            row = [timestamp]
            for column in self.column_names:
                row.append(values.get(column, "N/A"))
                
            writer.writerow(row)
            
        self.last_log_time = current_time
        return True