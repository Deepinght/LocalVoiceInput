from pathlib import Path
import numpy as np
import sherpa_onnx
from voiceinput.engine.context import AsrResult


class SenseVoiceProvider:
    def __init__(self, path):
        self.path = Path(path)
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(self.path / "model.int8.onnx"), tokens=str(self.path / "tokens.txt"),
            num_threads=2, use_itn=True, debug=False)

    def recognize(self, samples):
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(self.path / "silero_vad.onnx")
        config.silero_vad.min_speech_duration = 0.15
        config.silero_vad.min_silence_duration = 0.3
        config.sample_rate = 16000
        vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=310)
        window = config.silero_vad.window_size
        padded = np.pad(samples, (0, (-len(samples)) % window))
        for offset in range(0, len(padded), window):
            vad.accept_waveform(padded[offset:offset+window])
        vad.flush()
        if vad.empty():
            raise RuntimeError("未检测到语音，请靠近麦克风重试")
        texts = []
        while not vad.empty():
            stream = self.recognizer.create_stream()
            stream.accept_waveform(16000, vad.front.samples)
            self.recognizer.decode_stream(stream)
            texts.append(stream.result.text.strip())
            vad.pop()
        text = "".join(texts)
        if not text:
            raise RuntimeError("识别结果为空，请重试")
        return AsrResult(text, duration_ms=round(len(samples) / 16), metadata={"provider": "sensevoice"})
