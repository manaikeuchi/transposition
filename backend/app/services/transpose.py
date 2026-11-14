from pathlib import Path
from typing import Tuple

from music21 import converter
from music21 import key
from music21 import pitch
from music21 import stream


def load_score(musicxml_path: Path) -> stream.Score:
    return converter.parse(str(musicxml_path))


def analyze_key(score: stream.Score) -> key.Key:
    return score.analyze("key")


def semitones_to_reach_key(original_tonic: pitch.Pitch, target_key_name: str) -> int:
    """Smallest signed semitone shift (-6..+6) moving original_tonic's pitch class to target."""
    target_pitch = pitch.Pitch(target_key_name)
    diff = (target_pitch.pitchClass - original_tonic.pitchClass) % 12
    if diff > 6:
        diff -= 12
    return diff


def transpose_by_semitones(score: stream.Score, semitones: int) -> stream.Score:
    return score.transpose(semitones)


def transpose_score(
    score: stream.Score,
    mode: str,
    semitones: int = None,
    target_key_name: str = None,
) -> Tuple[stream.Score, int]:
    """Transpose score per the request, returning (new_score, semitones_applied)."""
    if mode == "semitones":
        n = int(semitones or 0)
        return transpose_by_semitones(score, n), n

    if mode == "key":
        if not target_key_name:
            raise ValueError("target_key is required when mode is 'key'")
        original_key = analyze_key(score)
        n = semitones_to_reach_key(original_key.tonic, target_key_name)
        return transpose_by_semitones(score, n), n

    raise ValueError(f"unknown transpose mode: {mode}")
