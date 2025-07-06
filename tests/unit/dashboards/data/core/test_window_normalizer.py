"""Unit tests for WindowTitleNormalizer."""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))))

from autotasktracker.dashboards.data.core.window_normalizer import WindowTitleNormalizer, get_window_normalizer


class TestWindowTitleNormalizer(unittest.TestCase):
    """Test cases for WindowTitleNormalizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = WindowTitleNormalizer()
    
    def test_development_patterns(self):
        """Test normalization of development application titles."""
        test_cases = [
            ("VS Code — task_board.py — AutoTaskTracker", "Code Development (task_board.py)"),
            ("Terminal — python script.py", "Terminal Work (python script.py)"),
            ("Xcode — MyApp.swift", "iOS Development (MyApp.swift)"),
        ]
        
        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = self.normalizer.normalize(input_title)
                self.assertEqual(result, expected)
    
    def test_communication_patterns(self):
        """Test normalization of communication application titles."""
        test_cases = [
            ("Gmail — Inbox (5) — paul@example.com", "Email Management"),
            ("Slack — #general", "Team Communication (#general)"),
            ("Zoom — Daily Standup", "Video Meeting (Daily Standup)"),
            ("Teams — Project Review", "Team Meeting (Project Review)"),
        ]
        
        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = self.normalizer.normalize(input_title)
                self.assertEqual(result, expected)
    
    def test_productivity_patterns(self):
        """Test normalization of productivity application titles."""
        test_cases = [
            ("Excel — budget.xlsx", "Spreadsheet Analysis (budget.xlsx)"),
            ("Word — report.docx", "Document Writing (report.docx)"),
            ("PowerPoint — presentation.pptx", "Presentation Creation (presentation.pptx)"),
            ("Notion — Project Planning", "Documentation (Project Planning)"),
        ]
        
        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = self.normalizer.normalize(input_title)
                self.assertEqual(result, expected)
    
    def test_ai_tools_patterns(self):
        """Test normalization of AI tool titles."""
        test_cases = [
            ("AutoTaskTracker — ✳ Project Premortem — claude", "Project Premortem (AI Consultation)"),
            ("ChatGPT — Conversation", "AI Research & Development"),
            ("Claude — AI Assistant", "AI Research & Development"),
        ]
        
        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = self.normalizer.normalize(input_title)
                self.assertEqual(result, expected)
    
    def test_web_browsing_patterns(self):
        """Test normalization of web browser titles."""
        test_cases = [
            ("Chrome — Stack Overflow", "Research & Problem Solving"),
            ("Chrome — GitHub", "Code Repository Management"),
            ("Safari — LinkedIn", "Professional Networking"),
        ]
        
        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = self.normalizer.normalize(input_title)
                self.assertEqual(result, expected)
    
    def test_generic_fallback(self):
        """Test generic fallback for unmatched patterns."""
        test_cases = [
            ("Chrome — some random website", "Web Research (some random website)"),
            ("Terminal — some command", "Terminal Work (some command)"),
            ("Unknown App — Some Context", "Some Context (Unknown App)"),
            ("Single Title", "Single Title"),
        ]
        
        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = self.normalizer.normalize(input_title)
                self.assertEqual(result, expected)
    
    def test_noise_removal(self):
        """Test removal of session-specific noise."""
        test_cases = [
            ("VS Code — MallocNanoZone=12345 — file.py", "Code Development (file.py)"),
            ("Terminal — command — 1920×1080", "Terminal Work (command)"),
            ("App — context — ▸ bash", "context (App)"),
            ("Project — main.py (a1b2c3d4e5f6)", "main.py (Project)"),
        ]
        
        for input_title, expected in test_cases:
            with self.subTest(input_title=input_title):
                result = self.normalizer.normalize(input_title)
                self.assertEqual(result, expected)
    
    def test_empty_and_none_inputs(self):
        """Test handling of empty and None inputs."""
        self.assertEqual(self.normalizer.normalize(""), "Unknown Activity")
        self.assertEqual(self.normalizer.normalize(None), "Unknown Activity")
        self.assertEqual(self.normalizer.normalize("   "), "Unknown Activity")
    
    def test_custom_patterns(self):
        """Test adding custom application patterns."""
        # Add a custom pattern
        self.normalizer.add_custom_pattern(
            r'MyApp.*?([^—]+)', 
            r'Custom App Work (\1)'
        )
        
        # Test the custom pattern
        result = self.normalizer.normalize("MyApp — Custom Task")
        self.assertEqual(result, "Custom App Work (Custom Task)")
    
    def test_get_patterns(self):
        """Test getting current patterns."""
        patterns = self.normalizer.get_patterns()
        self.assertIsInstance(patterns, dict)
        self.assertIn(r'VS Code.*?([^—]+\.(?:py|js|ts|jsx|tsx|html|css|sql|md))', patterns)
    
    def test_singleton_instance(self):
        """Test that get_window_normalizer returns the same instance."""
        normalizer1 = get_window_normalizer()
        normalizer2 = get_window_normalizer()
        self.assertIs(normalizer1, normalizer2)


class TestWindowNormalizerIntegration(unittest.TestCase):
    """Integration tests for window normalizer in context."""
    
    def test_realistic_scenarios(self):
        """Test realistic window title scenarios."""
        normalizer = get_window_normalizer()
        
        scenarios = [
            # Real VS Code scenarios
            ("Visual Studio Code — dashboard.py — AutoTaskTracker", "Code Development (dashboard.py)"),
            ("VS Code — README.md — my-project", "Code Development (README.md)"),
            
            # Real terminal scenarios
            ("Terminal — git status", "Terminal Work (git status)"),
            ("iTerm2 — python manage.py runserver", "Terminal Work (python manage.py runserver)"),
            
            # Real browser scenarios
            ("Google Chrome — How to implement feature X - Stack Overflow", "Research & Problem Solving"),
            ("Safari — username/repository - GitHub", "Code Repository Management"),
            
            # Real productivity scenarios
            ("Microsoft Excel — Q4-Budget-2024.xlsx", "Spreadsheet Analysis (Q4-Budget-2024.xlsx)"),
            ("Microsoft Word — Project-Report.docx", "Document Writing (Project-Report.docx)"),
        ]
        
        for input_title, expected in scenarios:
            with self.subTest(input_title=input_title):
                result = normalizer.normalize(input_title)
                self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()