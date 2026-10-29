#!/usr/bin/env python3
"""Unit tests for local-only Italian AV preview: NO actual downloads/streaming."""
from pathlib import Path
import sys
import unittest
import shutil
import subprocess
import tempfile
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_europa_av_preview import build_command


class LocalItalianAudioPreview(unittest.TestCase):
    def setUp(self):
        self.vs = [
            {"codec_type": "video", "index": 0},
            {"codec_type": "audio", "index": 1, "tags": {"language": "eng"}},
            {"codec_type": "audio", "index": 2, "tags": {"language": "ita"}},
        ]
        self.ass = [{"codec_type": "audio", "index": 0, "tags": {"language": "ita"}}]

    def test_separate_italian_track_replaces_original(self):
        item = {"audio_mode": "separate_it", "audio_offset_ms": 0}
        cmd = build_command(item, Path("/tmp/video-original.mp4"), Path("/tmp/italiano.aac"),
                            Path("/tmp/test-preview.mp4"), (949.0, self.vs, 949.5, self.ass))
        maps = [cmd[i+1] for i, word in enumerate(cmd) if word == "-map"]
        self.assertEqual(maps, ["0:v:0", "1:a:0"])
        self.assertNotIn("0:a:0", maps)
        self.assertIn("-itsoffset", cmd)
        self.assertIn("-n", cmd)
        self.assertNotIn("rtmp://", " ".join(cmd))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg mancante")
    def test_real_local_mix_uses_italian_audio_only(self):
        """Il tono 880 Hz IT sostituisce il tono 330 Hz originale."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "original.mp4"
            italian = root / "italiano.wav"
            output = root / "preview.mp4"
            original_cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=blue:s=160x90:r=15:d=2",
                "-f", "lavfi", "-i", "sine=frequency=330:duration=2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-shortest", str(original),
            ]
            it_cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=44100:duration=2",
                "-c:a", "pcm_s16le", str(italian),
            ]
            subprocess.run(original_cmd, check=True, timeout=20)
            subprocess.run(it_cmd, check=True, timeout=20)
            cmd = build_command(
                {"audio_mode": "separate_it", "audio_offset_ms": 0},
                original, italian, output,
                (2.0, self.vs, 2.0, self.ass),
            )
            subprocess.run(cmd, check=True, timeout=30)
            self.assertTrue(output.stat().st_size > 1000)
            output_audio = root / "out.wav"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-i", str(output), "-vn", "-ac", "1", "-ar", "44100",
                 "-c:a", "pcm_s16le", str(output_audio)], check=True, timeout=20
            )
            with wave.open(str(output_audio), "rb") as wf:
                frames = wf.readframes(wf.getnframes())
                rate = wf.getframerate()
            # Frequenza media stimata in una regione senza silenzi.
            import array
            sig = array.array("h")
            sig.frombytes(frames)
            start, end = int(rate * .35), int(rate * 1.35)
            changes = sum(1 for a,b in zip(sig[start:end], sig[start+1:end+1]) if a <= 0 < b)
            self.assertTrue(800 <= changes <= 960, f"IT 880 Hz non presente: {changes} cicli")

    def test_wrong_duration_fails_closed(self):
        item = {"audio_mode": "separate_it", "audio_offset_ms": 0}
        with self.assertRaisesRegex(ValueError, "non allineate"):
            build_command(item, Path("a.mp4"), Path("b.aac"), Path("preview.mp4"),
                          (120.0, self.vs, 90.0, self.ass))

    def test_embedded_italian_track_must_exist(self):
        item = {"audio_mode": "embedded_it", "audio_stream_index": 1}
        cmd = build_command(item, Path("video.mp4"), None, Path("preview.mp4"), (100, self.vs, 0, []))
        maps = [cmd[i+1] for i, word in enumerate(cmd) if word == "-map"]
        self.assertEqual(maps, ["0:v:0", "0:a:1"])
        item["audio_stream_index"] = 2
        with self.assertRaisesRegex(ValueError, "non esiste"):
            build_command(item, Path("video.mp4"), None, Path("preview.mp4"), (100, self.vs, 0, []))


if __name__ == "__main__":
    unittest.main()
