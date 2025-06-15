import json
import requests
import asyncio
import aiohttp
from pathlib import Path
import yaml

# Load configuration
CONFIG_PATH = Path(r"C:\Users\Qualcomm\Downloads\simple-whisper-transcription-main\simple-whisper-transcription-main\config.yaml")
TRANSCRIPTS_PATH = Path(r"C:\Users\Qualcomm\Downloads\simple-whisper-transcription-main\simple-whisper-transcription-main\transcripts.json")


with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    cfg = yaml.safe_load(file)

API_KEY = cfg["api_key"]
BASE_URL = cfg["model_server_base_url"]
WORKSPACE = cfg["workspace_slug"]
STREAM_MODE = cfg["stream"]
CHAT_URL = f"{BASE_URL}/workspace/{WORKSPACE}/{'stream-chat' if STREAM_MODE else 'chat'}"

HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def send_transcripts():
    """ Reads JSON speeches and sends them to AI for responses and triggers home automation """
    if not TRANSCRIPTS_PATH.exists():
        raise FileNotFoundError(f"Error: transcripts.json not found at {TRANSCRIPTS_PATH}")

    try:
        # Load speech data
        transcripts = json.loads(TRANSCRIPTS_PATH.read_text(encoding="utf-8"))

        for speech in transcripts:
            message = speech["textContent"]

            custom_prompt = f"""You are an intelligent smart home assistant. 
            - Perform the user's requests.
            - Respond **only** with the relevant action performed. 

            User Request: {message}
            """

            data = {
                "message": custom_prompt,
                "mode": "chat",
                "sessionId": "speech-session",
                "attachments": []
            }
 
            response_text = asyncio.run(stream_chat(data)) if STREAM_MODE else chat(data)
 
            print(f"Speech: {message}")
            print(f"AI Response: {response_text}")
 
            # Trigger smart home automation based on AI response
            trigger_home_automation(response_text)
 
    except json.JSONDecodeError:
        print("Error: transcripts.json is corrupted or improperly formatted.")
 
def trigger_home_automation(response_text):
    """ Parses AI response and executes smart home commands """
    response_text = response_text.lower()  # Normalize for easier matching
 
    if "lights on" in response_text:
        print("Executing: Turning on lights!")
        # Insert logic to control smart lights (e.g., MQTT or API call)
 
    elif "lights off" in response_text:
        print("Executing: Turning off lights!")
 
    elif "setting temperature" in response_text:
        print("Executing: Adjusting thermostat!")
 
    elif "playing music" in response_text:
        print("Executing: Playing music!")
 
def chat(data):
    """ Sends a non-streaming chat request """
    try:
        print(CHAT_URL, HEADERS, data)
        response = requests.post(CHAT_URL, headers=HEADERS, json=data)
        response.raise_for_status()
        return response.json().get("textResponse", "No response received.")
    except requests.RequestException as e:
        return f"Chat request failed: {e}"
async def stream_chat(data):
    """ Handles streaming chat responses asynchronously using aiohttp """
    response_text = ""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(CHAT_URL, headers=HEADERS, json=data) as response:
                async for chunk in response.content.iter_any():
                    chunk_text = chunk.decode("utf-8").strip()
 
                    # Ensure correct parsing of streaming AI responses
                    if chunk_text.startswith("data: "):
                        chunk_text = chunk_text[len("data: "):]
 
                    try:
                        parsed_chunk = json.loads(chunk_text)
                        response_text += parsed_chunk.get("textResponse", "").strip() + " "  # Combine results smoothly
                    except json.JSONDecodeError:
                        continue  # Ignore invalid JSON chunks
    except aiohttp.ClientError as e:
        return f"Streaming chat request failed: {e}"
 
    return response_text.strip()  # Ensure final response is clean
# Run the script
if __name__ == "__main__":
    send_transcripts()