import bpy
import sys
import os

# Ensure the brain addon is reachable
addon_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if addon_path not in sys.path:
    sys.path.append(addon_path)

# Enable addon by name
bpy.ops.preferences.addon_enable(module="the_brain")

# Mock urllib.request.urlopen to avoid real network requests
import urllib.request
import json
import io

class MockResponse:
    def __init__(self, data):
        self.data = data
    def read(self):
        return self.data
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def mock_urlopen(req, *args, **kwargs):
    mock_data = {
        "choices": [
            {
                "message": {
                    "content": '{"head_top": [0, 0, 2], "head_center": [0, 0, 1.8]}'
                }
            }
        ]
    }
    return MockResponse(json.dumps(mock_data).encode('utf-8'))

urllib.request.urlopen = mock_urlopen

# Setup scene
bpy.context.scene.brain_api_key = "test_key"
bpy.context.scene.brain_prompt_text = "Jump!"

# Trigger operator
bpy.ops.brain.send_to_ai()

# Wait for a brief moment and force timer evaluation (in background mode it might require manual pump)
import time
time.sleep(1)

# In headless blender we can just check if thread was started and result parsed manually,
# since modal timer handlers don't run automatically in background easily without a loop.

from the_brain.__init__ import BRAIN_OT_send_to_ai
# Since we invoked it, the instance ran execute() and spawned the thread.
# Wait for the thread in the class (if accessible, but we stored it in the instance which is discarded by op system).
# Alternatively, we can rely on standard print statements in a more controlled environment.
print("STATUS AFTER INVOKE:", bpy.context.scene.brain_status)
