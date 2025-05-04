import requests
import json
import time
import os
import torch
import numpy as np
from PIL import Image
import io
import tempfile
import cv2
from .config_manager import HedraConfig

# Initialize config
hedra_config = HedraConfig()

class HedraImageToVideo:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "audio": ("AUDIO",),
            },
            "optional": {
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "aspect_ratio": (["16:9", "9:16", "1:1"], {"default": "16:9"}),
                "resolution": (["540p", "720p"], {"default": "720p"}),
                "use_test_mode": ("BOOLEAN", {"default": False}),
                "debug_mode": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "INT", "STRING")
    RETURN_NAMES = ("images", "audio", "frame_count", "video_url") 
    FUNCTION = "generate_video"
    CATEGORY = "Hedra"
    OUTPUT_NODE = False

    def save_audio_to_file(self, audio_data, debug_mode=False):
        """Safely save audio data to a temporary WAV file"""
        import scipy.io.wavfile
        
        if debug_mode:
            print(f"[Hedra Debug] Audio data type: {type(audio_data)}")
            print(f"[Hedra Debug] Audio keys: {audio_data.keys() if isinstance(audio_data, dict) else 'Not a dict'}")
        
        # Extract waveform and sample rate from ComfyUI audio format
        if isinstance(audio_data, dict):
            waveform = audio_data.get("waveform")
            sample_rate = audio_data.get("sample_rate", 44100)
        else:
            waveform = audio_data
            sample_rate = 44100
        
        if debug_mode:
            print(f"[Hedra Debug] Waveform shape: {waveform.shape if hasattr(waveform, 'shape') else 'No shape'}")
            print(f"[Hedra Debug] Sample rate: {sample_rate}")
        
        # Convert to numpy if it's a tensor
        if torch.is_tensor(waveform):
            waveform = waveform.cpu().numpy()
        
        # Ensure waveform is 2D (samples, channels)
        if waveform.ndim == 1:
            waveform = waveform.reshape(-1, 1)
        elif waveform.ndim == 3:
            waveform = waveform[0].T
        elif waveform.ndim == 2 and waveform.shape[0] < waveform.shape[1]:
            waveform = waveform.T
        
        # Normalize audio
        max_val = np.max(np.abs(waveform))
        if max_val > 0:
            waveform = waveform / max_val * 0.95
        
        # Convert to int16
        waveform_int16 = (waveform * 32767).astype(np.int16)
        
        # Ensure sample rate is within valid range
        sample_rate = int(sample_rate)
        if sample_rate > 65535:
            sample_rate = 44100
        
        # Create temporary file
        temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_audio.close()
        
        try:
            scipy.io.wavfile.write(temp_audio.name, sample_rate, waveform_int16)
            if debug_mode:
                print(f"[Hedra Debug] Audio saved to: {temp_audio.name}")
            return temp_audio.name
        except Exception as e:
            if debug_mode:
                print(f"[Hedra Debug] Error saving audio: {e}")
            os.unlink(temp_audio.name)
            raise e

    def generate_video(self, image, audio, prompt="", aspect_ratio="16:9", resolution="720p", use_test_mode=False, debug_mode=True):
        """Generate a talking avatar video using Hedra API"""
        
        # Get API key from config
        api_key = hedra_config.get_api_key()
        
        # Correct base URL from the example code
        base_url = "https://api.hedra.com/web-app/public"
        
        if debug_mode:
            print(f"[Hedra Debug] Config file location: {hedra_config.config_file}")
            print(f"[Hedra Debug] Base URL: {base_url}")
            if api_key and len(api_key) > 8:
                masked_key = f"{api_key[:4]}...{api_key[-4:]}"
                print(f"[Hedra Debug] API Key (masked): {masked_key}")
        
        if not api_key or api_key == "your_api_key_here":
            raise ValueError("Please set your Hedra API key in config.json")
        
        # Headers for API requests
        headers = {
            'x-api-key': api_key,  # Note: lowercase 'x' as in the example
            'Content-Type': 'application/json'
        }
        
        # If in test mode, just return placeholder data
        if use_test_mode:
            print("Test mode enabled - not making actual API calls")
            return (image, audio, 1, "test_mode_url")
        
        try:
            # Step 1: Get model ID
            if debug_mode:
                print("[Hedra Debug] Getting model ID...")
            
            response = requests.get(f"{base_url}/models", headers=headers)
            if response.status_code != 200:
                raise Exception(f"Failed to get models: {response.text}")
            
            models = response.json()
            if not models:
                raise Exception("No models available")
            
            model_id = models[0]["id"]
            if debug_mode:
                print(f"[Hedra Debug] Got model ID: {model_id}")
            
            # Step 2: Process and upload image
            i = 255. * image.cpu().numpy()[0]
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            # Save image to temporary file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_img:
                img.save(temp_img.name, format='PNG')
                temp_img_path = temp_img.name
            
            # Create image asset
            if debug_mode:
                print("[Hedra Debug] Creating image asset...")
            
            image_asset_response = requests.post(
                f"{base_url}/assets",
                headers=headers,
                json={"name": "image.png", "type": "image"}
            )
            
            if image_asset_response.status_code != 200:
                raise Exception(f"Failed to create image asset: {image_asset_response.text}")
            
            image_id = image_asset_response.json()["id"]
            
            # Upload image
            if debug_mode:
                print(f"[Hedra Debug] Uploading image with ID: {image_id}")
            
            with open(temp_img_path, 'rb') as f:
                upload_headers = {'x-api-key': api_key}  # Don't include Content-Type for multipart
                files = {'file': ('image.png', f, 'image/png')}
                upload_response = requests.post(
                    f"{base_url}/assets/{image_id}/upload",
                    headers=upload_headers,
                    files=files
                )
            
            if upload_response.status_code != 200:
                raise Exception(f"Failed to upload image: {upload_response.text}")
            
            os.unlink(temp_img_path)
            
            # Step 3: Process and upload audio
            temp_audio_path = self.save_audio_to_file(audio, debug_mode)
            
            # Create audio asset
            if debug_mode:
                print("[Hedra Debug] Creating audio asset...")
            
            audio_asset_response = requests.post(
                f"{base_url}/assets",
                headers=headers,
                json={"name": "audio.wav", "type": "audio"}
            )
            
            if audio_asset_response.status_code != 200:
                raise Exception(f"Failed to create audio asset: {audio_asset_response.text}")
            
            audio_id = audio_asset_response.json()["id"]
            
            # Upload audio
            if debug_mode:
                print(f"[Hedra Debug] Uploading audio with ID: {audio_id}")
            
            with open(temp_audio_path, 'rb') as f:
                upload_headers = {'x-api-key': api_key}
                files = {'file': ('audio.wav', f, 'audio/wav')}
                upload_response = requests.post(
                    f"{base_url}/assets/{audio_id}/upload",
                    headers=upload_headers,
                    files=files
                )
            
            if upload_response.status_code != 200:
                raise Exception(f"Failed to upload audio: {upload_response.text}")
            
            os.unlink(temp_audio_path)
            
            # Step 4: Create generation request
            if debug_mode:
                print("[Hedra Debug] Creating generation request...")
            
            generation_data = {
                "type": "video",
                "ai_model_id": model_id,
                "start_keyframe_id": image_id,
                "audio_id": audio_id,
                "generated_video_inputs": {
                    "text_prompt": prompt if prompt else "Generate a talking avatar",
                    "resolution": resolution,
                    "aspect_ratio": aspect_ratio,
                }
            }
            
            generation_response = requests.post(
                f"{base_url}/generations",
                headers=headers,
                json=generation_data
            )
            
            if generation_response.status_code != 200:
                raise Exception(f"Failed to create generation: {generation_response.text}")
            
            generation_id = generation_response.json()["id"]
            if debug_mode:
                print(f"[Hedra Debug] Generation ID: {generation_id}")
            
            # Step 5: Poll for completion
            timeout = 600  # 10 minutes
            start_time = time.time()
            check_interval = 5
            video_url = None
            
            while time.time() - start_time < timeout:
                status_response = requests.get(
                    f"{base_url}/generations/{generation_id}/status",
                    headers=headers
                )
                
                if status_response.status_code != 200:
                    raise Exception(f"Failed to check status: {status_response.text}")
                
                status_data = status_response.json()
                status = status_data.get("status", "Unknown")
                
                if debug_mode:
                    print(f"[Hedra Debug] Status: {status}")
                
                if status == "complete":
                    video_url = status_data.get("url")
                    if video_url:
                        print(f"Video generated successfully!")
                        break
                    else:
                        raise Exception("Video completed but URL not found")
                elif status == "error":
                    error_msg = status_data.get("error_message", "Unknown error")
                    raise Exception(f"Video generation failed: {error_msg}")
                
                time.sleep(check_interval)
            
            if not video_url:
                raise Exception("Timeout waiting for video generation")
            
            # Step 6: Download and process video
            print("Downloading generated video...")
            response = requests.get(video_url)
            if response.status_code != 200:
                raise Exception(f"Failed to download video: {response.status_code}")
            
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
                temp_video.write(response.content)
                temp_video_path = temp_video.name
            
            # Extract frames
            print("Extracting frames from video...")
            cap = cv2.VideoCapture(temp_video_path)
            frames = []
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_tensor = torch.from_numpy(frame_rgb.astype(np.float32) / 255.0)
                frames.append(frame_tensor)
                frame_count += 1
            
            cap.release()
            os.unlink(temp_video_path)
            
            if not frames:
                raise Exception("No frames extracted from video")
            
            images_tensor = torch.stack(frames)
            print(f"Successfully extracted {frame_count} frames")
            
            return (images_tensor, audio, frame_count, video_url)
            
        except Exception as e:
            raise Exception(f"Error in video generation: {str(e)}")


NODE_CLASS_MAPPINGS = {
    "HedraImageToVideo": HedraImageToVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "HedraImageToVideo": "Hedra Image to Video",
}