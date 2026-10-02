"""Offline ASR integration check with Windows-generated speech in memory."""
import json
import numpy as np
import win32com.client
from voiceinput.common.paths import user_root
from voiceinput.asr.model_manager import ModelManager
from voiceinput.asr.sensevoice import SenseVoiceProvider
from voiceinput.config.loader import ConfigStore
from voiceinput.engine.pipeline import Pipeline

voice = win32com.client.Dispatch("SAPI.SpVoice")
voices = voice.GetVoices()
for i in range(voices.Count):
    token = voices.Item(i)
    if "804" in token.GetAttribute("Language"):
        voice.Voice = token
        break
stream = win32com.client.Dispatch("SAPI.SpMemoryStream")
stream.Format.Type = 18  # SAFT16kHz16BitMono
voice.AudioOutputStream = stream
voice.Speak("今天下午去实验室看看数据。氮气流量一百标准立方米每小时，温度五百摄氏度。")
samples = np.frombuffer(bytes(stream.GetData()), dtype="<i2").astype(np.float32) / 32768
root = user_root()
result = SenseVoiceProvider(ModelManager(root).get_model_path()).recognize(samples)
assert "实验室" in result.text and "氮气" in result.text, result.text
ctx = Pipeline(ConfigStore(root)).process(result, "science")
print(json.dumps({"samples": len(samples), "raw_text": result.text, "processed_text": ctx.text, "trace_events": len(ctx.trace)}, ensure_ascii=False, indent=2))
