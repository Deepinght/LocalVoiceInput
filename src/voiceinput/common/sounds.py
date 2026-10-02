"""Quiet in-memory PCM cues; no network, files or playback threads."""
import io
import math
import struct
import wave
import winsound


class SoundCues:
    def __init__(self):
        self.cache = {}

    def play(self, name, enabled=True):
        if not enabled:
            return
        if name not in self.cache:
            frequencies = {"start": (660, 880), "stop": (880, 660), "error": (330, 260)}[name]
            sample_rate, samples = 16000, []
            for frequency in frequencies:
                count = int(sample_rate * 0.055)
                for i in range(count):
                    envelope = math.sin(math.pi * i / count) ** 2
                    samples.append(int(32767 * 0.10 * envelope * math.sin(2 * math.pi * frequency * i / sample_rate)))
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(sample_rate)
                out.writeframes(struct.pack("<" + "h" * len(samples), *samples))
            self.cache[name] = buffer.getvalue()
        try:
            # Windows does not support SND_MEMORY with SND_ASYNC. The cue is 110 ms.
            winsound.PlaySound(self.cache[name], winsound.SND_MEMORY | winsound.SND_NODEFAULT)
        except RuntimeError:
            pass  # Audio feedback must never stop the recording workflow.
