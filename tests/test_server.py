import tempfile
import os
import shutil
from unittest import TestCase
from unittest.mock import patch
from .. import server
from .. import fsmodel


class ServerTests(TestCase):
    """
    These tests run in the same process with the server,
    so use the same manager. Lazy objects don't make new http requests when activated.

    Anyway they are fine to test flask code.
    """

    def setUp(self):
        super().setUp()
        server.app.config['TESTING'] = True
        self.client = server.app.test_client(use_cookies=False)

    def test_get_directory(self):
        tempdir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(tempdir))

        open(os.path.join(tempdir, "foo"), "wt").write("bar")
        open(os.path.join(tempdir, "foo2"), "wt").write("bar2")
        os.mkdir(os.path.join(tempdir, "foodir"))
        open(os.path.join(tempdir, "foodir/foo3"), "wt").write("bar3")

        with patch.dict(server.BUCKETS, {"temp": tempdir}):
            resp = self.client.get(f"/temp/directory/-root-/")
            json_resp = resp.get_data()

            directory = fsmodel.Directory.deserialize_json(json_resp)
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

            resp = self.client.get(f"/temp/file/foodir/foo3/")
            json_resp = resp.get_data()
            foo3 = fsmodel.File.deserialize_json(json_resp)

            assert foo3.content == b"bar3"

            resp = self.client.get(f"/temp/directory/foodir/foo3/")
            assert resp.status == "400 BAD REQUEST"

            resp = self.client.get(f"/temp/file/foodir/")
            assert resp.status == "400 BAD REQUEST"

            resp = self.client.get(f"/temp/directory/bar/")
            assert resp.status == "404 NOT FOUND"

    def test_bucket_not_found(self):
        resp = self.client.get(f"/temp/directory/-root-/")
        assert resp.status == "404 NOT FOUND"
        assert b"Bucket temp not found" in resp.get_data()