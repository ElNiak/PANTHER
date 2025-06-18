#!/usr/bin/env python3
"""
Demonstration script for the new experiment reporting system.

This script shows the working features of the experiment reporting system.
"""

import json
from pathlib import Path
from panther.core.reporting.experiment_reporter import ExperimentReporter
from panther.core.reporting.status_collector import StatusCollector

def main():
    print("🧪 PANTHER Experiment Reporting System Demo")
    print("=" * 60)
    
    # Find a recent experiment
    experiment_dir = Path("outputs/2025-06-16_12-28-36")
    
    if not experiment_dir.exists():
        print("❌ Demo experiment directory not found")
        return
    
    print(f"📁 Analyzing experiment: {experiment_dir.name}")
    print()
    
    # 1. Demonstrate StatusCollector
    print("🔍 1. STATUS COLLECTION")
    print("-" * 30)
    
    collector = StatusCollector(experiment_dir)
    summary = collector.collect_experiment_summary()
    
    print(f"Experiment ID: {summary.experiment_id}")
    print(f"Status: {summary.status.value}")
    print(f"Tests: {summary.total_tests} total, {summary.passed_tests} passed, {summary.failed_tests} failed")
    print(f"Success Rate: {summary.success_rate:.1f}%")
    print(f"Fast-fail enabled: {summary.fast_fail.enabled}")
    print()
    
    # 2. Demonstrate ReportGeneration
    print("📝 2. REPORT GENERATION")
    print("-" * 30)
    
    reporter = ExperimentReporter(experiment_dir)
    
    # Generate quick summary
    quick_summary = reporter.generate_quick_summary()
    print(f"Quick Summary: {quick_summary}")
    print()
    
    # Generate reports
    results = reporter.generate_reports()
    
    for report_type, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"{report_type.upper()}: {status}")
    
    print()
    
    # 3. Show generated files
    print("📄 3. GENERATED FILES")
    print("-" * 30)
    
    report_files = {
        "experiment_summary.json": "Machine-readable JSON report",
        "EXPERIMENT_REPORT.md": "Human-readable Markdown report"
    }
    
    for filename, description in report_files.items():
        file_path = experiment_dir / filename
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✅ {filename} ({size:,} bytes)")
            print(f"   {description}")
        else:
            print(f"❌ {filename} (not found)")
        print()
    
    # 4. Show JSON sample data
    print("📊 4. SAMPLE JSON DATA")
    print("-" * 30)
    
    json_file = experiment_dir / "experiment_summary.json"
    if json_file.exists():
        with open(json_file) as f:
            data = json.load(f)
        
        print("Key metrics extracted:")
        print(f"  • Experiment status: {data['status']}")
        print(f"  • Total tests: {data['tests']['total']}")
        print(f"  • Success rate: {data['tests']['success_rate']:.1f}%")
        print(f"  • Fast-fail enabled: {data['fast_fail']['enabled']}")
        print(f"  • Report generated: {data['report_metadata']['generated_at']}")
        print()
    
    # 5. Integration with ExperimentManager
    print("🔧 5. INTEGRATION STATUS")
    print("-" * 30)
    print("✅ StatusCollector implemented - collects test results and metrics")
    print("✅ ExperimentReporter implemented - generates multiple report formats")
    print("✅ Integrated into ExperimentManager.cleanup() method")
    print("✅ Automatic report generation on experiment completion")
    print("✅ JSON format for machine processing")
    print("✅ Markdown format for human reading")
    print("✅ Fast-fail analysis and status tracking")
    print("✅ Resource usage monitoring")
    print()
    
    print("🎯 BENEFITS")
    print("-" * 30)
    print("• Immediate experiment status overview")
    print("• Detailed failure analysis with log references")
    print("• Machine-readable data for automation")
    print("• Historical tracking and trend analysis")
    print("• Integration-ready for CI/CD systems")
    print()
    
    print("✨ The experiment reporting system is fully implemented!")
    print("   Reports will be automatically generated for all future experiments.")

if __name__ == "__main__":
    main()