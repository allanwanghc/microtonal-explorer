# Microtonal N-EDO Generator

A command-line tool for composers to explore microtonal tuning systems. Enter a frequency range and number of divisions, hear what N-EDO sounds like, and compare it to 12-EDO.

## Features

- Divide any frequency interval into N equal parts (N-EDO)
- When N > 12, automatically finds the nearest N-EDO pitches to a 12-division reference
- Plays ascending/descending sequences of the matched pitches
- Warm tone with ADSR envelope and light reverb
- Falls back to WAV file export if audio playback is unavailable

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 microtonal.py
```

You will be prompted for:

1. **Start frequency** (default: 440 Hz)
2. **End frequency** (default: 880 Hz)
3. **Number of divisions** (default: 13)

Then choose which sequences to play:

```
Play all N-EDO pitches? (y/n, default n):
Play ascending sequence (nearest to 12-division ref)? (y/n, default n):
Play descending sequence? (y/n, default n):
```

Frequency tables are always printed regardless of playback choices.

## Example

```
Start frequency (Hz, default 440): 440
End frequency (Hz, default 880): 880
Number of divisions (N, default 13): 19

Frequency ratio: 2.0000
Step ratio: 1.037155
Cents per step: 63.16
```

19-EDO is popular in the microtonal community because several of its pitches closely approximate just intonation intervals.

## License

MIT
