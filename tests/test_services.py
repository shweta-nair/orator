"""Unit tests for the analysis services. Run from the project root:

    python -m unittest discover -s tests -v

They need only numpy + opencv (no Flask, no database).
"""
import importlib.util
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    """Import app/services/<name>.py without importing the Flask app package."""
    path = os.path.join(ROOT, "app", "services", f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


speech = load("speech_service")
fusion = load("fusion_service")
stats = load("stats_service")

SCRIPT = ("Good morning everyone. Today I am going to talk about the future of artificial "
          "intelligence. It is one of the most rapidly developing technologies in the world.")


class SpeechTests(unittest.TestCase):
    def test_spec_example_filler_words(self):
        r = speech.analyze_transcript("um today I am going to basically explain AI", "Hello there", 10)
        self.assertEqual(r["filler_breakdown"], {"um": 1, "basically": 1})
        self.assertEqual(r["filler_words"], 2)

    def test_fillers_that_are_part_of_the_script_are_not_counted(self):
        r = speech.analyze_transcript("so this is like a test", "So this is like a test", 10)
        self.assertEqual(r["filler_words"], 0)

    def test_script_accuracy_is_order_aware(self):
        self.assertEqual(speech.analyze_transcript(SCRIPT, SCRIPT, 30)["script_accuracy"], 100)
        shuffled = " ".join(reversed(SCRIPT.split()))
        self.assertLess(speech.analyze_transcript(shuffled, SCRIPT, 30)["script_accuracy"], 30)
        half = " ".join(SCRIPT.split()[:15])
        self.assertTrue(30 <= speech.analyze_transcript(half, SCRIPT, 30)["script_accuracy"] <= 60)

    def test_wpm_uses_real_duration(self):
        words = " ".join(["word"] * 120)
        self.assertEqual(speech.analyze_transcript(words, "", 60)["speaking_pace_wpm"], 120)
        self.assertIsNone(speech.analyze_transcript(words, "", 0)["speaking_pace_wpm"])
        self.assertIsNone(speech.analyze_transcript(words, "", 1.5)["speaking_pace_wpm"])

    def test_empty_transcript_gives_no_metrics(self):
        r = speech.analyze_transcript("", SCRIPT, 30)
        for key in ("script_accuracy", "speaking_pace_wpm", "fluency", "filler_words"):
            self.assertIsNone(r[key])


class FusionTests(unittest.TestCase):
    SPEECH = {"word_count": 200, "script_accuracy": 80, "speaking_pace_wpm": 135, "fluency": 90, "filler_words": 2}
    VISUAL = {"eye_contact": 80}

    def test_weighted_formula(self):
        # 0.30*80 + 0.20*100 + 0.20*90 + 0.15*80 + 0.15*87.5 = 87.125
        self.assertEqual(fusion.fuse(self.SPEECH, self.VISUAL)["score"], 87)

    def test_missing_metrics_are_renormalised_not_faked(self):
        self.assertEqual(fusion.fuse(self.SPEECH, {})["score"], 88)
        self.assertEqual(fusion.fuse({}, self.VISUAL)["score"], 80)
        self.assertEqual(fusion.fuse({}, self.VISUAL)["based_on"], ["eye_contact"])
        self.assertIsNone(fusion.fuse({}, {})["score"])

    def test_pace_score(self):
        self.assertEqual(fusion.pace_score(130), 100)
        self.assertLess(fusion.pace_score(60), 30)
        self.assertLess(fusion.pace_score(220), 40)

    def test_feedback_only_uses_measured_values(self):
        notes = fusion.generate_feedback({"speaking_pace_wpm": 100, "script_accuracy": 90}, {})
        text = " ".join(notes)
        self.assertIn("100 WPM", text)
        self.assertIn("90%", text)
        self.assertNotIn("camera", text)

    def test_legacy_attempts_are_upgraded_without_debug_fields(self):
        old = {"transcript": "hi", "stages": {}, "temporal": {"available": False},
               "speech": {"wpm": 42, "script_accuracy_pct": 28, "fluency": 100, "filler_total": 0, "word_count": 48,
                          "model_stage": "rule_based_transcript"},
               "visual": {"eye_contact_proxy_pct": 100, "face_detection_rate_pct": 100, "frames_analyzed": 2,
                          "gesture_activity_level": "high", "model_stage": "cv_baseline"}}
        metrics, feedback = fusion.upgrade_legacy_metrics(old, 68.8)
        self.assertEqual(metrics["version"], fusion.REPORT_VERSION)
        self.assertEqual(metrics["speech"]["script_accuracy"], 28)
        self.assertIsNone(metrics["visual"]["gesture_activity"])
        self.assertNotIn("temporal", metrics)
        self.assertNotIn("stages", metrics)
        self.assertIsNotNone(metrics["overall"]["score"])
        self.assertTrue(feedback)


class StatsTests(unittest.TestCase):
    @staticmethod
    def attempt(i, score):
        return {"id": i, "status": "completed", "overall_score": score, "script_accuracy": 80,
                "speaking_pace_wpm": 120, "eye_contact": None, "fluency": 90}

    def test_dashboard_and_progress_agree(self):
        attempts = [self.attempt(1, 65), self.attempt(2, 78)]
        dash = stats.dashboard_stats(attempts, presentation_count=1)
        prog = stats.progress_stats(attempts)
        self.assertEqual((dash["presentation_count"], dash["practice_sessions"], dash["latest_score"]), (1, 2, 78))
        self.assertEqual([a["overall_score"] for a in prog["attempts"]], [65, 78])
        self.assertEqual((prog["latest_score"], prog["best_score"], prog["average_score"]), (78, 78, 72))
        self.assertIsNone(prog["average_eye_contact"])

    def test_empty(self):
        dash = stats.dashboard_stats([], 0)
        self.assertEqual((dash["practice_sessions"], dash["latest_score"], dash["recent"]), (0, None, []))
        self.assertEqual(stats.progress_stats([])["sessions"], 0)


class VisionTests(unittest.TestCase):
    def test_video_is_sampled_about_once_per_second(self):
        """Regression: the old code analysed only 2-4 frames of a one-minute recording."""
        import cv2
        import numpy as np
        vision = load("vision_service")
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "clip.avi")
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (320, 240))
            if not writer.isOpened():
                self.skipTest("this OpenCV build cannot write test videos")
            for i in range(150):  # 15 seconds at 10 fps
                frame = np.full((240, 320, 3), 60 + (i % 5), np.uint8)
                writer.write(frame)
            writer.release()
            result = vision.analyze_video(path, duration_hint=15.0)
        self.assertTrue(14 <= result["frames_analyzed"] <= 16, result)
        self.assertEqual(result["face_detection"], 0)
        self.assertIsNone(result["eye_contact"])       # no face -> not estimated, not 0
        self.assertEqual(result["gesture_activity"], "low")

    def test_unreadable_video_raises(self):
        vision = load("vision_service")
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "bad.webm")
            with open(path, "wb") as f:
                f.write(b"not a video")
            with self.assertRaises(ValueError):
                vision.analyze_video(path, 5)


if __name__ == "__main__":
    unittest.main()
