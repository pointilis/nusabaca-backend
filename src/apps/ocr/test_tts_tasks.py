"""
Test script for Google Text-to-Speech Celery tasks.
Run this to test the TTS task integration.
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nusabaca.settings.development')
django.setup()

from apps.ocr.tasks import submit_tts_task, get_tts_task_status_sync, quick_tts_task


def test_basic_tts_task():
    """Test basic TTS task submission and status checking."""
    print("🎤 Testing TTS Task Integration")
    print("=" * 50)
    
    # Test text
    test_text = "Hello, this is a test of the Google Text-to-Speech integration with Celery tasks."
    
    print(f"📝 Text to synthesize: {test_text}")
    print(f"📏 Text length: {len(test_text)} characters")
    
    # Submit task
    print("\n🚀 Submitting TTS task...")
    try:
        task_id = submit_tts_task(
            text=test_text,
            language_code='en',
            voice_gender='female',
            audio_format='mp3',
            file_prefix='test_tts'
        )
        print(f"✅ Task submitted successfully!")
        print(f"🆔 Task ID: {task_id}")
        
        # Check initial status
        print("\n📊 Checking task status...")
        status = get_tts_task_status_sync(task_id)
        print(f"📈 Status: {status['status']}")
        print(f"📊 Progress: {status['progress']}%")
        print(f"💬 Message: {status['message']}")
        
        return task_id
        
    except Exception as e:
        print(f"❌ Error submitting task: {e}")
        return None


def test_quick_tts():
    """Test quick TTS helper function."""
    print("\n🎵 Testing Quick TTS Helper")
    print("=" * 50)
    
    # Test Indonesian text
    test_text_id = "Selamat datang di aplikasi kami!"
    
    print(f"📝 Indonesian text: {test_text_id}")
    
    try:
        task_id = quick_tts_task(
            text=test_text_id,
            language='id',
            gender='female'
        )
        print(f"✅ Quick TTS task submitted!")
        print(f"🆔 Task ID: {task_id}")
        
        # Check status
        status = get_tts_task_status_sync(task_id)
        print(f"📈 Status: {status['status']}")
        print(f"💬 Message: {status['message']}")
        
        return task_id
        
    except Exception as e:
        print(f"❌ Error with quick TTS: {e}")
        return None


def test_advanced_tts():
    """Test advanced TTS options."""
    print("\n🎛️ Testing Advanced TTS Options")
    print("=" * 50)
    
    # Test with custom settings
    test_text = "This is a test with custom voice settings and slower speaking rate."
    
    print(f"📝 Text: {test_text}")
    
    try:
        task_id = submit_tts_task(
            text=test_text,
            language_code='en',
            voice_gender='male',
            voice_index=1,  # Use second male voice
            audio_format='wav',
            speaking_rate=0.8,  # Slower
            pitch=-2.0,  # Lower pitch
            volume_gain_db=3.0,  # Louder
            file_prefix='advanced_tts',
            user_metadata={
                'test_type': 'advanced_settings',
                'user_id': 'test_user_123'
            }
        )
        print(f"✅ Advanced TTS task submitted!")
        print(f"🆔 Task ID: {task_id}")
        
        return task_id
        
    except Exception as e:
        print(f"❌ Error with advanced TTS: {e}")
        return None


def test_error_handling():
    """Test error handling with invalid input."""
    print("\n⚠️ Testing Error Handling")
    print("=" * 50)
    
    # Test empty text
    try:
        task_id = submit_tts_task(
            text="",  # Empty text should fail
            language_code='en'
        )
        print(f"🆔 Task ID for empty text: {task_id}")
        
        # Check if it fails properly
        status = get_tts_task_status_sync(task_id)
        print(f"📈 Status: {status['status']}")
        print(f"💬 Message: {status['message']}")
        
        if status['status'] in ['FAILURE', 'ERROR']:
            print("✅ Empty text properly rejected!")
        else:
            print("⚠️ Empty text not rejected as expected")
            
    except Exception as e:
        print(f"❌ Error during error handling test: {e}")


if __name__ == "__main__":
    print("🧪 TTS Task Integration Tests")
    print("=" * 60)
    
    # Run tests
    basic_task_id = test_basic_tts_task()
    quick_task_id = test_quick_tts()
    advanced_task_id = test_advanced_tts()
    test_error_handling()
    
    print("\n📋 Summary")
    print("=" * 60)
    print("Task IDs submitted:")
    if basic_task_id:
        print(f"  📝 Basic TTS: {basic_task_id}")
    if quick_task_id:
        print(f"  🎵 Quick TTS: {quick_task_id}")
    if advanced_task_id:
        print(f"  🎛️ Advanced TTS: {advanced_task_id}")
    
    print("\n💡 Next steps:")
    print("  1. Check Celery worker logs for processing details")
    print("  2. Monitor task status using task IDs")
    print("  3. Check Google Cloud Storage for generated audio files")
    print("  4. Use the task IDs in your application to track progress")
    
    print("\n🔧 To check task status later, use:")
    print("  from apps.ocr.tasks import get_tts_task_status_sync")
    print("  status = get_tts_task_status_sync('task_id')")