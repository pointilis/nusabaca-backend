"""
Test script for TTS Async API Views.
Demonstrates how to use the TTS API endpoints for text-to-speech processing.
"""

import requests
import time
import json


class TTSAPITester:
    """Test class for TTS API endpoints."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.tts_submit_url = f"{base_url}/api/ocr/v1/tts/async/"
        self.tts_status_url = f"{base_url}/api/ocr/v1/tts/status/"
    
    def submit_tts_task(self, text, language='en', voice_gender='female', audio_encoding='mp3'):
        """
        Submit a TTS processing task.
        
        Args:
            text (str): Text to convert to speech
            language (str): Language code
            voice_gender (str): Voice gender
            audio_encoding (str): Audio format
            
        Returns:
            dict: API response
        """
        payload = {
            'text': text,
            'language': language,
            'voice_gender': voice_gender,
            'audio_encoding': audio_encoding,
            'speaking_rate': 1.0,
            'pitch': 0.0,
            'volume_gain_db': 0.0,
            'file_prefix': 'api_test_tts'
        }
        
        try:
            print(f"🚀 Submitting TTS task...")
            print(f"📝 Text: {text[:100]}{'...' if len(text) > 100 else ''}")
            print(f"🌐 Language: {language}, Voice: {voice_gender}, Format: {audio_encoding}")
            
            response = requests.post(self.tts_submit_url, json=payload)
            
            if response.status_code == 202:
                data = response.json()
                print(f"✅ Task submitted successfully!")
                print(f"🆔 Task ID: {data['task_id']}")
                print(f"📊 Status URL: {data['status_url']}")
                return data
            else:
                print(f"❌ Failed to submit task: {response.status_code}")
                print(f"Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error submitting task: {e}")
            return None
    
    def check_task_status(self, task_id):
        """
        Check the status of a TTS task.
        
        Args:
            task_id (str): Task ID
            
        Returns:
            dict: Task status
        """
        try:
            url = f"{self.tts_status_url}{task_id}/"
            response = requests.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            return None
    
    def wait_for_completion(self, task_id, max_wait_time=300):
        """
        Wait for task completion with progress updates.
        
        Args:
            task_id (str): Task ID
            max_wait_time (int): Maximum wait time in seconds
            
        Returns:
            dict: Final task status
        """
        print(f"\n⏳ Waiting for task completion: {task_id}")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_data = self.check_task_status(task_id)
            
            if not status_data:
                print("❌ Failed to get task status")
                break
            
            status = status_data.get('status', 'unknown')
            progress = status_data.get('progress', 0)
            message = status_data.get('message', '')
            
            print(f"📈 Status: {status.upper()} | Progress: {progress}% | {message}")
            
            if status == 'completed':
                print("🎉 Task completed successfully!")
                
                # Show download info
                if 'download_url' in status_data:
                    print(f"📥 Download URL: {status_data['download_url']}")
                    print(f"⏰ Expires at: {status_data.get('download_expires_at', 'Unknown')}")
                
                if 'audio_file' in status_data:
                    audio_info = status_data['audio_file']
                    print(f"🎵 Audio File: {audio_info.get('filename')}")
                    print(f"📊 Size: {audio_info.get('size_mb', 0):.2f} MB")
                    print(f"⏱️ Duration estimate: {audio_info.get('duration_estimate', 0)} seconds")
                
                return status_data
                
            elif status == 'failed':
                print("❌ Task failed!")
                if 'error_details' in status_data:
                    print(f"Error: {status_data['error_details']}")
                return status_data
            
            time.sleep(3)  # Wait 3 seconds before next check
        
        print("⏰ Timeout waiting for task completion")
        return self.check_task_status(task_id)


def test_basic_tts():
    """Test basic TTS functionality."""
    print("🧪 Testing Basic TTS API")
    print("=" * 50)
    
    tester = TTSAPITester()
    
    # Test with English text
    text = "Hello, this is a test of the text-to-speech API. It should convert this text into audio."
    
    result = tester.submit_tts_task(text, language='en', voice_gender='female')
    
    if result and 'task_id' in result:
        final_status = tester.wait_for_completion(result['task_id'])
        return final_status
    
    return None


def test_indonesian_tts():
    """Test Indonesian TTS functionality."""
    print("\n🧪 Testing Indonesian TTS API")
    print("=" * 50)
    
    tester = TTSAPITester()
    
    # Test with Indonesian text
    text = "Selamat datang di aplikasi text-to-speech kami. Ini adalah tes untuk bahasa Indonesia."
    
    result = tester.submit_tts_task(text, language='id', voice_gender='male')
    
    if result and 'task_id' in result:
        final_status = tester.wait_for_completion(result['task_id'])
        return final_status
    
    return None


def test_advanced_tts():
    """Test advanced TTS options."""
    print("\n🧪 Testing Advanced TTS Options")
    print("=" * 50)
    
    tester = TTSAPITester()
    
    # Test with custom settings
    text = "This is a test with custom voice settings. The speech should be slower and with different pitch."
    
    # Custom payload with advanced options
    payload = {
        'text': text,
        'language': 'en',
        'voice_gender': 'male',
        'voice_index': 1,  # Second male voice
        'audio_encoding': 'wav',
        'speaking_rate': 0.8,  # Slower
        'pitch': -2.0,  # Lower pitch
        'volume_gain_db': 3.0,  # Louder
        'file_prefix': 'advanced_test'
    }
    
    try:
        print(f"🚀 Submitting advanced TTS task...")
        response = requests.post(tester.tts_submit_url, json=payload)
        
        if response.status_code == 202:
            data = response.json()
            print(f"✅ Advanced task submitted successfully!")
            print(f"🆔 Task ID: {data['task_id']}")
            
            final_status = tester.wait_for_completion(data['task_id'])
            return final_status
        else:
            print(f"❌ Failed to submit advanced task: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error in advanced test: {e}")
        return None


def test_error_handling():
    """Test error handling."""
    print("\n🧪 Testing Error Handling")
    print("=" * 50)
    
    tester = TTSAPITester()
    
    # Test with empty text
    print("Testing empty text...")
    payload = {'text': ''}
    
    try:
        response = requests.post(tester.tts_submit_url, json=payload)
        
        if response.status_code == 400:
            print("✅ Empty text properly rejected!")
            data = response.json()
            print(f"Error message: {data.get('message', 'Unknown error')}")
        else:
            print(f"⚠️ Unexpected response for empty text: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error in error handling test: {e}")


if __name__ == "__main__":
    print("🎤 TTS API Integration Tests")
    print("=" * 60)
    print("Note: Make sure Django server is running on localhost:8000")
    print("=" * 60)
    
    # Run tests
    basic_result = test_basic_tts()
    indonesian_result = test_indonesian_tts()
    advanced_result = test_advanced_tts()
    test_error_handling()
    
    print("\n📋 Test Summary")
    print("=" * 60)
    
    results = [
        ("Basic English TTS", basic_result),
        ("Indonesian TTS", indonesian_result),
        ("Advanced TTS", advanced_result)
    ]
    
    for test_name, result in results:
        if result and result.get('status') == 'completed':
            print(f"✅ {test_name}: SUCCESS")
        elif result and result.get('status') == 'failed':
            print(f"❌ {test_name}: FAILED")
        else:
            print(f"⚠️ {test_name}: INCOMPLETE")
    
    print("\n💡 API Usage Examples:")
    print("  POST /api/ocr/v1/tts/async/ - Submit TTS task")
    print("  GET /api/ocr/v1/tts/status/{task_id}/ - Check task status")
    print("\n🔧 Required payload fields:")
    print("  text (required): Text to convert to speech")
    print("  language (optional): 'en', 'id', 'en-GB'")
    print("  voice_gender (optional): 'male', 'female'")
    print("  audio_encoding (optional): 'mp3', 'wav', 'ogg'")