# Adapting SpeechOcean762

**Purpose here:** pronunciation scoring only (spec section 15) — an
auxiliary signal, not a general presentation dataset. It has no video, no
"presentation delivery" labels, and its speakers are reading isolated
sentences, not presenting.

I could not download this myself — my sandbox can't reach the hosts it's
distributed from. Steps to get it yourself:

1. Search for "SpeechOcean762 dataset download" — it's typically
   distributed via OpenSLR or a paired GitHub repo with a download script,
   under a research-use license. Check the license terms before using it in
   anything beyond a class project.
2. It ships as audio clips + a JSON/text file of per-word and per-phoneme
   pronunciation scores (typically 0-10 scale) from expert annotators.
3. To use it for pretraining/fine-tuning a pronunciation head in isolation
   (before your custom dataset exists):
   - Convert its per-utterance score to the 0-100 scale this project's
     `manifest_schema.py` uses (`score_100 = raw_score_0_10 * 10`).
   - Build a manifest with the same required columns, but leave
     `visual_feature_path` empty and only fill `speech_feature_path`
     (run `training/models/speech_encoder.py` over its audio) and
     `pronunciation` in the targets.
   - Train with `train_speech.py` using an experiment config that only
     targets `pronunciation` (add one to `training/config.py`) — this
     gives you a pronunciation-only baseline before you have enough of
     your own rated recordings to train that head from scratch.
4. **Do not** report a model trained/evaluated on SpeechOcean762 as
   evidence about presentation delivery — it measures phoneme-level
   pronunciation accuracy on read sentences, not delivery quality.
