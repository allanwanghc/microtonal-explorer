#!/usr/bin/env python3
"""Microtonal N-EDO Generator

Given start/end frequencies and N divisions, generates an N-EDO scale.
When N > 12, finds the nearest N-EDO pitch for each 12-division reference
pitch and plays ascending/descending sequences of the matched subset.

Note: when the interval ratio != 2, this is NOT traditional 12-EDO; it is
simply dividing the given interval into 12 equal (log-frequency) parts as
a reference grid.
"""

import wave
import numpy as np

SAMPLE_RATE = 48000
NOTE_DURATION = 0.2  # Duration per note (seconds)

# ADSR envelope timings (seconds)
# Attack:  how fast the note reaches full volume
# Decay:   drop from peak to sustain level
# Sustain: steady-state volume (as a fraction of peak)
# Release: fade out at the end of the note
ATTACK = 0.02
DECAY = 0.08
SUSTAIN_LEVEL = 0.6
RELEASE = 0.08

# Harmonics: (frequency multiplier, relative amplitude)
# Minimal overtones to keep pitch clear for microtonal work,
# while sounding slightly warmer than a pure sine.
HARMONICS = [
    (1, 1.0),   # fundamental
    (2, 0.1),   # 2nd partial — very subtle warmth
]

# Simple reverb: short echoes to add a sense of space
# without smearing the pitch.
REVERB_ECHOES = 4       # number of echo repetitions
REVERB_DELAY = 0.04     # delay between echoes (seconds)
REVERB_DECAY = 0.3      # amplitude multiplier per echo

# Try importing sounddevice; fall back to WAV export if unavailable
try:
    import sounddevice as sd
    HAS_SD = True
except (ImportError, OSError):
    HAS_SD = False


def relative_cents(f, base):
    """Convert frequency to cents relative to base."""
    return 1200 * np.log2(f / base)


def make_adsr(num_samples, sr=SAMPLE_RATE):
    """Build an ADSR envelope curve (values 0.0 to 1.0).

    The envelope shapes each note so it feels "played" rather than
    abruptly switched on/off:
      - Attack:  ramp up to 1.0
      - Decay:   ease down to SUSTAIN_LEVEL
      - Sustain: hold at SUSTAIN_LEVEL
      - Release: fade to 0.0
    """
    a = int(sr * ATTACK)
    d = int(sr * DECAY)
    r = int(sr * RELEASE)
    s = max(num_samples - a - d - r, 0)  # sustain fills the remainder

    env = np.concatenate([
        np.linspace(0, 1, a),              # attack
        np.linspace(1, SUSTAIN_LEVEL, d),   # decay
        np.full(s, SUSTAIN_LEVEL),          # sustain
        np.linspace(SUSTAIN_LEVEL, 0, r),   # release
    ])

    # Trim or pad to exact length (rounding can cause ±1 sample)
    return env[:num_samples] if len(env) >= num_samples else np.pad(env, (0, num_samples - len(env)))


def apply_reverb(signal, sr=SAMPLE_RATE):
    """Add simple reverb by mixing in quieter, delayed copies of the signal.

    Each echo is delayed by REVERB_DELAY seconds and attenuated by
    REVERB_DECAY relative to the previous echo.  This gives a sense
    of space without smearing pitch — important for microtonal work.
    """
    out_len = len(signal) + int(sr * REVERB_DELAY * REVERB_ECHOES)
    out = np.zeros(out_len, dtype=np.float64)
    out[:len(signal)] += signal

    amp = REVERB_DECAY
    for i in range(1, REVERB_ECHOES + 1):
        offset = int(sr * REVERB_DELAY * i)
        out[offset:offset + len(signal)] += signal * amp
        amp *= REVERB_DECAY  # each echo is quieter

    return out


