"""Regression test for large AzuraCast station file listings."""
import importlib.util
import io
import json
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/deploy-geopolitica-oracle.py"
spec = importlib.util.spec_from_file_location("rdi_deploy_geopolitica", SCRIPT)
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class Response:
    def __init__(self, payload):
        self.source = io.BytesIO(payload)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.source.read(limit)


class AzuraCastClientTest(TestCase):
    def test_reads_full_media_json_larger_than_two_megabytes(self):
        files = [{"id": i, "path": f"music/track-{i:06d}.mp3"}
                 for i in range(55000)]
        payload = json.dumps(files).encode("utf-8")
        self.assertGreater(len(payload), 2_000_000)
        with patch.object(deploy.urllib.request, "urlopen", return_value=Response(payload)):
            result = deploy.Client("a" * 16 + ":" + "b" * 16).call(
                "GET", "/station/1/files"
            )
        self.assertEqual(len(result), len(files))
        self.assertEqual(result[-1]["id"], len(files) - 1)

    def test_invalid_media_json_has_an_explicit_error(self):
        with patch.object(deploy.urllib.request, "urlopen", return_value=Response(b'{"broken":')):
            with self.assertRaisesRegex(RuntimeError, "returned invalid JSON"):
                deploy.Client("a" * 16 + ":" + "b" * 16).call(
                    "GET", "/station/1/files"
                )


if __name__ == "__main__":
    main()
