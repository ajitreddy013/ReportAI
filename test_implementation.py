#!/usr/bin/env python3
"""
Test script to verify the smart report generation functionality
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test that all modules can be imported successfully"""
    try:
        from document_analyzer import DocumentAnalyzer
        print("✓ DocumentAnalyzer imported successfully")
    except Exception as e:
        print(f"✗ DocumentAnalyzer import failed: {e}")
        return False
    
    try:
        from content_generator import ContentGenerator
        print("✓ ContentGenerator imported successfully")
    except Exception as e:
        print(f"✗ ContentGenerator import failed: {e}")
        return False
    
    try:
        from image_processor import ImageProcessor
        print("✓ ImageProcessor imported successfully")
    except Exception as e:
        print(f"✗ ImageProcessor import failed: {e}")
        return False
    
    try:
        from smart_report_generator import SmartReportGenerator
        print("✓ SmartReportGenerator imported successfully")
    except Exception as e:
        print(f"✗ SmartReportGenerator import failed: {e}")
        return False
    
    try:
        from models.analysis import SampleDocumentAnalysis, ContentGenerationRequest
        print("✓ Models imported successfully")
    except Exception as e:
        print(f"✗ Models import failed: {e}")
        return False
    
    return True

def test_document_analyzer():
    """Test basic document analyzer functionality"""
    try:
        from document_analyzer import DocumentAnalyzer
        analyzer = DocumentAnalyzer()
        print("✓ DocumentAnalyzer instantiated successfully")
        return True
    except Exception as e:
        print(f"✗ DocumentAnalyzer instantiation failed: {e}")
        return False

def test_content_generator():
    """Test basic content generator functionality"""
    try:
        from content_generator import ContentGenerator
        generator = ContentGenerator()
        print("✓ ContentGenerator instantiated successfully")
        
        # Test basic content generation
        content = generator.generate_content(
            "Machine Learning Applications", 
            ["Introduction", "Methodology", "Results", "Conclusion"]
        )
        print(f"✓ Content generated successfully ({content.overall_word_count} words)")
        return True
    except Exception as e:
        print(f"✗ ContentGenerator test failed: {e}")
        return False

def test_smart_report_generator():
    """Test basic smart report generator functionality"""
    try:
        from smart_report_generator import SmartReportGenerator
        generator = SmartReportGenerator(".")
        print("✓ SmartReportGenerator instantiated successfully")
        return True
    except Exception as e:
        print(f"✗ SmartReportGenerator instantiation failed: {e}")
        return False

def main():
    print("Running Smart Report AI Implementation Tests")
    print("=" * 50)
    
    # Test imports
    print("\n1. Testing module imports:")
    if not test_imports():
        print("Import tests failed!")
        return False
    
    # Test individual components
    print("\n2. Testing individual components:")
    tests = [
        test_document_analyzer,
        test_content_generator,
        test_smart_report_generator
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nResults: {passed}/{len(tests)} component tests passed")
    
    if passed == len(tests):
        print("\n🎉 All tests passed! The smart report generation system is ready.")
        print("\nTo start the server:")
        print("cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        print("\nTo access the smart report interface:")
        print("Open frontend/smart-report.html in your browser")
        return True
    else:
        print(f"\n⚠️  {len(tests) - passed} tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)