#!/usr/bin/env python3
"""
VLM Model Validation Script
Validates Ollama model availability and basic functionality for AutoTaskTracker VLM dual-model implementation.
"""
import sys
import os
import json
import time
import requests
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autotasktracker.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VLMModelValidator:
    """Validates VLM models for AutoTaskTracker implementation."""
    
    def __init__(self):
        """Initialize validator with configuration."""
        self.config = get_config()
        self.ollama_host = self.config.SERVER_HOST
        self.ollama_port = self.config.OLLAMA_PORT
        self.base_url = f"http://{self.ollama_host}:{self.ollama_port}"
        
        # Models to validate
        self.required_models = {
            'minicpm-v:8b': 'Vision model for screenshot analysis',
            'llama3:8b': 'Text model for session reasoning'
        }
        
        # Test image for validation
        self.test_image_path = None
        self.create_test_image()
        
    def create_test_image(self):
        """Create a simple test image for validation."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import tempfile
            
            # Create simple test image
            img = Image.new('RGB', (400, 300), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add some text
            draw.text((20, 20), "AutoTaskTracker VLM Test", fill='black')
            draw.text((20, 50), "This is a test screenshot", fill='black')
            draw.text((20, 80), "for model validation", fill='black')
            
            # Add some simple UI elements
            draw.rectangle([20, 120, 200, 150], outline='blue', width=2)
            draw.text((30, 130), "Test Button", fill='blue')
            
            # Save to temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            img.save(temp_file.name)
            self.test_image_path = temp_file.name
            logger.info(f"Created test image: {self.test_image_path}")
            
        except Exception as e:
            logger.error(f"Failed to create test image: {e}")
            self.test_image_path = None
    
    def check_ollama_service(self) -> bool:
        """Check if Ollama service is running."""
        try:
            response = requests.get(f"{self.base_url}/api/version", timeout=5)
            if response.status_code == 200:
                version_info = response.json()
                logger.info(f"Ollama service running: {version_info}")
                return True
            else:
                logger.error(f"Ollama service returned status {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama service at {self.base_url}")
            return False
        except Exception as e:
            logger.error(f"Error checking Ollama service: {e}")
            return False
    
    def list_available_models(self) -> List[Dict]:
        """List all available models in Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models_data = response.json()
                models = models_data.get('models', [])
                logger.info(f"Found {len(models)} available models")
                return models
            else:
                logger.error(f"Failed to list models: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def check_model_availability(self, model_name: str) -> Tuple[bool, Dict]:
        """Check if specific model is available."""
        models = self.list_available_models()
        for model in models:
            if model.get('name') == model_name:
                logger.info(f"Model {model_name} is available")
                return True, model
        
        logger.warning(f"Model {model_name} not found")
        return False, {}
    
    def download_model(self, model_name: str) -> bool:
        """Download model if not available."""
        logger.info(f"Downloading model: {model_name}")
        
        try:
            # Start download
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={'name': model_name},
                stream=True,
                timeout=600  # 10 minute timeout for download
            )
            
            if response.status_code == 200:
                # Monitor download progress
                for line in response.iter_lines():
                    if line:
                        try:
                            progress = json.loads(line.decode('utf-8'))
                            if 'status' in progress:
                                if progress['status'] == 'success':
                                    logger.info(f"Successfully downloaded {model_name}")
                                    return True
                                elif 'total' in progress and 'completed' in progress:
                                    percent = (progress['completed'] / progress['total']) * 100
                                    logger.info(f"Download progress: {percent:.1f}%")
                        except json.JSONDecodeError:
                            continue
            else:
                logger.error(f"Failed to download {model_name}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading {model_name}: {e}")
            return False
        
        return False
    
    def test_model_inference(self, model_name: str) -> Tuple[bool, Dict]:
        """Test model inference with a simple prompt."""
        if not self.test_image_path and 'minicpm-v' in model_name:
            logger.error("No test image available for vision model testing")
            return False, {}
        
        try:
            # Prepare test payload
            if 'minicpm-v' in model_name:
                # Test vision model
                import base64
                with open(self.test_image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                
                payload = {
                    'model': model_name,
                    'prompt': 'Describe what you see in this image.',
                    'images': [image_data],
                    'stream': False,
                    'options': {
                        'temperature': 0.0,
                        'top_p': 0.9,
                        'num_predict': 100
                    }
                }
            else:
                # Test text model
                payload = {
                    'model': model_name,
                    'prompt': 'What is the capital of France?',
                    'stream': False,
                    'options': {
                        'temperature': 0.0,
                        'top_p': 0.9,
                        'num_predict': 50
                    }
                }
            
            # Make inference request
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            inference_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if 'response' in result:
                    response_text = result['response'].strip()
                    logger.info(f"Model {model_name} inference successful ({inference_time:.2f}s)")
                    logger.info(f"Response: {response_text[:100]}...")
                    
                    return True, {
                        'response': response_text,
                        'inference_time': inference_time,
                        'model_info': result
                    }
                else:
                    logger.error(f"No response in result: {result}")
                    return False, {}
            else:
                logger.error(f"Inference failed: {response.status_code}")
                return False, {}
                
        except Exception as e:
            logger.error(f"Error testing {model_name}: {e}")
            return False, {}
    
    def validate_model_memory(self, model_name: str) -> Dict:
        """Estimate model memory requirements."""
        try:
            # Get model info
            response = requests.post(
                f"{self.base_url}/api/show",
                json={'name': model_name},
                timeout=10
            )
            
            if response.status_code == 200:
                model_info = response.json()
                
                # Extract size information
                size_info = {}
                if 'details' in model_info:
                    details = model_info['details']
                    if 'parameter_size' in details:
                        size_info['parameter_size'] = details['parameter_size']
                    if 'quantization_level' in details:
                        size_info['quantization'] = details['quantization_level']
                
                # Estimate memory usage (rough calculation)
                # For 8B models, typically 4-8GB depending on quantization
                if '8b' in model_name.lower():
                    size_info['estimated_memory_gb'] = 6  # Conservative estimate
                elif '7b' in model_name.lower():
                    size_info['estimated_memory_gb'] = 5
                else:
                    size_info['estimated_memory_gb'] = 4
                
                logger.info(f"Model {model_name} memory estimate: {size_info}")
                return size_info
            else:
                logger.error(f"Failed to get model info for {model_name}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting memory info for {model_name}: {e}")
            return {}
    
    def run_validation(self) -> Dict:
        """Run complete validation process."""
        logger.info("Starting VLM model validation...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'ollama_service': False,
            'models': {},
            'overall_status': 'failed',
            'recommendations': []
        }
        
        # Check Ollama service
        if not self.check_ollama_service():
            results['recommendations'].append("Start Ollama service before proceeding")
            return results
        
        results['ollama_service'] = True
        
        # List available models
        available_models = self.list_available_models()
        available_names = [m.get('name', '') for m in available_models]
        
        # Validate each required model
        all_models_ready = True
        for model_name, description in self.required_models.items():
            logger.info(f"Validating {model_name}: {description}")
            
            model_result = {
                'name': model_name,
                'description': description,
                'available': False,
                'inference_test': False,
                'memory_info': {},
                'download_attempted': False
            }
            
            # Check availability
            is_available, model_info = self.check_model_availability(model_name)
            model_result['available'] = is_available
            
            if not is_available:
                # Try to download
                logger.info(f"Attempting to download {model_name}")
                model_result['download_attempted'] = True
                if self.download_model(model_name):
                    model_result['available'] = True
                    is_available = True
                else:
                    all_models_ready = False
                    results['recommendations'].append(f"Manually download {model_name} with: ollama pull {model_name}")
            
            if is_available:
                # Test inference
                inference_success, inference_result = self.test_model_inference(model_name)
                model_result['inference_test'] = inference_success
                model_result['inference_result'] = inference_result
                
                # Get memory info
                memory_info = self.validate_model_memory(model_name)
                model_result['memory_info'] = memory_info
                
                if not inference_success:
                    all_models_ready = False
                    results['recommendations'].append(f"Fix inference issues with {model_name}")
            
            results['models'][model_name] = model_result
        
        # Overall status
        if all_models_ready:
            results['overall_status'] = 'ready'
            results['recommendations'].append("All models validated successfully - ready for dual-model implementation")
        else:
            results['overall_status'] = 'partial'
            results['recommendations'].append("Some models need attention before proceeding")
        
        return results
    
    def cleanup(self):
        """Clean up test resources."""
        if self.test_image_path and os.path.exists(self.test_image_path):
            try:
                os.unlink(self.test_image_path)
                logger.info("Cleaned up test image")
            except Exception as e:
                logger.error(f"Failed to clean up test image: {e}")


def main():
    """Main validation function."""
    validator = VLMModelValidator()
    
    try:
        # Run validation
        results = validator.run_validation()
        
        # Print results
        print("\n" + "="*60)
        print("VLM MODEL VALIDATION RESULTS")
        print("="*60)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Ollama Service: {'✓' if results['ollama_service'] else '✗'}")
        print(f"Overall Status: {results['overall_status'].upper()}")
        print()
        
        # Print model details
        for model_name, model_result in results['models'].items():
            print(f"Model: {model_name}")
            print(f"  Available: {'✓' if model_result['available'] else '✗'}")
            print(f"  Inference Test: {'✓' if model_result['inference_test'] else '✗'}")
            
            if model_result.get('memory_info'):
                memory_info = model_result['memory_info']
                if 'estimated_memory_gb' in memory_info:
                    print(f"  Memory Estimate: {memory_info['estimated_memory_gb']}GB")
            
            if model_result.get('inference_result'):
                inference_time = model_result['inference_result'].get('inference_time', 0)
                print(f"  Inference Time: {inference_time:.2f}s")
            
            print()
        
        # Print recommendations
        if results['recommendations']:
            print("RECOMMENDATIONS:")
            for i, rec in enumerate(results['recommendations'], 1):
                print(f"{i}. {rec}")
        
        # Save results to file
        results_file = Path("validation_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to: {results_file}")
        
        # Return appropriate exit code
        if results['overall_status'] == 'ready':
            return 0
        elif results['overall_status'] == 'partial':
            return 1
        else:
            return 2
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 3
    finally:
        validator.cleanup()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)