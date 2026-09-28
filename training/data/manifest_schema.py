"""Defines the manifest CSV schema every dataset (custom-recorded or
adapted public) must be normalized into before training.

One row = one recording (one participant doing one scenario once).
"""

REQUIRED_COLUMNS = [
    "participant_id",     # str — used for participant-level splitting, never
                           # split clips from the same participant across train/test
    "presentation_id",    # str — unique recording id
    "scenario",           # str — academic | news | flight | advertisement | speech
    "speech_feature_path",  # path to precomputed speech embedding (.npy), or raw audio path
    "visual_feature_path",  # path to precomputed per-frame visual embeddings (.npy)
    "transcript",          # str — recognized or ground-truth transcript
    "script",               # str — expected script
]

# Human-rated target columns (spec section 12). Not all need to be present —
# datasets/dataset.py drops columns that are entirely NaN for a given split
# and the assessment head is sized to whatever targets are available.
TARGET_COLUMNS = [
    "fluency",
    "pronunciation",
    "script_accuracy",
    "eye_contact",
    "posture",
    "gesture_activity",
    "overall_delivery",
]
