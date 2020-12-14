import tempfile
import os
import random
import shutil
import time
import socket
import subprocess
import requests
from unittest import TestCase
from .. import client
from .. import fsmodel


class LiveServerTests(TestCase):
    flask_command = "/usr/local/bin/flask run -p {self.flask_port} --no-reload"
    LIVESERVER_TIMEOUT = 5

    def setUp(self):
        self.flask_port = random.randint(3000, 9999)
        self.flask = subprocess.Popen(
            self.flask_command.format(**locals()).split(),
            stdout=subprocess.DEVNULL,
            env={
                "BUCKETS": self.buckets,
                "FLASK_APP": f"app/server.py",
            },
        )
        self.addCleanup(self.flask.terminate)

        # We must wait for the server to start listening, but give up
        # after a specified maximum timeout
        timeout = self.LIVESERVER_TIMEOUT
        start_time = time.time()

        while True:
            elapsed_time = (time.time() - start_time)
            if elapsed_time > timeout:
                raise RuntimeError(
                    f"Failed to start the server after {timeout} seconds. "
                )

            if self._can_ping_server():
                break

        client.set_managers(self.server_url)

    def _can_ping_server(self):
        host, port = "localhost", self.flask_port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((host, port))
        except socket.error:
            success = False
        else:
            success = True
        finally:
            sock.close()

        return success

    @property
    def server_url(self):
        return f"http://localhost:{self.flask_port}"


class SampleFilesLiveServerTests(LiveServerTests):
    buckets = "samples:/usr/local/app/tests/files"

    def test_samplefiles(self):
        resp = requests.get(f"{self.server_url}/samples/directory/-root-/")
        assert resp.ok
        directory = fsmodel.Directory.deserialize_jsondict(resp.json())

        assert len(directory.files) == 3
        assert len(directory.subdirs) == 0

        directory.files.sort(key=lambda f: f.path)
        assert ["/preambulo.txt", "/radio_cut_64.png", "/radiocut-app-640x360.mp4"] == [
            f.path for f in directory.files
        ]
        assert isinstance(directory.files[0], fsmodel.TextFile)
        assert isinstance(directory.files[1], fsmodel.ImageFile)
        assert isinstance(directory.files[2], fsmodel.VideoFile)


class TempLiveServerTests(LiveServerTests):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tempdir))
        self.buckets = f"temp:{self.tempdir}"
        super().setUp()

    def test_get_directory(self):
        open(os.path.join(self.tempdir, "foo"), "wt").write("bar")
        open(os.path.join(self.tempdir, "foo2"), "wt").write("bar2")
        os.mkdir(os.path.join(self.tempdir, "foodir"))
        open(os.path.join(self.tempdir, "foodir/foo3"), "wt").write("bar3")

        resp = requests.get(f"{self.server_url}/temp/directory/-root-/")
        assert resp.ok
        directory = fsmodel.Directory.deserialize_jsondict(resp.json())

        assert len(directory.files) == 2
        assert len(directory.subdirs) == 1

        directory.files.sort(key=lambda f: f.path)
        assert ["/foo", "/foo2"] == [f.path for f in directory.files]
        assert directory.files[0].content == b"bar"
        assert directory.files[0].size == 3
        assert directory.files[1].content == b"bar2"
        assert directory.files[1].size == 4

        foodir = directory.subdirs[0]
        assert foodir.subdirs == []
        assert len(foodir.files) == 1
        assert foodir.files[0].content == b"bar3"

        resp = requests.get(f"{self.server_url}/temp/file/foodir/foo3/")
        json_resp = resp.content
        foo3 = fsmodel.File.deserialize_json(json_resp)

        assert foo3.content == b"bar3"

        resp = requests.get(f"{self.server_url}/temp/directory/foodir/foo3/")
        assert resp.status_code == 400

        resp = requests.get(f"{self.server_url}/temp/file/foodir/")
        assert resp.status_code == 400

        resp = requests.get(f"{self.server_url}/temp/directory/bar/")
        assert resp.status_code == 404

    def test_bucket_not_found(self):
        resp = requests.get(f"{self.server_url}/tempfoo/directory/-root-/")
        assert resp.status_code == 404
        assert b"Bucket tempfoo not found" in resp.content
