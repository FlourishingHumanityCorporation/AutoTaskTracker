#!/usr/bin/env python3
"""
Package Legitimacy Validator for AutoTaskTracker
Protects against slopsquatting attacks by validating package legitimacy.

Based on meta-testing best practices for AI-generated code security.
"""

import json
import logging
import re
import requests
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PackageValidator:
    """Validates package legitimacy to prevent slopsquatting attacks."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".autotask_package_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.suspicious_patterns = [
            r'.*-?db$',  # Common AI hallucination pattern (e.g., "orango-db")
            r'.*-?client$',  # AI often suggests generic clients
            r'.*-?api$',  # Generic API packages
            r'auto.*',  # AI loves "auto" prefixes
            r'.*-?helper$',  # Generic helper libraries
            r'.*-?utils$',  # Generic utilities
        ]
        
    def validate_package(self, package_name: str, index: str = "pypi") -> Dict:
        """
        Validate a package's legitimacy.
        
        Returns:
            Dict with validation results including:
            - is_legitimate: bool
            - risk_score: float (0-10)
            - warnings: List[str]
            - metadata: Dict
        """
        result = {
            "package_name": package_name,
            "is_legitimate": False,
            "risk_score": 0.0,
            "warnings": [],
            "metadata": {},
            "checked_at": datetime.now().isoformat()
        }
        
        try:
            # Check if package exists
            if index == "pypi":
                metadata = self._get_pypi_metadata(package_name)
            else:
                raise ValueError(f"Unsupported package index: {index}")
                
            if not metadata:
                result["warnings"].append("Package does not exist")
                result["risk_score"] = 10.0
                return result
                
            result["metadata"] = metadata
            
            # Perform legitimacy checks
            risk_factors = []
            
            # Check 1: Age and download count
            age_risk = self._check_package_age(metadata)
            if age_risk > 0:
                risk_factors.append(f"Package age risk: {age_risk}/10")
                
            # Check 2: Download popularity
            download_risk = self._check_download_count(metadata)
            if download_risk > 0:
                risk_factors.append(f"Low download count risk: {download_risk}/10")
                
            # Check 3: Maintainer reputation
            maintainer_risk = self._check_maintainer_reputation(metadata)
            if maintainer_risk > 0:
                risk_factors.append(f"Maintainer reputation risk: {maintainer_risk}/10")
                
            # Check 4: Suspicious naming patterns
            naming_risk = self._check_suspicious_naming(package_name)
            if naming_risk > 0:
                risk_factors.append(f"Suspicious naming pattern: {naming_risk}/10")
                
            # Check 5: Typosquatting similarity
            typo_risk = self._check_typosquatting(package_name)
            if typo_risk > 0:
                risk_factors.append(f"Possible typosquatting: {typo_risk}/10")
                
            # Calculate overall risk score
            total_risk = age_risk + download_risk + maintainer_risk + naming_risk + typo_risk
            result["risk_score"] = min(total_risk, 10.0)
            result["warnings"] = risk_factors
            
            # Determine legitimacy threshold
            result["is_legitimate"] = result["risk_score"] < 7.0
            
            logger.info(f"Package {package_name}: risk={result['risk_score']:.1f}, legitimate={result['is_legitimate']}")
            
        except Exception as e:
            logger.error(f"Error validating package {package_name}: {e}")
            result["warnings"].append(f"Validation error: {str(e)}")
            result["risk_score"] = 5.0  # Moderate risk for unknown packages
            
        return result
        
    def _get_pypi_metadata(self, package_name: str) -> Optional[Dict]:
        """Get package metadata from PyPI."""
        cache_file = self.cache_dir / f"{package_name}.json"
        
        # Check cache (valid for 24 hours)
        if cache_file.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age < timedelta(hours=24):
                try:
                    return json.loads(cache_file.read_text())
                except (json.JSONDecodeError, OSError):
                    pass
                    
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            metadata = response.json()
            
            # Cache the result
            cache_file.write_text(json.dumps(metadata, indent=2))
            return metadata
            
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch metadata for {package_name}: {e}")
            return None
            
    def _check_package_age(self, metadata: Dict) -> float:
        """Check package age risk (newer = higher risk)."""
        try:
            upload_time = metadata["info"]["upload_time"]
            if upload_time:
                upload_date = datetime.fromisoformat(upload_time.replace('Z', '+00:00'))
                age_days = (datetime.now() - upload_date.replace(tzinfo=None)).days
                
                if age_days < 7:
                    return 8.0  # Very new packages are high risk
                elif age_days < 30:
                    return 5.0  # Recent packages are moderate risk
                elif age_days < 90:
                    return 2.0  # Somewhat new packages are low risk
                else:
                    return 0.0  # Established packages are low risk
                    
        except (KeyError, ValueError, TypeError):
            pass
            
        return 3.0  # Unknown age = moderate risk
        
    def _check_download_count(self, metadata: Dict) -> float:
        """Check download count risk (fewer downloads = higher risk)."""
        # Note: PyPI doesn't provide download stats in the JSON API
        # This would need to be enhanced with pypistats or similar
        return 0.0
        
    def _check_maintainer_reputation(self, metadata: Dict) -> float:
        """Check maintainer reputation risk."""
        try:
            author = metadata["info"].get("author", "")
            author_email = metadata["info"].get("author_email", "")
            
            # Check for suspicious patterns
            if not author or not author_email:
                return 4.0
                
            # Check for throwaway email patterns
            throwaway_patterns = [
                r'.*@(gmail|yahoo|hotmail|outlook)\.com',
                r'.*temp.*',
                r'.*test.*',
                r'.*fake.*'
            ]
            
            for pattern in throwaway_patterns:
                if re.match(pattern, author_email.lower()):
                    return 3.0
                    
        except (KeyError, TypeError):
            return 4.0
            
        return 0.0
        
    def _check_suspicious_naming(self, package_name: str) -> float:
        """Check for suspicious naming patterns common in AI hallucinations."""
        for pattern in self.suspicious_patterns:
            if re.match(pattern, package_name.lower()):
                return 6.0
                
        # Check for generic/vague names
        if len(package_name) < 3:
            return 5.0
            
        return 0.0
        
    def _check_typosquatting(self, package_name: str) -> float:
        """Check for typosquatting similarity to popular packages."""
        popular_packages = [
            "requests", "numpy", "pandas", "flask", "django", "sqlalchemy",
            "boto3", "pytest", "click", "pillow", "opencv", "tensorflow",
            "torch", "scikit-learn", "matplotlib", "seaborn", "fastapi"
        ]
        
        for popular in popular_packages:
            if self._is_similar(package_name.lower(), popular.lower()):
                return 8.0
                
        return 0.0
        
    def _is_similar(self, name1: str, name2: str) -> bool:
        """Check if two package names are suspiciously similar."""
        # Simple Levenshtein-like check
        if abs(len(name1) - len(name2)) > 2:
            return False
            
        differences = sum(c1 != c2 for c1, c2 in zip(name1, name2))
        return differences <= 2 and differences > 0
        
    def validate_requirements_file(self, requirements_path: str) -> Dict:
        """Validate all packages in a requirements file."""
        results = {
            "total_packages": 0,
            "legitimate_packages": 0,
            "suspicious_packages": [],
            "high_risk_packages": [],
            "validation_results": []
        }
        
        try:
            requirements_file = Path(requirements_path)
            if not requirements_file.exists():
                raise FileNotFoundError(f"Requirements file not found: {requirements_path}")
                
            content = requirements_file.read_text()
            packages = self._parse_requirements(content)
            
            results["total_packages"] = len(packages)
            
            for package_name in packages:
                validation = self.validate_package(package_name)
                results["validation_results"].append(validation)
                
                if validation["is_legitimate"]:
                    results["legitimate_packages"] += 1
                else:
                    results["suspicious_packages"].append(package_name)
                    
                if validation["risk_score"] >= 8.0:
                    results["high_risk_packages"].append(package_name)
                    
        except Exception as e:
            logger.error(f"Error validating requirements file: {e}")
            results["error"] = str(e)
            
        return results
        
    def _parse_requirements(self, content: str) -> List[str]:
        """Parse package names from requirements file content."""
        packages = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
                
            # Extract package name (before version specifiers)
            package_name = re.split(r'[>=<!]', line)[0].strip()
            
            # Skip local/URL packages
            if any(prefix in package_name for prefix in ['http://', 'https://', 'git+', '-e ']):
                continue
                
            if package_name:
                packages.append(package_name)
                
        return packages


def main():
    parser = argparse.ArgumentParser(description="Validate package legitimacy")
    parser.add_argument("--package", help="Single package to validate")
    parser.add_argument("--requirements", help="Requirements file to validate")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--fail-on-suspicious", action="store_true", 
                       help="Exit with non-zero code if suspicious packages found")
    
    args = parser.parse_args()
    
    validator = PackageValidator()
    
    if args.package:
        result = validator.validate_package(args.package)
        print(json.dumps(result, indent=2))
        
        if args.fail_on_suspicious and not result["is_legitimate"]:
            sys.exit(1)
            
    elif args.requirements:
        result = validator.validate_requirements_file(args.requirements)
        
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))
            
        # Print summary
        print(f"\n🔍 Package Validation Summary:")
        print(f"Total packages: {result['total_packages']}")
        print(f"Legitimate packages: {result['legitimate_packages']}")
        print(f"Suspicious packages: {len(result['suspicious_packages'])}")
        print(f"High-risk packages: {len(result['high_risk_packages'])}")
        
        if result["high_risk_packages"]:
            print(f"\n⚠️  High-risk packages found: {', '.join(result['high_risk_packages'])}")
            
        if args.fail_on_suspicious and result["suspicious_packages"]:
            sys.exit(1)
            
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()