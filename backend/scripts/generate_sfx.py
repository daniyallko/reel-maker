import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / "assets" / "music" / "sfx"
RATE = 22050


def write(name: str, samples: np.ndarray) -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    samples = np.tanh(samples)
    stereo = np.column_stack((samples, samples))
    with wave.open(str(DESTINATION / name), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes((stereo * 32767).astype("<i2").tobytes())


def main():
    t = np.arange(RATE) / RATE
    whoosh = np.sin(2 * np.pi * (220 * t + 800 * t**2)) * np.exp(-t * 5) * 0.35
    pop = np.sin(2 * np.pi * 880 * t) * np.exp(-t * 32) * 0.45
    drop = (np.sin(2 * np.pi * (70 * t - 20 * t**2)) + 0.4 * np.sin(2 * np.pi * 140 * t)) * np.exp(-t * 4) * 0.5
    write("whoosh.wav", whoosh)
    write("pop.wav", pop)
    write("drop.wav", drop)
    print(f"Generated three original SFX in {DESTINATION}")


if __name__ == "__main__":
    main()
