#!/usr/bin/env python3
"""
Full Gemini AI Integration Test Script
Tests the complete workflow with Google Gemini API integration
"""

import sys
import os
import asyncio

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test that all modules can be imported successfully"""
    try:
        from config.gemini_config import gemini_config
        print("✅ Gemini configuration module imported")
    except Exception as e:
        print(f"❌ Gemini configuration import failed: {e}")
        return False
    
    try:
        from utils.gemini_client import gemini_generator
        print("✅ Gemini client module imported")
    except Exception as e:
        print(f"❌ Gemini client import failed: {e}")
        return False
    
    try:
        from enhanced_content_generator import enhanced_generator
        print("✅ Enhanced content generator imported")
    except Exception as e:
        print(f"❌ Enhanced content generator import failed: {e}")
        return False
    
    return True

async def test_gemini_integration():
    """Test Gemini API integration"""
    print("\n=== Gemini API Integration Test ===")
    
    # Check configuration status
    from config.gemini_config import gemini_config
    print(f"Configuration Status: {'Configured' if gemini_config.is_configured() else 'Not configured'}")
    print(f"API Key Present: {bool(gemini_config.api_key)}")
    print(f"Model: {gemini_config.model_name}")
    
    # Test Gemini client
    from utils.gemini_client import gemini_generator
    print(f"Gemini Client Available: {gemini_generator.is_available()}")
    
    if gemini_generator.is_available():
        # Test connection
        status = await gemini_generator.test_connection()
        print(f"Connection Status: {status['status']}")
        if status['status'] == 'available':
            print(f"Model: {status['model']}")
            print(f"Test Response: {status['test_response']}")
        else:
            print(f"Error: {status['message']}")
    
    # Test enhanced generator
    from enhanced_content_generator import enhanced_generator
    status = enhanced_generator.get_generation_status()
    print(f"\nEnhanced Generator Status:")
    print(f"  Gemini Available: {status['gemini_available']}")
    print(f"  Rule-based Available: {status['rule_based_available']}")
    print(f"  Primary Engine: {status['primary_engine']}")
    print(f"  API Key Configured: {status['api_key_configured']}")
    
    return True

async def test_content_generation():
    """Test content generation with both engines"""
    print("\n=== Content Generation Test ===")
    
    from enhanced_content_generator import enhanced_generator
    
    # Test content generation
    try:
        result = await enhanced_content_generator(
            'Artificial Intelligence in Education',
            ['Introduction', 'Objectives', 'Methodology', 'Results', 'Conclusion'],
            'academic',
            {
                'student_name': 'John Doe',
                'college_name': 'MIT',
                'department': 'Computer Science'
            }
        )
        
        print("✅ Content generation successful!")
        print(f"Topic: {result.topic}")
        print(f"Sections: {list(result.sections.keys())}")
        print(f"Word count: {result.overall_word_count}")
        print(f"Quality score: {result.content_quality_score}")
        
        # Show sample content
        if 'introduction' in result.sections:
            intro = result.sections['introduction'].content
            print(f"\nSample Introduction (first 200 chars):")
            print(intro[:200] + "..." if len(intro) > 200 else intro)
            
        return True
    except Exception as e:
        print(f"❌ Content generation failed: {e}")
        return False

async def enhanced_content_generator(*args, **kwargs):
    """Helper function to match the import above"""
    from enhanced_content_generator import enhanced_generator
    return await enhanced_generator.generate_content(*args, **kwargs)

async def main():
    print("🧪 Gemini AI Integration Test Suite")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("Import tests failed!")
        return False
    
    # Test Gemini integration
    if not await test_gemini_integration():
        print("Integration tests failed!")
        return False
    
    # Test content generation
    if not await test_content_generation():
        print("Generation tests failed!")
        return False
    
    print("\n🎉 All Gemini integration tests completed successfully!")
    print("\nConfiguration Instructions:")
    print("1. Get your API key from: https://aistudio.google.com/app/apikey")
    print("2. Set GEMINI_API_KEY in environment variables or backend/.env file")
    print("3. Restart the backend server")
    print("4. Access the Gemini status from the web interface")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)