import io
import os
import tempfile
import unittest
from unittest.mock import patch

from application import application


class PhotoShareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"LOCAL_UPLOAD_DIR": self.temp.name, "EFS_ID": ""})
        self.env.start()
        self.client = application.test_client()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_upload_and_gallery(self):
        payload = {"photo": (io.BytesIO(b"demo-data"), "example.png", "image/png")}
        response = self.client.post("/upload", data=payload, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 303)
        gallery = self.client.get("/")
        self.assertEqual(gallery.status_code, 200)
        self.assertIn(b"example.png", gallery.data)

    def test_rejects_wrong_extension(self):
        payload = {"photo": (io.BytesIO(b"bad"), "malware.exe", "application/octet-stream")}
        response = self.client.post("/upload", data=payload, content_type="multipart/form-data")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
