import json
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / "assets" / "music"
RATE = 22050
DURATION = 22
BEATS = {
    "action": [0, 3, 6, 11, 14, 17, 20],
    "indie": [0, 4, 8, 12, 16, 20],
    "comedy": [0, 2.5, 5, 8, 11, 14, 17, 20],
    "scifi": [0, 4, 8, 11, 14, 18, 20],
}
CHORDS = {
    "action": [55, 65.41, 73.42, 49],
    "indie": [65.41, 82.41, 98, 73.42],
    "comedy": [73.42, 92.5, 110, 82.41],
    "scifi": [49, 61.74, 73.42, 55],
}


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    count = RATE * DURATION
    timeline = np.arange(count) / RATE
    rng = np.random.default_rng(84)
    for genre, roots in CHORDS.items():
        signal = np.zeros(count, dtype=np.float64)
        for bar, root in enumerate(roots * 6):
            mask = (timeline >= bar * 4) & (timeline < bar * 4 + 4)
            local = timeline[mask] - bar * 4
            pad = sum(np.sin(2 * np.pi * root * ratio * local) for ratio in (1, 1.5, 2, 3)) / 4
            signal[mask] += pad * 0.16 * (0.72 + 0.28 * np.sin(np.pi * local / 4))
            signal[mask] += np.sin(2 * np.pi * root / 2 * local) * 0.15
        for beat in np.arange(0, DURATION, 0.5):
            start = int(beat * RATE)
            length = min(int(0.18 * RATE), count - start)
            local = np.arange(length) / RATE
            kick = np.sin(2 * np.pi * (75 * local - 80 * local**2)) * np.exp(-local * 24) * 0.55
            signal[start:start + length] += kick
        for beat in np.arange(0.25, DURATION, 0.5):
            start = int(beat * RATE)
            length = min(int(0.06 * RATE), count - start)
            signal[start:start + length] += rng.normal(0, 0.12, length) * np.exp(-np.arange(length) / RATE * 65)
        for drop in BEATS[genre][1:]:
            start = int(drop * RATE)
            length = min(int(0.45 * RATE), count - start)
            signal[start:start + length] += np.sin(2 * np.pi * 42 * np.arange(length) / RATE) * np.exp(-np.arange(length) / RATE * 8) * 0.42
        fade = np.minimum(1, timeline / 0.8) * np.minimum(1, (DURATION - timeline) / 1.2)
        signal *= fade
        signal = np.tanh(signal * 1.25)
        stereo = np.column_stack((signal, np.roll(signal, 31)))
        path = DESTINATION / f"{genre}.wav"
        with wave.open(str(path), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(RATE)
            output.writeframes((stereo * 32767).astype("<i2").tobytes())
    (DESTINATION / "beats.json").write_text(json.dumps(BEATS, indent=2), encoding="utf-8")
    print(f"Generated four original scores in {DESTINATION}")


if __name__ == "__main__":
    main()
