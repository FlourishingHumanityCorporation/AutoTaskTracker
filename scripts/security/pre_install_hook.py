#!/usr/bin/env python3
"""
Pre-installation hook for AutoTaskTracker dependency management.
Validates packages before installation to prevent slopsquatting attacks.

Usage:
    # As a pre-commit hook
    python scripts/security/pre_install_hook.py --requirements requirements.txt
    
    # Before pip install
    python scripts/security/pre_install_hook.py --package some-new-package
"""

import json
import sys
from pathlib import Path
from package_validator import PackageValidator


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Pre-installation security validation")
    parser.add_argument("--package", help="Validate single package before install")
    parser.add_argument("--requirements", help="Validate requirements file")
    parser.add_argument("--strict", action="store_true", 
                       help="Fail on any suspicious packages (default: fail only on high-risk)")
    
    args = parser.parse_args()
    
    validator = PackageValidator()
    
    if args.package:
        print(f"🔍 Validating package: {args.package}")
        result = validator.validate_package(args.package)
        
        if not result["is_legitimate"]:
            print(f"⚠️  SUSPICIOUS PACKAGE: {args.package}")
            print(f"   Risk Score: {result['risk_score']}/10")
            for warning in result["warnings"]:
                print(f"   - {warning}")
                
            if args.strict or result["risk_score"] >= 8.0:
                print(f"\n❌ Installation blocked for security reasons")
                sys.exit(1)
            else:
                print(f"\n⚠️  Proceeding with caution (use --strict to block)")
        else:
            print(f"✅ Package appears legitimate")
            
    elif args.requirements:
        print(f"🔍 Validating requirements file: {args.requirements}")
        results = validator.validate_requirements_file(args.requirements)
        
        if "error" in results:
            print(f"❌ Validation error: {results['error']}")
            sys.exit(1)
            
        print(f"📊 Results: {results['legitimate_packages']}/{results['total_packages']} packages legitimate")
        
        if results["suspicious_packages"]:
            print(f"\n⚠️  Suspicious packages found:")
            for validation in results["validation_results"]:
                if not validation["is_legitimate"]:
                    pkg = validation["package_name"]
                    risk = validation["risk_score"]
                    print(f"   - {pkg} (risk: {risk}/10)")
                    
        if results["high_risk_packages"]:
            print(f"\n❌ High-risk packages that should be blocked:")
            for pkg in results["high_risk_packages"]:
                print(f"   - {pkg}")
                
        # Determine exit code
        if results["high_risk_packages"]:
            print(f"\n❌ Installation blocked due to high-risk packages")
            sys.exit(1)
        elif args.strict and results["suspicious_packages"]:
            print(f"\n❌ Installation blocked due to suspicious packages (strict mode)")
            sys.exit(1)
        else:
            print(f"\n✅ Validation passed")
            
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()