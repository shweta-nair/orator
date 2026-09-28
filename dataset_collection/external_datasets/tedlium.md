# Adapting TED-LIUM

**Purpose here:** speech recognition / speech-representation context only
(spec section 16). It has real presentation-style speech (TED talks), but
**no presentation-quality labels** — do not treat "gave a TED talk" as a
proxy for "delivered it well."

Realistic uses in this project:

1. **Speech encoder sanity-checking.** Before running
   `training/models/speech_encoder.py` on your own recordings, run it on a
   few TED-LIUM clips first — it's a good way to confirm the encoder
   pipeline (resampling, feature extraction) works correctly on real
   long-form speech, since your own dataset will start small.
2. **Domain-adaptation pretraining**, if you have time: fine-tune a speech
   encoder on TED-LIUM's transcripts/audio pairs before fine-tuning again on
   your smaller labeled custom dataset — a standard way to get more out of
   a small labeled set. This is an optional stretch goal, not required for
   a first working pipeline.
3. Getting it: TED-LIUM is distributed via OpenSLR, in releases (v1/v2/v3),
   with an audio + transcript pairing per talk. I can't fetch it from this
   sandbox — search "TED-LIUM release download" and follow OpenSLR's
   instructions; the license permits research use.

Do not use TED-LIUM's transcripts as ground truth "correct scripts" for
script-accuracy training — those speakers aren't reading a script your
system provided, so there's no equivalent of your `script.txt` file for it.
