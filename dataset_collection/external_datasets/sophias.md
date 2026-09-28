# Adapting SOPHIAS

**Purpose here:** the closest existing match to this project's actual
research question — presentation behavior, eye contact, filler words,
temporal behavior, and (per spec section 14) human evaluations, from a
public repository rather than an ad-hoc scrape.

Repository: https://github.com/dataGHIA/SOPHIAS

I could not fetch or inspect this repository from this sandbox (network
access here is restricted to a small allowlist that doesn't include
general GitHub content browsing for this purpose), so the following is
guidance on *how to adapt it*, not a confirmed description of its exact
file layout — check the repo's own README for the authoritative structure
and access process before assuming anything below matches it exactly.

1. Read the repo's README/access instructions directly - the project brief
   for this system explicitly says not to assume the full raw dataset is
   directly downloadable from GitHub. Some research datasets require a
   signed data-use agreement even when the code/annotations are public.
2. Once you have it, the adaptation work is mapping SOPHIAS's own column/
   label names onto this project's `manifest_schema.py` columns - a
   deliberate one-to-one mapping (e.g. their eye-contact annotation column
   becomes this project's `eye_contact` column), not a guess. Do this
   mapping explicitly in a small script under `scripts/` once you can see
   the real schema, rather than assuming it matches.
3. If SOPHIAS's own scoring scale differs from this project's 0-100 scale,
   rescale explicitly and note the transform in your thesis methodology
   section - this is exactly the kind of detail that should be
   reproducible from your code, not just described in prose.
4. Because this is the dataset most aligned with the actual research
   question, it's worth prioritizing over SpeechOcean762/TED-LIUM/DAiSEE if
   its access process is tractable on your timeline.
