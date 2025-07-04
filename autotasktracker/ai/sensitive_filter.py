"""
Sensitive data filtering for VLM processing.
Detects and redacts sensitive information in screenshots before processing.
"""
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import numpy as np

logger = logging.getLogger(__name__)


class SensitiveDataFilter:
    """Filter for detecting and handling sensitive information in screenshots."""
    
    def __init__(self):
        # Regex patterns for sensitive data
        self.patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
            'ssn': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
            'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            'api_key': re.compile(r'\b[A-Za-z0-9]{32,}\b'),
            'password_field': re.compile(r'password[:\s]*[^\s\n]+', re.IGNORECASE),
            'token': re.compile(r'\b(bearer|token|jwt)[:\s]+[A-Za-z0-9._-]+', re.IGNORECASE),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'mac_address': re.compile(r'\b[0-9A-Fa-f]{2}[:-]?[0-9A-Fa-f]{2}[:-]?[0-9A-Fa-f]{2}[:-]?[0-9A-Fa-f]{2}[:-]?[0-9A-Fa-f]{2}[:-]?[0-9A-Fa-f]{2}\b'),
        }
        
        # Keywords that indicate sensitive content
        self.sensitive_keywords = {
            'authentication': ['password', 'login', 'signin', 'auth', 'credentials'],
            'personal': ['social security', 'ssn', 'birth date', 'birthday'],
            'financial': ['bank account', 'routing number', 'card number', 'cvv', 'security code'],
            'medical': ['medical record', 'patient id', 'diagnosis', 'prescription'],
            'confidential': ['confidential', 'secret', 'private', 'classified'],
        }
        
        # Window titles that might contain sensitive data
        self.sensitive_windows = [
            'password manager', 'keychain', '1password', 'lastpass', 'bitwarden',
            'banking', 'paypal', 'venmo', 'financial', 'tax',
            'medical', 'health', 'doctor', 'patient',
            'vpn', 'ssh', 'terminal', 'admin',
        ]
    
    def scan_text_for_sensitive_data(self, text: str) -> Dict[str, List[str]]:
        """Scan text for sensitive data patterns."""
        if not text:
            return {}
        
        found_patterns = {}
        text_lower = text.lower()
        
        # Check regex patterns
        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(text)
            if matches:
                found_patterns[pattern_name] = matches
        
        # Check sensitive keywords
        for category, keywords in self.sensitive_keywords.items():
            found_keywords = [kw for kw in keywords if kw in text_lower]
            if found_keywords:
                found_patterns[f'{category}_keywords'] = found_keywords
        
        return found_patterns
    
    def is_window_sensitive(self, window_title: str) -> bool:
        """Check if window title indicates sensitive content."""
        if not window_title:
            return False
        
        window_lower = window_title.lower()
        return any(sensitive in window_lower for sensitive in self.sensitive_windows)
    
    def calculate_sensitivity_score(self, text: str, window_title: str = None) -> float:
        """Calculate a sensitivity score (0-1) for the content."""
        score = 0.0
        
        # Text-based scoring
        if text:
            sensitive_data = self.scan_text_for_sensitive_data(text)
            
            # Weight different types of sensitive data (updated thresholds)
            weights = {
                'email': 0.4,  # Increased - emails often contain sensitive info
                'phone': 0.5,
                'ssn': 0.9,
                'credit_card': 0.9,
                'api_key': 0.8,  # Increased - API keys are very sensitive
                'password_field': 0.9,  # Increased - passwords are critical
                'token': 0.8,  # Increased - tokens are sensitive
                'ip_address': 0.3,  # Increased - can be identifying
                'mac_address': 0.3,  # Increased - hardware identifiers
                'authentication_keywords': 0.7,  # Increased
                'personal_keywords': 0.6,  # Increased
                'financial_keywords': 0.8,  # Increased - banking is very sensitive
                'medical_keywords': 0.8,
                'confidential_keywords': 0.7,  # Increased
            }
            
            for pattern_type, matches in sensitive_data.items():
                weight = weights.get(pattern_type, 0.3)
                # Score increases with number of matches, but caps at weight
                pattern_score = min(weight, len(matches) * weight / 3)
                score += pattern_score
        
        # Window-based scoring (improved)
        if window_title and self.is_window_sensitive(window_title):
            # Higher score for clearly sensitive windows
            window_lower = window_title.lower()
            if any(keyword in window_lower for keyword in ['password', 'banking', 'financial', 'medical']):
                score += 0.6  # High sensitivity windows
            else:
                score += 0.4  # Medium sensitivity windows
        
        return min(1.0, score)
    
    def should_process_image(self, image_path: str, window_title: str = None, 
                           ocr_text: str = None, threshold: float = 0.5) -> Tuple[bool, float, Dict]:
        """Determine if image should be processed based on sensitivity."""
        sensitivity_score = self.calculate_sensitivity_score(ocr_text or "", window_title)
        
        # Get detailed scan results for logging
        scan_results = {}
        if ocr_text:
            scan_results['text_patterns'] = self.scan_text_for_sensitive_data(ocr_text)
        if window_title:
            scan_results['sensitive_window'] = self.is_window_sensitive(window_title)
        
        should_process = sensitivity_score < threshold
        
        if not should_process:
            logger.warning(f"Skipping sensitive content: {image_path} (score: {sensitivity_score:.2f})")
        
        return should_process, sensitivity_score, scan_results
    
    def get_privacy_safe_prompt(self, app_type: str) -> str:
        """Get privacy-safe prompts that avoid requesting sensitive details."""
        privacy_safe_prompts = {
            'IDE': "Describe the development activity: programming language, general code structure, and development task type (no specific code content)",
            'Terminal': "Describe the terminal activity: type of commands being run and general task category (no specific commands or output)",
            'Browser': "Describe the web browsing activity: type of website, general content category, and browsing task (no specific URLs or content)",
            'Meeting': "Describe the meeting activity: platform being used, meeting type, and general context (no participant details)",
            'Document': "Describe the document activity: document type, general editing task, and content category (no specific document content)",
            'Chat': "Describe the communication activity: platform type, communication context, and general topic area (no specific messages)",
            'Default': "Describe the general computer activity: application category, task type, and work context (no specific details or content)"
        }
        
        return privacy_safe_prompts.get(app_type, privacy_safe_prompts['Default'])


# Global filter instance
_sensitive_filter = SensitiveDataFilter()


def get_sensitive_filter() -> SensitiveDataFilter:
    """Get the global sensitive data filter instance."""
    return _sensitive_filter