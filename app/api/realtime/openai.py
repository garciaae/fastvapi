import orjson
from app.config import get_config

REALTIME_HEADERS = {
    "Authorization": f"Bearer {get_config('OPENAI_API_KEY')}",
    "OpenAI-Beta": "realtime=v1"
}
REALTIME_WS_URL = 'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01'

START_SESSION = {
    'turn_detection': {'type': 'server_vad'},
    'input_audio_format': 'g711_ulaw',
    'output_audio_format': 'g711_ulaw',
    'voice': get_config('VOICE', default='alloy'),
    'instructions': get_config('SYSTEM_MESSAGE'),
    'modalities': ['text', 'audio'],
    'temperature': 0.7,
}

async def send_session_update(openai_ws, command=None):
    """Send session update to OpenAI WebSocket."""
    if command is None:
        command = START_SESSION
    session_update = {
        'type': 'session.update',
        'session': command
    }
    session_data = orjson.dumps(session_update).decode('utf-8')
    await openai_ws.send(session_data)
