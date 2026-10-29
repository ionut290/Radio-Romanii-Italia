#!/usr/bin/env python3
"""Unit tests for local-only Italian AV preview: NO actual downloads/streaming."""
from pathlib import Path
import sys
import unittest

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
