#!/usr/bin/env python3
"""
Generate security metrics for AutoTaskTracker.

Tracks security findings over time and generates reports.
"""
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def run_semgrep() -> Dict[str, Any]:
    """Run Semgrep and return findings count."""
    try:
        subprocess.run(
            ["semgrep", "--config=.semgrep.yml", "autotasktracker/", "--json", "-o", "temp-semgrep.json"],
            capture_output=True,
            text=True
        )
        
        with open("temp-semgrep.json", "r") as f:
            data = json.load(f)
        
        Path("temp-semgrep.json").unlink()
        
        # Group by check_id
        findings = {}
        for result in data.get("results", []):
            check_id = result["check_id"]
            findings[check_id] = findings.get(check_id, 0) + 1
            
        return findings
    except Exception as e:
        print(f"Semgrep error: {e}")
        return {}


def run_bandit() -> Dict[str, Any]:
    """Run Bandit and return findings count."""
    try:
        subprocess.run(
            ["bandit", "-r", "autotasktracker/", "-f", "json", "-o", "temp-bandit.json"],
            capture_output=True,
            text=True
        )
        
        with open("temp-bandit.json", "r") as f:
            data = json.load(f)
        
        Path("temp-bandit.json").unlink()
        
        # Group by severity
        findings = {
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for result in data.get("results", []):
            severity = result["issue_severity"].lower()
            findings[severity] += 1
            
        return findings
    except Exception as e:
        print(f"Bandit error: {e}")
        return {}


def generate_metrics() -> Dict[str, Any]:
    """Generate comprehensive security metrics."""
    print("🔍 Running security scans...")
    
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "semgrep": run_semgrep(),
        "bandit": run_bandit(),
        "summary": {
            "total_findings": 0,
            "critical_findings": 0,
            "trends": []
        }
    }
    
    # Calculate totals
    metrics["summary"]["total_findings"] = (
        sum(metrics["semgrep"].values()) +
        sum(metrics["bandit"].values())
    )
    
    metrics["summary"]["critical_findings"] = metrics["bandit"].get("high", 0)
    
    return metrics


def save_metrics(metrics: Dict[str, Any]):
    """Save metrics to file."""
    metrics_dir = Path("security-reports")
    metrics_dir.mkdir(exist_ok=True)
    
    filename = f"security_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = metrics_dir / filename
    
    with open(filepath, "w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"✅ Metrics saved to {filepath}")
    
    # Also save as latest
    latest_path = metrics_dir / "latest_metrics.json"
    with open(latest_path, "w") as f:
        json.dump(metrics, f, indent=2)


def print_summary(metrics: Dict[str, Any]):
    """Print metrics summary."""
    print("\n📊 Security Metrics Summary")
    print("=" * 40)
    print(f"Timestamp: {metrics['timestamp']}")
    print(f"Total findings: {metrics['summary']['total_findings']}")
    print(f"Critical findings: {metrics['summary']['critical_findings']}")
    
    print("\nSemgrep findings:")
    for check_id, count in metrics["semgrep"].items():
        print(f"  - {check_id}: {count}")
    
    print("\nBandit findings:")
    for severity, count in metrics["bandit"].items():
        print(f"  - {severity}: {count}")
    
    print("\n✅ Use 'make security-check' for detailed analysis")


def main():
    """Main entry point."""
    metrics = generate_metrics()
    save_metrics(metrics)
    print_summary(metrics)


if __name__ == "__main__":
    main()