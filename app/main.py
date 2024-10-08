import asyncio
import base64
import orjson
import sys
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocketDisconnect
from loguru import logger
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv
from app.config import get_config

from api.realtime.openai import send_session_update, REALTIME_HEADERS, REALTIME_WS_URL

logger.add(sys.stdout, colorize=True, format="<green>{time}</green> <level>{message}</level>")
load_dotenv()

# Configuration
OPENAI_API_KEY = get_config('OPENAI_API_KEY') # requires OpenAI Realtime API Access
PORT = int(get_config('PORT', default='5050'))
SYSTEM_MESSAGE = get_config('SYSTEM_MESSAGE', default='You are a helpful AI assistant who loves to chat')
VOICE = get_config('VOICE', default='alloy')
LOG_EVENT_TYPES = [
    'response.content.done',
    'rate_limits.updated',
    'response.done',
    'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started',
    'session.created'
]

app = FastAPI()


if not OPENAI_API_KEY:
    raise ValueError('Missing the OpenAI API key. Please set it in the .env file.')

@app.get('/', response_class=HTMLResponse)
async def index_page():
    return HTMLResponse("Twilio Media Stream Server is running!")

@app.api_route('/finished-call', methods=['POST'])
async def handle_finished_call(request: Request):
    """Handle call finished event."""
    return HTMLResponse("Call finished event received.")

@app.api_route("/incoming-call", methods=['GET', 'POST'])
async def handle_incoming_call(request: Request):
    """Handle incoming call and return TwiML response to connect to Media Stream."""
    response = VoiceResponse()
    response.play('https://prod-smith.s3.amazonaws.com/twilio/outgoing.mp3')
    response.pause(length=1)
    host = request.url.hostname
    connect = Connect()
    connect.stream(url=f'wss://{host}/media-stream')
    response.append(connect)
    return HTMLResponse(content=str(response), media_type='application/xml')

@app.websocket('/media-stream')
async def handle_media_stream(websocket: WebSocket):
    """Handle WebSocket connections between Twilio and OpenAI."""
    logger.info('Client connected')
    await websocket.accept()

    async with websockets.connect(REALTIME_WS_URL, extra_headers=REALTIME_HEADERS) as openai_ws:
        await send_session_update(openai_ws)
        stream_sid = None

        async def receive_from_twilio():
            """Receive audio data from Twilio and send it to the OpenAI Realtime API."""
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    data = orjson.loads(message)
                    if data['event'] == 'media' and openai_ws.open:
                        audio_append = {
                            'type': 'input_audio_buffer.append',
                            'audio': data['media']['payload']
                        }
                        await openai_ws.send(orjson.dumps(audio_append).decode('utf-8'))
                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        logger.info(f'Incoming stream has started {stream_sid}')
            except WebSocketDisconnect:
                logger.info('Client disconnected.')
                if openai_ws.open:
                    await openai_ws.close()

        async def send_to_twilio():
            """Receive events from the OpenAI Realtime API, send audio back to Twilio."""
            nonlocal stream_sid
            try:
                async for openai_message in openai_ws:
                    response = orjson.loads(openai_message)
                    if response['type'] in LOG_EVENT_TYPES:
                        logger.info(f"Received event: {response['type']}", response)
                    if response['type'] == 'session.updated':
                        logger.info('Session updated successfully:', response)
                    if response['type'] == 'response.audio.delta' and response.get('delta'):
                        # Audio from OpenAI
                        try:
                            audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                            audio_delta = {
                                'event': 'media',
                                'streamSid': stream_sid,
                                'media': {
                                    'payload': audio_payload
                                }
                            }
                            await websocket.send_json(audio_delta)
                        except Exception as e:
                            logger.info(f'Error processing audio data: {e}')
            except Exception as e:
                logger.info(f'Error in send_to_twilio: {e}')

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=PORT)