import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from frontend import mount_frontend
import hf_space

class Response:
    def __init__(self, payload=None, lines=(), status=200):
        self.payload, self.lines, self.status_code = payload, lines, status
    def raise_for_status(self): pass
    def json(self): return self.payload
    def iter_lines(self, **kwargs): return iter(self.lines)
    def __enter__(self): return self
    def __exit__(self, *args): pass

class DeploymentTests(unittest.TestCase):
    def test_api_precedes_spa_and_deep_navigation_works(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "index.html").write_text("<h1>CaseTwin</h1>")
            app=FastAPI()
            @app.get("/health")
            def health():return {"status":"ok"}
            with patch.dict(os.environ,{"FRONTEND_DIST":directory}):mount_frontend(app)
            client=TestClient(app)
            self.assertEqual(client.get("/health").json(),{"status":"ok"})
            self.assertIn("CaseTwin",client.get("/about").text)
            self.assertEqual(client.get("/missing.js").status_code,404)

    @patch("hf_space.space_url",return_value="https://models.example")
    @patch("hf_space.requests.post",return_value=Response({"event_id":"job"}))
    @patch("hf_space.requests.get",return_value=Response(lines=["event: heartbeat","data: null","event: complete",'data: [{"generated_text":"result"}]']))
    def test_gradio_sse_waits_for_completion(self,get,post,url):
        self.assertEqual(hf_space.generate(None,"prompt"),[{"generated_text":"result"}])
        self.assertEqual(post.call_args.kwargs["json"]["data"][0],"")

    @patch("hf_space.space_url",return_value="https://models.example")
    @patch("hf_space.requests.post",return_value=Response({"event_id":"job"}))
    @patch("hf_space.requests.get",return_value=Response(lines=["event: error",'data: "quota exceeded"']))
    def test_model_errors_do_not_become_fake_results(self,get,post,url):
        with self.assertRaises(RuntimeError):hf_space.generate(None,"prompt")

    @patch("hf_space.call_space",return_value={"image_embedding":[0.0]*1152})
    def test_zero_vectors_are_rejected(self,call):
        with self.assertRaises(RuntimeError):hf_space.embed_image(Image.new("RGB",(2,2)))

if __name__ == "__main__":unittest.main()
