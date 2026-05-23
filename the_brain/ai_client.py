import urllib.request
import urllib.error
import json
import threading

SYSTEM_PROMPT = """You are a 2D animation pose assistant. Return ONLY valid JSON with no explanation. Return joint positions for the requested action with these exact keys: head_top, head_center, neck, left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist, hip_center, left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle. Each value is [x, y, z]. Also include target_frame (integer) and action_description (string)."""

def call_openrouter(api_key, user_message, callback):
    def run():
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            data = json.dumps({
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ]
            }).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("Content-Type", "application/json")
            req.add_header("HTTP-Referer", "https://the-brain-blender.local")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                callback(content, None)
        except urllib.error.HTTPError as e:
            callback(None, f"HTTP {e.code}: {e.reason} — {e.read().decode()}")
        except Exception as e:
            callback(None, str(e))
    threading.Thread(target=run, daemon=True).start()