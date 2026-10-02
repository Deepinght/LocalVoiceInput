"""Opt-in checks using the actual installed models; audio is never persisted."""
import argparse
import json
import time
from voiceinput.common.paths import user_root
from voiceinput.asr.model_manager import ModelManager

parser = argparse.ArgumentParser()
parser.add_argument("--download", action="store_true")
parser.add_argument("--microphone", action="store_true")
args = parser.parse_args()
root = user_root()
manager = ModelManager(root)
if args.download:
    last = [0]
    def progress(current, total):
        if time.monotonic()-last[0] > 5:
            print(f"Download {current/1048576:.1f}/{total/1048576:.1f} MB", flush=True)
            last[0] = time.monotonic()
    manager.download(progress_cb=progress)
    print("Model download and runtime validation PASS", flush=True)
if args.microphone:
    from voiceinput.audio.recorder import Recorder
    recorder = Recorder()
    recorder.start()
    time.sleep(1)
    samples = recorder.stop()
    print(json.dumps({"microphone_samples": len(samples), "sample_rate": 16000}))
if manager.is_installed():
    from voiceinput.asr.sensevoice import SenseVoiceProvider
    import numpy as np
    provider = SenseVoiceProvider(manager.get_model_path())
    try:
        provider.recognize(np.zeros(16000, dtype=np.float32))
        raise AssertionError("silence accepted")
    except RuntimeError as exc:
        if "未检测到语音" not in str(exc):
            raise
        print("Silero silence rejection PASS")
