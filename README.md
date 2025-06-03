# Glutaugenpilz-win
Glutaugenpilz measures a CPU cooler’s max sustained heat dissipation. For AMD CPUs.

## Features
- Measures CPU cooler's maximum sustained heat dissipation
- Controls CPU PPT (Package Power Tracking) limits using ZenStates
- Monitors CPU temperature and power consumption
- Integrates with Prime95 for CPU stress testing

## Requirements
- Windows operating system
- AMD Ryzen CPU
- Administrative privileges
- Prime95 (for stress testing)

## Setup
1. Clone this repository
2. Download Prime95 from https://www.mersenne.org/download/
3. Extract Prime95 to `External\Prime95` directory in the project
4. Run Glutaugenpilz.py with administrative privileges

## Usage
The script will:
1. Start a Prime95 torture test to stress the CPU
2. Monitor CPU temperature and power consumption
3. Stop the torture test when you press Ctrl+C