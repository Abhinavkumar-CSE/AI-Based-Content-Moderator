import requests
import os

API_USER = os.environ.get('SIGHTENGINE_API_USER', '11864192')
API_SECRET = os.environ.get('SIGHTENGINE_API_SECRET', 'hBMAuLvF58hE7hkNPeQNEj5ED52cWcPn')

def check_image_content(image_path):
    url = 'https://api.sightengine.com/1.0/check.json'
    
    result_data = {
        "label": "❌ Error processing image.",
        "safe": False,
        "raw_response": None # Store raw API response for debugging
    }

    try:
        with open(image_path, 'rb') as f:
            files = {'media': f}
            data = {
                'models': 'nudity,wad,offensive,gore',
                'api_user': API_USER,
                'api_secret': API_SECRET
            }

            response = requests.post(url, files=files, data=data, timeout=10)
            response.raise_for_status()
            api_result = response.json()
            result_data["raw_response"] = api_result

            # --- DEBUGGING: Print raw API response ---
            print(f"Sightengine API Raw Response for {image_path}: {api_result}")
            # --- END DEBUGGING ---

            if api_result.get('status') == 'success':
                nudity_safe = api_result.get('nudity', {}).get('safe', 1.0)
                offensive_prob = api_result.get('offensive', {}).get('prob', 0)
                gore_prob = api_result.get('gore', {}).get('prob', 0)
                weapon_detected_prob = api_result.get('weapon', {}).get('weapon', 0)

                # --- FURTHER ADJUSTED THRESHOLDS ---
                # Relaxing nudity threshold even more: if safe score is below 0.6 (was 0.8), it's inappropriate
                NUDITY_SAFE_THRESHOLD = 0.6
                # Raising offensive/gore/weapon thresholds even more: require higher confidence to flag
                OFFENSIVE_THRESHOLD = 0.7 # Was 0.6
                GORE_THRESHOLD = 0.7      # Was 0.6
                WEAPON_THRESHOLD = 0.7    # Was 0.6

                if (nudity_safe < NUDITY_SAFE_THRESHOLD or
                    offensive_prob > OFFENSIVE_THRESHOLD or
                    gore_prob > GORE_THRESHOLD or
                    weapon_detected_prob > WEAPON_THRESHOLD):
                    
                    result_data["label"] = "⚠️ Inappropriate image detected."
                    result_data["safe"] = False
                else:
                    result_data["label"] = "✅ Image is safe."
                    result_data["safe"] = True
            else:
                error_message = api_result.get('error', {}).get('message', 'Unknown API error')
                result_data["label"] = f"❌ API Error: {error_message}"
                result_data["safe"] = False

    except requests.exceptions.RequestException as e:
        result_data["label"] = f"❌ Network or API communication error: {e}"
        result_data["safe"] = False
    except FileNotFoundError:
        result_data["label"] = "❌ Image file not found."
        result_data["safe"] = False
    except Exception as e:
        result_data["label"] = f"❌ Unexpected error during image processing: {e}"
        result_data["safe"] = False
    
    return result_data