# Adapting DAiSEE

**Purpose here:** visual-engagement experiments only (spec section 17).
DAiSEE labels are **engagement/boredom/confusion/frustration levels of
students watching video content** - not presentation delivery quality, and
not eye-contact-with-camera in the sense this project needs (its subjects
are watching something, not presenting to a camera).

**Do not** map DAiSEE's engagement labels directly onto this project's
`eye_contact` or `overall_delivery` targets - that would be using a proxy
label as if it were the real one, which the original spec explicitly warns
against.

Legitimate uses:

1. **Pretraining the visual encoder** on face/attention-related patterns
   before fine-tuning on your (much smaller) custom presentation dataset -
   a standard transfer-learning use, not a labeling shortcut.
2. As a **discussion point in your thesis** about the difference between
   "engagement while watching" and "presentation delivery while speaking" -
   useful to explicitly write up as a limitation/scoping decision.

Getting it: DAiSEE is available from its official project page/request form
(search "DAiSEE dataset request") - typically requires filling a form for
academic access. I can't fetch it from this sandbox.
