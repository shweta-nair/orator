# Presentation Coach (Orator)

A Flask + vanilla-JS web app for rehearsing presentations: you write a script,
practise with a teleprompter while the browser records camera + microphone, and
get a report with speech and visual metrics, an overall score and feedback.
History, Progress and the Dashboard are all built from the saved attempts.

Read `NEXT_STEPS.md` for the research plan (trained deep-learning models).

```
frontend/             the web UI (served by Flask at http://localhost:5000)
app/                  the Flask API + analysis services (this README)
tests/                unit tests for the analysis services (no Flask needed)
training/             PyTorch scaffolding for the future trained model (not used by the app)
dataset_collection/   protocol + scripts for collecting a training dataset
```

## Run it

```bash
pip install -r requirements.txt
python run.py            # http://localhost:5000  (SQLite database at instance/coach.db)
```

Nothing else has to be installed (no ffmpeg, no PyTorch): video is decoded by
OpenCV and speech is transcribed by the browser.

* Use **Chrome or Edge** - live transcription uses the browser's Web Speech
  API, which needs an internet connection. Without it the app still analyses
  the video, and the report says that no speech was recognised.
* Set `SECRET_KEY` (session cookie signing) outside development.
* `DATABASE_URL` switches to PostgreSQL (`pip install psycopg2-binary`).
* `CORS_ORIGINS` (comma separated) is only needed if the frontend is served
  from a different origin than the API.

Run the unit tests:

```bash
python -m unittest discover -s tests -v
```

## How the data flows

```
create presentation  ->  Presentation (title, scenario, difficulty, script, target duration)
        |
practise: browser records camera+mic into ONE WebM (MediaRecorder) and the
          transcript comes from speech recognition
        |  POST /api/presentations/<id>/attempts  (multipart: payload JSON + video)
        v
speech_service   transcript -> script accuracy, speaking pace (WPM), fluency, filler words
vision_service   video -> OpenCV samples ~1 frame/second -> face detection, eye contact
                 estimate, gesture activity (movement between frames)
fusion_service   weighted score over the metrics that exist + feedback text
        |
        v
Attempt row in the database  (the single source of truth)
        |
        +--> GET /api/attempts/<id>   report
        +--> GET /api/dashboard       presentations, practice sessions, latest score, recent activity
        +--> GET /api/history         presentations with all their attempts
        +--> GET /api/progress        averages, best/latest score, score-over-attempts
```

Dashboard, History, Progress and the Report all read the same stored attempts
(`Attempt.summary()` / `Attempt.to_dict()`), so they cannot disagree.

### Metrics (only what is actually measured)

| Metric | How it is computed |
|---|---|
| Script accuracy | word-level, order-aware match (difflib) between transcript and script, 0-100 |
| Speaking pace | transcript words / real recording duration in minutes (WPM) |
| Fluency | 100 minus a length-normalised penalty for filler words and repeated words |
| Filler words | um / uh / er / like / you know / actually / basically / so (words the script itself contains are not counted) |
| Eye contact (estimate) | % of sampled frames with a frontal face near the centre of the frame |
| Face detected | % of sampled frames with a frontal face (OpenCV Haar cascade) |
| Gesture activity | low / medium / high from how much the picture changes between sampled frames (a simple motion measure, not gesture recognition) |

A metric that cannot be computed is left out of the report; it is never
replaced by a placeholder.

**Overall score** = weighted average of the available components, with the
weights re-normalised over the ones that exist:
script accuracy 30 %, speaking pace 20 %, fluency 20 %, eye contact 15 %,
filler words 15 % (`fusion_service.WEIGHTS`). Pace scores 100 inside
120-150 WPM and loses 1.25 points per WPM outside it; the filler score falls
from 100 (no fillers) to 0 (8+ fillers per 100 words).

## Structure

```
app/
  __init__.py          app factory, DB init (+ small schema/data upgrade), CORS, blueprints
  models.py            User, Presentation, Attempt (SQLAlchemy)
  auth_utils.py        session-based @login_required decorator
  routes/
    auth.py            register / login / logout (clears the session) / me
    presentations.py   create / list / update / delete presentations
    attempts.py        submit a recording -> analyse -> save; list / read attempts
    stats.py           dashboard / history / progress
  services/            no Flask imports - callable and testable on their own
    speech_service.py  transcript metrics
    vision_service.py  video sampling + OpenCV face/motion analysis
    fusion_service.py  score, feedback, upgrade of old stored attempts
    stats_service.py   dashboard / progress aggregation
```

The services are deliberately modular: a trained speech model, a landmark/pose
model or an LSTM/GRU/Transformer over per-frame features can replace or extend
one of them without changing the routes, the database format or the UI.

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /api/auth/register | - | create account |
| POST | /api/auth/login | - | log in |
| POST | /api/auth/logout | - | log out (clears the session) |
| GET  | /api/auth/me | - | current session user (`{"user": null}` when signed out) |
| GET/POST | /api/presentations | yes | list / create |
| GET/PUT/DELETE | /api/presentations/:id | yes | manage one presentation |
| POST | /api/presentations/:id/attempts | yes | multipart: `payload` (JSON `transcript`, `duration_seconds`) + `video`; a plain JSON body without video is also accepted |
| GET  | /api/presentations/:id/attempts | yes | attempts of one presentation |
| GET  | /api/attempts/:id | yes | full report of one attempt |
| GET  | /api/dashboard | yes | counts, latest score, recent activity |
| GET  | /api/history | yes | presentations with their attempts |
| GET  | /api/progress | yes | averages, best/latest score, score series |

Report JSON:

```json
{ "id": 1, "presentation_id": 2, "duration_seconds": 66, "created_at": "...Z",
  "presentation": {"id": 2, "title": "...", "scenario": "academic"},
  "overall": {"score": 75, "based_on": ["script_accuracy", "speaking_pace", "fluency", "eye_contact", "filler_words"]},
  "speech": {"script_accuracy": 82, "speaking_pace_wpm": 118, "fluency": 91, "filler_words": 3, "filler_breakdown": {"like": 3}, "word_count": 240},
  "visual": {"eye_contact": 86, "face_detection": 94, "gesture_activity": "medium", "frames_analyzed": 62},
  "transcript": "...", "feedback": ["...", "..."] }
```

## Upgrading an existing database

On start-up the app adds the new `presentation.target_duration_minutes`
column if it is missing and converts attempts saved by the older version to
the current report format (their overall score and feedback are recomputed
with the current formula). No manual migration is needed.

## Not in this pass

Password change, email verification and rate limiting. The trained
deep-learning models are a separate research step (see `NEXT_STEPS.md`);
until one exists the app reports only what the rule-based / OpenCV analysis
actually measures.
