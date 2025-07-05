# AutoTaskTracker Makefile
# Convenience commands for development and security

.PHONY: help install test security-check health-check clean

help:
	@echo "AutoTaskTracker Development Commands:"
	@echo "  make install        - Install dependencies and setup development environment"
	@echo "  make test          - Run all tests"
	@echo "  make security-check - Run security scans (AI code validation)"
	@echo "  make health-check  - Run health tests"
	@echo "  make clean         - Clean temporary files and caches"
	@echo ""
	@echo "Security Commands:"
	@echo "  make scan-code     - Run Semgrep AI-specific rules"
	@echo "  make scan-deps     - Validate dependencies for security"
	@echo "  make scan-dashboards - Test dashboard security (requires running dashboards)"

install:
	pip install -r requirements.txt
	pip install -e .
	@echo "✅ Installation complete"

test:
	pytest tests/ -v

# Primary security check command
security-check: scan-code scan-deps
	@echo "✅ Security check complete"

# Individual security scans
scan-code:
	@echo "🔍 Running AI-specific security scans..."
	-semgrep --config=.semgrep.yml autotasktracker/ --quiet || echo "⚠️  Semgrep not available"
	bandit -r autotasktracker/ --exclude=tests,venv,__pycache__ --severity-level medium -f json -o bandit-report.json
	@echo "✅ Code scanning complete"

scan-deps:
	@echo "🔍 Validating dependencies..."
	pip-audit
	safety check --policy-file .safety-policy.json
	python scripts/security/package_validator.py --requirements requirements.txt
	@echo "✅ Dependency validation complete"

scan-dashboards:
	@echo "🔍 Testing dashboard security..."
	python scripts/security/dashboard_security_tester.py --all
	@echo "✅ Dashboard security test complete"

# Security metrics and monitoring
security-metrics:
	@echo "📊 Generating security metrics..."
	python scripts/security/security_metrics.py

# Technical debt monitoring
complexity-check:
	@echo "📈 Monitoring code complexity..."
	python scripts/monitor_complexity.py

debt-analysis:
	@echo "🔍 Running comprehensive technical debt analysis..."
	make complexity-check
	make security-metrics
	@echo "✅ Technical debt analysis complete - check reports/ directories"

# Health checks
health-check:
	@echo "🏥 Running health tests..."
	pytest tests/health/test_metatesting_security.py -v
	pytest tests/health/code_quality/ -v
	pytest tests/health/database/ -v
	@echo "✅ Health check complete"

# Quick AI code check for pre-commit
pre-commit-check:
	@echo "🚀 Quick pre-commit security check..."
	semgrep --config=.semgrep.yml autotasktracker/ --quiet --error
	python scripts/security/pre_install_hook.py --requirements requirements.txt --strict
	@echo "✅ Pre-commit check passed"

# Clean temporary files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	@echo "✅ Cleanup complete"

# Development helpers
format:
	black autotasktracker/
	isort autotasktracker/

lint:
	flake8 autotasktracker/
	
# Run all quality checks
quality: format lint security-check health-check
	@echo "✅ All quality checks passed!"

# CI simulation - run what CI would run
ci-local:
	@echo "🤖 Simulating CI pipeline..."
	make install
	make security-check
	make health-check
	make test
	@echo "✅ CI simulation complete - ready to push!"