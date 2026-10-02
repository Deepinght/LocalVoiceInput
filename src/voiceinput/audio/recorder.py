import numpy as np
import sounddevice as sd


class Recorder:
    def __init__(self):
        self.stream = None
        self.blocks = []
        self.count = 0
        self.error = None
        self.level = 0.0

    def start(self, device=None, max_seconds=120):
        self.blocks, self.count, self.error = [], 0, None
        self.level = 0.0
        self.limit = max_seconds * 16000
        def callback(indata, frames, time, status):
            if status:
                self.error = str(status)
            rms = float(np.sqrt(np.mean(np.square(indata))))
            self.level = max(0.0, min(1.0, (20 * np.log10(max(rms, 1e-6)) + 60) / 60))
            if self.count + frames <= self.limit:
                self.blocks.append(indata[:, 0].copy())
                self.count += frames
        self.stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32", device=device, callback=callback)
        try:
            self.stream.start()
        except Exception:
            self.stream.close()
            self.stream = None
            raise

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.level = 0.0
        blocks, self.blocks = self.blocks, []
        if self.error:
            raise RuntimeError(f"录音数据不完整：{self.error}")
        if not blocks:
            raise RuntimeError("没有录到音频，请检查麦克风")
        return np.concatenate(blocks)

    def cancel(self):
        if self.stream:
            try:
                self.stream.abort()
            finally:
                self.stream.close()
                self.stream = None
        self.blocks = []
        self.count = 0
        self.level = 0.0
