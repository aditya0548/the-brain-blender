import urllib.request
import json
import threading

SYSTEM_PROMPT = "You are a 2D animation pose assistant. You receive a character's locked proportions and a camera setup. Your ONLY job is to return joint positions for the requested action. Return ONLY valid JSON, no text, no explanation. The JSON must contain these joints: head_top, head_center, neck, left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist, hip_center, left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle. Each joint is [x, y, z] in world space. Maintain the locked proportions exactly."

def call_openrouter(api_key, system_prompt, user_message):
    url = 'https://openrouter.ai/api/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://blender-the-brain.local',
    }
    body = {
        'model': 'google/gemini-2.0-flash-exp:free',
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ],
        'response_format': {'type': 'json_object'}
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

class AIThread(threading.Thread):
    def __init__(self, api_key, system_prompt, user_message):
        super().__init__()
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.user_message = user_message
        self.result = None
        self.error = None
        self.is_done = False

    def run(self):
        try:
            self.result = call_openrouter(self.api_key, self.system_prompt, self.user_message)
        except Exception as e:
            self.error = e
        finally:
            self.is_done = True

def call_openrouter_async(api_key, user_message):
    thread = AIThread(api_key, SYSTEM_PROMPT, user_message)
    thread.start()
    return thread