def generate_tone(freq, duration=NOTE_DURATION, sr=SAMPLE_RATE):
    """Generate a single note with harmonics, ADSR envelope, and reverb.

    1. Sum sine waves for each harmonic (fundamental + overtones)
    2. Apply ADSR envelope so the note feels natural
    3. Add light reverb for spatial warmth
    4. Normalize to avoid clipping
    """
    num_samples = int(sr * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # Layer harmonics: each is a sine at (freq * multiplier) scaled by amplitude
    wave = np.zeros(num_samples, dtype=np.float64)
    for multiplier, amp in HARMONICS:
        wave += amp * np.sin(2 * np.pi * freq * multiplier * t)

    # Normalize the harmonic sum so peak == 1.0
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave /= peak

    # Shape with ADSR envelope
    envelope = make_adsr(num_samples, sr)
    wave *= envelope

    # Add reverb
    wave = apply_reverb(wave, sr)

    # Final normalization to 50% amplitude (headroom for mixing)
    peak = np.max(np.abs(wave))
    if peak > 0:
        wave = wave / peak * 0.5

    return wave.astype(np.float32)


def save_wav(filename, audio, sr=SAMPLE_RATE):
    """Save float32 audio array to a 16-bit WAV file (no external deps)."""
    pcm = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    print(f"  -> Saved: {filename}")


def play_audio(audio, filename):
    """Play audio if sounddevice is available, otherwise save to WAV."""
    if HAS_SD:
        sd.play(audio, SAMPLE_RATE)
        sd.wait()
    else:
        save_wav(filename, audio)


def print_sequence(freqs, label=""):
    """Print a frequency table (no audio)."""
    if label:
        print(f"\n{'='*55}")
        print(f"  {label}")
        print(f"{'='*55}")

    for i, f in enumerate(freqs):
        cents = relative_cents(f, freqs[0])
        print(f"  [{i+1:2d}] {f:8.2f} Hz  ({cents:+7.1f} cents)")


def build_audio(freqs):
    """Build concatenated audio from a list of frequencies."""
    waves = [generate_tone(f) for f in freqs]
    return np.concatenate(waves)


def ask_yes_no(prompt, default=False):
    """Prompt for y/n, return bool."""
    suffix = "(y/n, default n): " if not default else "(y/n, default y): "
    raw = input(prompt + suffix).strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def get_positive_float(prompt, default):
    """Prompt for a positive float with a default value."""
    raw = input(prompt).strip()
    if not raw:
        return default
    val = float(raw)
    if val <= 0:
        raise ValueError(f"Must be positive, got {val}")
    return val


def get_positive_int(prompt, default):
    """Prompt for a positive integer with a default value."""
    raw = input(prompt).strip()
    if not raw:
        return default
    val = int(raw)
    if val <= 0:
        raise ValueError(f"Must be positive, got {val}")
    return val


def run_session():
    """Run one session: input params, compute, optionally play."""

    # --- Input with validation ---
    try:
        start_freq = get_positive_float("Start frequency (Hz, default 440): ", 440)
        end_freq = get_positive_float("End frequency (Hz, default 880): ", 880)
        n = get_positive_int("Number of divisions (N, default 13): ", 13)
    except ValueError as e:
        print(f"Invalid input: {e}")
        return

    if end_freq <= start_freq:
        print("Error: end frequency must be greater than start frequency.")
        return

    ratio = end_freq / start_freq

    # Warn if the interval is not an octave
    interval_cents = 1200 * np.log2(ratio)
    if abs(interval_cents - 1200) > 1:
        print(f"\n  [!] Interval is {interval_cents:.1f} cents (not an octave).")
        print(f"      The 12-division reference below is NOT standard 12-EDO,")
        print(f"      but 12 equal log-divisions of this specific interval.\n")

    print(f"Frequency ratio: {ratio:.4f}")
    print(f"Step ratio: {ratio**(1/n):.6f}")
    print(f"Cents per step: {interval_cents / n:.2f}")

    # --- Generate all N-EDO frequencies ---
    edo_freqs = [start_freq * ratio ** (i / n) for i in range(n + 1)]

    # --- Playback options ---
    print()
    play_all = ask_yes_no("Play all N-EDO pitches? ")

    if n > 12:
        play_asc = ask_yes_no("Play ascending sequence (nearest to 12-division ref)? ")
        play_desc = ask_yes_no("Play descending sequence? ")
    else:
        play_asc = False
        play_desc = False

    # --- All N-EDO pitches ---
    label_all = f"{n}-EDO All Pitches ({start_freq}→{end_freq} Hz)"
    print_sequence(edo_freqs, label_all)
    if play_all:
        play_audio(build_audio(edo_freqs), "all_pitches.wav")

    # --- 12-division matching (only when N > 12) ---
    if n > 12:
        target_12 = [start_freq * ratio ** (i / 12) for i in range(1, 12)]

        matches = []
        for t_idx, target in enumerate(target_12):
            target_cents = relative_cents(target, start_freq)
            best_idx = min(
                range(len(edo_freqs)),
                key=lambda j: abs(relative_cents(edo_freqs[j], start_freq) - target_cents),
            )
            best_diff = abs(relative_cents(edo_freqs[best_idx], start_freq) - target_cents)
            matches.append((t_idx + 1, best_idx, edo_freqs[best_idx], best_diff))

        matched_indices = sorted(set(m[1] for m in matches))

        # Display matching table
        print(f"\n{'='*55}")
        print(f"  12-Division Matching")
        print(f"{'='*55}")
        print(f"  {'Ref #':>6}  {'N-EDO #':>7}  {'Freq(Hz)':>10}  {'Diff(cents)':>11}")
        for t_idx, n_idx, freq, diff in matches:
            print(f"  {t_idx:>6}  {n_idx:>7}  {freq:>10.2f}  {diff:>+11.1f}")

        # Ascending
        scale_up = [start_freq] + [edo_freqs[i] for i in matched_indices] + [end_freq]
        count = len(scale_up)
        print_sequence(scale_up, f"Ascending sequence ({count} notes, nearest to 12-division ref)")
        if play_asc:
            play_audio(build_audio(scale_up), "ascending.wav")

        # Descending
        scale_down = list(reversed(scale_up))
        print_sequence(scale_down, f"Descending sequence ({count} notes)")
        if play_desc:
            play_audio(build_audio(scale_down), "descending.wav")
    else:
        print(f"\n  [i] N={n} <= 12, skipping 12-division matching.")


def main():
    print("=== Microtonal N-EDO Scale Generator ===\n")

    if not HAS_SD:
        print("  [!] sounddevice not available; will export WAV files instead.\n")

    while True:
        run_session()
        print()
        if not ask_yes_no("Try another? "):
            break
        print("\n" + "-" * 55 + "\n")

    print("Done!")


if __name__ == "__main__":
    main()
