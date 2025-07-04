"""
OCR enhancement module for better text extraction and analysis.
Uses OCR confidence scores and layout analysis to improve task detection.
"""
import json
import logging
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Enhanced OCR result with confidence and layout information."""
    text: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # x, y, width, height
    line_number: Optional[int] = None
    is_title: bool = False
    is_code: bool = False
    is_ui_element: bool = False


@dataclass
class OCRLayout:
    """Layout analysis results from OCR."""
    title_regions: List[OCRResult]
    code_regions: List[OCRResult]
    ui_elements: List[OCRResult]
    body_text: List[OCRResult]
    average_confidence: float
    high_confidence_ratio: float


class OCREnhancer:
    """Enhance OCR results with confidence scoring and layout analysis."""
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        
        # Patterns for identifying different text types
        self.code_patterns = [
            r'^\s*(?:def|class|function|var|let|const|if|for|while|import|from)\s',
            r'[{}\[\]();]',
            r'^\s*#.*$',  # Comments
            r'^\s*//.*$',  # Comments
            r'=>|==|!=|<=|>=',  # Operators
        ]
        
        self.ui_patterns = [
            r'^(?:File|Edit|View|Help|Tools?|Window|Debug)\s*$',
            r'^(?:OK|Cancel|Save|Open|Close|Submit|Next|Previous|Back)\s*$',
            r'^\s*\[.*\]\s*$',  # Buttons
            r'^\s*<.*>\s*$',  # UI elements
        ]
        
        self.title_indicators = {
            'position': 0.2,  # Top 20% of screen
            'font_size_ratio': 1.3,  # 30% larger than average
            'capital_ratio': 0.7,  # 70% capital letters
        }
    
    def parse_ocr_json(self, ocr_json: str) -> List[OCRResult]:
        """Parse OCR JSON results into structured format."""
        if not ocr_json:
            return []
        
        try:
            # Handle different OCR result formats
            if isinstance(ocr_json, str):
                ocr_data = json.loads(ocr_json)
            else:
                ocr_data = ocr_json
            
            results = []
            
            # RapidOCR format
            if isinstance(ocr_data, list):
                for item in ocr_data:
                    if isinstance(item, list) and len(item) >= 2:
                        # Format: [[bbox], text, confidence]
                        bbox = item[0] if len(item) > 0 else None
                        text = item[1] if len(item) > 1 else ""
                        confidence = item[2] if len(item) > 2 else 0.0
                        
                        if text and confidence > 0.5:  # Basic threshold
                            results.append(OCRResult(
                                text=text.strip(),
                                confidence=float(confidence),
                                bbox=self._parse_bbox(bbox)
                            ))
            
            # Alternative format: dict with 'results' key
            elif isinstance(ocr_data, dict) and 'results' in ocr_data:
                for result in ocr_data['results']:
                    text = result.get('text', '')
                    confidence = result.get('confidence', 0.0)
                    bbox = result.get('bbox', None)
                    
                    if text and confidence > 0.5:
                        results.append(OCRResult(
                            text=text.strip(),
                            confidence=float(confidence),
                            bbox=self._parse_bbox(bbox)
                        ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error parsing OCR JSON: {e}")
            return []
    
    def _parse_bbox(self, bbox: any) -> Optional[Tuple[int, int, int, int]]:
        """Parse bounding box into standard format."""
        if not bbox:
            return None
        
        try:
            # Handle different bbox formats
            if isinstance(bbox, list) and len(bbox) >= 4:
                if isinstance(bbox[0], list):
                    # Format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    x_coords = [p[0] for p in bbox]
                    y_coords = [p[1] for p in bbox]
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    return (x_min, y_min, x_max - x_min, y_max - y_min)
                else:
                    # Format: [x, y, width, height]
                    return tuple(bbox[:4])
            return None
        except (TypeError, ValueError, IndexError) as e:
            logger.debug(f"Error parsing bbox: {e}")
            return None
    
    def analyze_layout(self, ocr_results: List[OCRResult]) -> OCRLayout:
        """Analyze OCR results to identify layout structure."""
        if not ocr_results:
            return OCRLayout([], [], [], [], 0.0, 0.0)
        
        # Calculate statistics
        confidences = [r.confidence for r in ocr_results]
        avg_confidence = statistics.mean(confidences) if confidences else 0.0
        high_conf_ratio = len([c for c in confidences if c >= self.confidence_threshold]) / len(confidences)
        
        # Classify text regions
        title_regions = []
        code_regions = []
        ui_elements = []
        body_text = []
        
        # Determine screen dimensions for position analysis
        max_y = max((r.bbox[1] + r.bbox[3] for r in ocr_results if r.bbox), default=1000)
        
        for i, result in enumerate(ocr_results):
            result.line_number = i
            
            # Check if it's a title (position-based)
            if result.bbox and result.bbox[1] < max_y * self.title_indicators['position']:
                # Additional title checks
                if (len(result.text) < 100 and  # Not too long
                    result.confidence > self.confidence_threshold and
                    not self._is_code(result.text)):
                    result.is_title = True
                    title_regions.append(result)
                    continue
            
            # Check if it's code
            if self._is_code(result.text):
                result.is_code = True
                code_regions.append(result)
            # Check if it's a UI element
            elif self._is_ui_element(result.text):
                result.is_ui_element = True
                ui_elements.append(result)
            # Otherwise it's body text
            else:
                body_text.append(result)
        
        return OCRLayout(
            title_regions=title_regions,
            code_regions=code_regions,
            ui_elements=ui_elements,
            body_text=body_text,
            average_confidence=avg_confidence,
            high_confidence_ratio=high_conf_ratio
        )
    
    def _is_code(self, text: str) -> bool:
        """Check if text appears to be code."""
        for pattern in self.code_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Additional heuristics
        # High ratio of special characters
        special_chars = sum(1 for c in text if c in '{}[]()<>;:=+-*/%&|')
        if len(text) > 0 and special_chars / len(text) > 0.15:
            return True
        
        return False
    
    def _is_ui_element(self, text: str) -> bool:
        """Check if text appears to be a UI element."""
        text = text.strip()
        
        # Check patterns
        for pattern in self.ui_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        # Short text in specific formats
        if len(text) < 20:
            # All caps UI elements
            if text.isupper() and len(text.split()) <= 2:
                return True
            # Icon + text format
            if re.match(r'^[^\w\s]+\s*\w+', text):
                return True
        
        return False
    
    def extract_high_confidence_text(self, ocr_results: List[OCRResult], 
                                   min_confidence: Optional[float] = None) -> str:
        """Extract only high-confidence text."""
        threshold = min_confidence or self.confidence_threshold
        
        high_conf_texts = [
            result.text 
            for result in ocr_results 
            if result.confidence >= threshold
        ]
        
        return ' '.join(high_conf_texts)
    
    def get_task_relevant_text(self, layout: OCRLayout) -> str:
        """Extract text most relevant for task identification."""
        relevant_parts = []
        
        # Prioritize titles
        if layout.title_regions:
            relevant_parts.extend([r.text for r in layout.title_regions[:2]])  # Top 2 titles
        
        # Add high-confidence UI elements (might indicate actions)
        ui_texts = [r.text for r in layout.ui_elements if r.confidence > 0.8]
        if ui_texts:
            relevant_parts.extend(ui_texts[:3])  # Top 3 UI elements
        
        # Add beginning of code if present
        if layout.code_regions:
            code_preview = ' '.join([r.text for r in layout.code_regions[:3]])
            if len(code_preview) > 100:
                code_preview = code_preview[:100] + "..."
            relevant_parts.append(f"[Code: {code_preview}]")
        
        # Add high-confidence body text
        body_texts = [
            r.text for r in layout.body_text 
            if r.confidence > self.confidence_threshold and len(r.text) > 10
        ]
        if body_texts:
            relevant_parts.extend(body_texts[:2])  # Top 2 body texts
        
        return ' | '.join(relevant_parts)
    
    def enhance_task_with_ocr(self, ocr_json: str, base_task: str = None) -> Dict[str, any]:
        """
        Enhance task information using OCR analysis.
        
        Args:
            ocr_json: Raw OCR JSON from Pensieve
            base_task: Optional base task description
            
        Returns:
            Enhanced task information
        """
        ocr_results = self.parse_ocr_json(ocr_json)
        if not ocr_results:
            return {
                'task': base_task or "Activity",
                'ocr_quality': 'no_text',
                'confidence': 0.0
            }
        
        layout = self.analyze_layout(ocr_results)
        
        # Determine OCR quality
        if layout.average_confidence >= 0.85 and layout.high_confidence_ratio >= 0.8:
            ocr_quality = 'excellent'
        elif layout.average_confidence >= 0.7 and layout.high_confidence_ratio >= 0.6:
            ocr_quality = 'good'
        elif layout.average_confidence >= 0.5:
            ocr_quality = 'fair'
        else:
            ocr_quality = 'poor'
        
        # Extract task-relevant text
        relevant_text = self.get_task_relevant_text(layout)
        
        # Enhance task description
        enhanced_task = base_task or "Activity"
        
        if layout.title_regions and layout.title_regions[0].confidence > 0.8:
            # Use high-confidence title as primary task indicator
            title_text = layout.title_regions[0].text
            if len(title_text) > 5 and len(title_text) < 100:
                enhanced_task = f"Working on: {title_text}"
        
        # Add context from code
        if layout.code_regions and len(layout.code_regions) > 5:
            enhanced_task = f"{enhanced_task} (Coding)"
        
        return {
            'task': enhanced_task,
            'ocr_quality': ocr_quality,
            'confidence': layout.average_confidence,
            'has_code': len(layout.code_regions) > 0,
            'has_ui_elements': len(layout.ui_elements) > 0,
            'title_text': layout.title_regions[0].text if layout.title_regions else None,
            'relevant_text': relevant_text,
            'text_regions': {
                'titles': len(layout.title_regions),
                'code': len(layout.code_regions),
                'ui': len(layout.ui_elements),
                'body': len(layout.body_text)
            }
        }


def create_ocr_enhancer(confidence_threshold: float = 0.7) -> OCREnhancer:
    """Factory function to create OCR enhancer."""
    return OCREnhancer(confidence_threshold)