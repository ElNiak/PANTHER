#!/usr/bin/env python3
"""
Test script for experiment reporting system.

This script tests the experiment reporting functionality with existing experiment outputs.
"""

import sys
from pathlib import Path

# Add panther to path
sys.path.insert(0, str(Path(__file__).parent))

from panther.core.reporting.experiment_reporter import ExperimentReporter
from panther.core.reporting.status_collector import StatusCollector


def test_reporting_system():
    """Test the reporting system with existing experiment outputs."""
    
    # Find existing experiment directories
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        print("❌ No outputs directory found")
        return False
    
    experiment_dirs = [d for d in outputs_dir.iterdir() if d.is_dir()]
    if not experiment_dirs:
        print("❌ No experiment directories found")
        return False
    
    print(f"Found {len(experiment_dirs)} experiment directories")
    
    # Test with the most recent experiment
    latest_experiment = max(experiment_dirs, key=lambda x: x.stat().st_mtime)
    print(f"Testing with experiment: {latest_experiment.name}")
    
    try:
        # Test StatusCollector
        print("\n🔍 Testing StatusCollector...")
        collector = StatusCollector(latest_experiment)
        summary = collector.collect_experiment_summary()
        
        print(f"  ✅ Collected summary for {summary.experiment_id}")
        print(f"  📊 Status: {summary.status.value}")
        print(f"  📋 Total tests: {summary.total_tests}")
        print(f"  ✅ Passed: {summary.passed_tests}")
        print(f"  ❌ Failed: {summary.failed_tests}")
        print(f"  📈 Success rate: {summary.success_rate:.1f}%")
        
        # Test ExperimentReporter
        print("\n📝 Testing ExperimentReporter...")
        reporter = ExperimentReporter(latest_experiment)
        
        # Generate quick summary
        quick_summary = reporter.generate_quick_summary()
        if quick_summary:
            print(f"  💬 Quick summary: {quick_summary}")
        
        # Generate reports
        results = reporter.generate_reports()
        
        print(f"  📄 Report generation results:")
        for report_type, success in results.items():
            status = "✅" if success else "❌"
            print(f"    {status} {report_type}")
        
        # Check generated files
        print("\n📁 Generated files:")
        report_files = [
            "experiment_summary.json",
            "EXPERIMENT_REPORT.md",
            "experiment_summary.txt"
        ]
        
        for report_file in report_files:
            file_path = latest_experiment / report_file
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  ✅ {report_file} ({size} bytes)")
            else:
                print(f"  ❌ {report_file} (not found)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_experiments():
    """Test reporting with multiple experiment directories."""
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        return
    
    experiment_dirs = [d for d in outputs_dir.iterdir() if d.is_dir()]
    
    print(f"\n🔄 Testing multiple experiments ({len(experiment_dirs)} found)...")
    
    success_count = 0
    for exp_dir in experiment_dirs[:3]:  # Test first 3 experiments
        try:
            reporter = ExperimentReporter(exp_dir)
            quick_summary = reporter.generate_quick_summary()
            if quick_summary:
                print(f"  {exp_dir.name}: {quick_summary}")
                success_count += 1
        except Exception as e:
            print(f"  {exp_dir.name}: ❌ Error - {e}")
    
    print(f"  📊 Successfully processed {success_count}/{min(3, len(experiment_dirs))} experiments")


if __name__ == "__main__":
    print("🧪 Testing PANTHER Experiment Reporting System")
    print("=" * 50)
    
    success = test_reporting_system()
    test_multiple_experiments()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Experiment reporting system test completed successfully!")
    else:
        print("❌ Experiment reporting system test failed!")
    
    sys.exit(0 if success else 1)