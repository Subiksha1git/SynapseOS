import numpy as np
import os
import queue
import sounddevice as sd
import sys
import threading
import yaml
import time
import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from model import WhisperBaseEnONNX
from qai_hub_models.models.whisper_base_en import App as WhisperApp

CONFIG_PATH = "./config.yaml"

HEADERS = {}
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


# ========== UTILITIES ==========

def chat(data):
    try:
        response = requests.post(CHAT_URL, headers=HEADERS, json=data)
        response.raise_for_status()
        return response.json().get('textResponse', 'No response received')
    except requests.RequestException as e:
        return f"Chat request failed due to {e}"

def send_transcript(transcript: str):
    # transcript = 'hey its winter, too cold in here'
    try: 
        custom_prompt = f"""You are an intelligent smart home assistant. 
        - Perform the user's requests. like temperature, volume, device activation and control.
        - response type like room : system : action : degree/digit of action (only when relevant)
        - Respond **only** with the relevant action performed. 

        User Request: {transcript}
        """

        data = {
            "message": custom_prompt,
            "mode": "chat",
            "sessionId": "speech-session",
            "attachments": []
        }

        response_text = chat(data)

        print(f"Speech: {custom_prompt}")
        print(f"AI Response: {response_text}")
    except json.JSONDecodeError:
        print("Error: transcripts.json")

# def send_to_anything_llm(text):
#     url = f"{ANY_LLM_URL}/api/v1/openai"
#     headers = {
#         'accept': 'application/json',
#         'Content-Type': 'application/json',
#         'Authorization': f'Bearer {API_KEY}'
#     }

#     payload = {
#         "messages": [
#             {"role": "user", "content": "Extract subject, verb, object from this text."},
#             {"role": "user", "content": text}
#         ],
#         "model": WORKSPACE_SLUG,
#         "stream": False,
#         "temperature": 0.5
#     }

#     try:
#         res = requests.post(url, headers=headers, json=payload)
#         res.raise_for_status()
#         return res.json().get("textResponse", "[No response]")
#     except Exception as e:
#         return f"[Error from AnythingLLM] {e}"

# def append_transcript_entry(text: str):
#     entry = {
#         "timestamp": datetime.now().isoformat(),
#         "text": text.strip()
#     }

#     if not os.path.exists("transcripts"):
#         os.makedirs("transcripts")

#     if not os.path.exists(TRANSCRIPT_FILE):
#         with open(TRANSCRIPT_FILE, "w") as f:
#             json.dump([entry], f, indent=2)
#     else:
#         with open(TRANSCRIPT_FILE, "r+") as f:
#             data = json.load(f)
#             data.append(entry)
#             f.seek(0)
#             json.dump(data, f, indent=2)

#     print(f"📝 Transcript saved.")
#     return entry

# ========== PROCESSING ==========
def process_transcription(whisper, chunk, silence_threshold, sample_rate):
    if np.abs(chunk).mean() > silence_threshold:
        transcript = whisper.transcribe(chunk, sample_rate).strip()
        if transcript:
            print(f"\n🎤 Detected: {transcript}")
            response = send_transcript(transcript=transcript)
            # print(f"🤖 LLM Response: {response}")

def process_audio(whisper, audio_queue, stop_event, chunk_samples, silence_threshold, sample_rate):
    buffer = np.empty((0,), dtype=np.float32)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        while not stop_event.is_set():
            try:
                chunk = audio_queue.get(timeout=1.0).flatten()
                buffer = np.concatenate([buffer, chunk])
                while len(buffer) >= chunk_samples:
                    current_chunk = buffer[:chunk_samples]
                    buffer = buffer[chunk_samples:]
                    future = executor.submit(process_transcription, whisper, current_chunk, silence_threshold, sample_rate)
                    futures.append(future)
                    futures = [f for f in futures if not f.done()]
            except queue.Empty:
                continue
        for future in futures:
            future.result()

def record_audio(audio_queue, stop_event, sample_rate, channels):
    def callback(indata, frames, time_info, status):
        if status:
            print("⚠️ Audio Status:", status)
        if not stop_event.is_set():
            audio_queue.put(indata.copy())

    with sd.InputStream(samplerate=sample_rate, channels=channels, callback=callback):
        print("🎙️ Recording... (Ctrl+C to stop)")
        stop_event.wait()

# ========== MAIN CLASS ==========
class LiveTranscriber:
    def __init__(self):
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)

        self.sample_rate = config.get("sample_rate", 16000)
        self.chunk_duration = config.get("chunk_duration", 4)
        self.channels = config.get("channels", 1)
        self.chunk_samples = int(self.sample_rate * self.chunk_duration)
        self.silence_threshold = config.get("silence_threshold", 0.001)

        self.encoder_path = config["encoder_path"]
        self.decoder_path = config["decoder_path"]

        if not os.path.exists(self.encoder_path) or not os.path.exists(self.decoder_path):
            sys.exit("❌ Model files missing. Check encoder/decoder paths.")

        print("🔍 Loading Whisper ONNX model...")
        self.model = WhisperApp(WhisperBaseEnONNX(self.encoder_path, self.decoder_path))

        self.audio_queue = queue.Queue()
        self.stop_event = threading.Event()

    def run(self):
        record_thread = threading.Thread(
            target=record_audio,
            args=(self.audio_queue, self.stop_event, self.sample_rate, self.channels)
        )
        process_thread = threading.Thread(
            target=process_audio,
            args=(self.model, self.audio_queue, self.stop_event, self.chunk_samples, self.silence_threshold, self.sample_rate)
        )

        record_thread.start()
        process_thread.start()

        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping transcription...")
            self.stop_event.set()

        record_thread.join()
        process_thread.join()
        print("✅ Transcription session ended.")

# ========== ENTRY POINT ==========
if __name__ == "__main__":
    LiveTranscriber().run()
