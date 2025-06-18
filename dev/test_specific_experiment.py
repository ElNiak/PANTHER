#!/usr/bin/env python3
"""
Test script for a specific experiment.
"""

import sys
from pathlib import Path

# Add panther to path
sys.path.insert(0, str(Path(__file__).parent))

from panther.core.reporting.experiment_reporter import ExperimentReporter

def main():
    experiment_dir = Path("outputs/2025-06-16_12-28-36")
    
    if not experiment_dir.exists():
        print("Experiment directory not found")
        return
    
    reporter = ExperimentReporter(experiment_dir)
    results = reporter.generate_reports()
    
    print("Report generation results:")
    for report_type, success in results.items():
        print(f"  {report_type}: {'✅' if success else '❌'}")

if __name__ == "__main__":
    main()