import json
transcript_log = []
def process_transcription(
    whisper: WhisperApp,
    chunk: np.ndarray,
    silence_threshold: float,
    sample_rate: int
) -> None:
    global transcript_log  # allow appending to shared list

    if np.abs(chunk).mean() > silence_threshold:
        transcript = whisper.transcribe(chunk, sample_rate)
        if transcript.strip():
            print(f"Transcript: {transcript}")
            transcript_log.append({
                "timestamp": datetime.now().isoformat(),
                "text": transcript.strip()
            })

            # Save the growing list to JSON file
            with open("transcripts.json", "w", encoding="utf-8") as f:
                json.dump(transcript_log, f, ensure_ascii=False, indent=4)