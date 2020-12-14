# -*- coding: utf-8 -*-
import os
import datetime
import zoneinfo
import mimetypes
# from flask import Flask, jsonify, request, abort, send_file
from flask import Flask, abort

import subprocess
import json
import logging
from environs import Env
import chardet

from .fsmodel import Directory, File, TextFile, ImageFile, AudioFile, VideoFile

app = Flask(__name__)
application = app

env = Env()

if "BUCKETS" not in app.config:
    BUCKETS = env.list("BUCKETS")
    BUCKETS = dict(x.split(":") for x in BUCKETS)
    app.config["BUCKETS"] = BUCKETS
else:
    BUCKETS = app.config["BUCKETS"]

UTC = zoneinfo.ZoneInfo("UTC")

for bucketname, dirname in BUCKETS.items():
    if not os.path.isdir(dirname):
        os.makedirs(dirname)


class BaseManager:
    def _full_path(self, bucket, path):
        if ".." in path:
            app.logger.warning(f"Invalid path '{path}' - bucket {bucket}!")
            abort(403, f"Invalid filename '{path}'!")

        path = path.lstrip("/")

        if bucket not in app.config["BUCKETS"]:
            app.logger.warning(f"Bucket {bucket} not found!")
            abort(404, f"Bucket {bucket} not found!")

        return os.path.join(app.config["BUCKETS"][bucket], path)

    def findByPrimaryKey(self, pk):
        bucket, path = pk

        full_path = self._full_path(bucket, path)
        if not os.path.exists(full_path):
            abort(404, f"{bucket}/{path} not found!")
        return self._build_object(bucket, path, full_path)


class DirectoryManager(BaseManager):
    def _build_object(self, bucket, path, full_path):
        if not os.path.isdir(full_path):
            abort(400, f"{bucket}/{path} is not a directory!")

        stat = os.stat(full_path)

        return Directory.fromdb(
            bucket=bucket,
            path=path,
            created=datetime.datetime.fromtimestamp(stat.st_ctime, tz=UTC),
            last_modified=datetime.datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            subdirs=self._get_files(bucket, path, full_path, dirs=True),
            files=self._get_files(bucket, path, full_path, dirs=False),
        )

    def get_file_class(self, full_filename):
        mimetype, _ = mimetypes.guess_type(full_filename)
        if not mimetype:
            return File
        if mimetype.startswith("text/"):
            return TextFile
        elif mimetype.startswith("image/"):
            return ImageFile
        elif mimetype.startswith("video/"):
            return VideoFile
        return File

    def _get_files(self, bucket, path, full_path, dirs):
        ret = []
        for filename in os.listdir(full_path):
            full_filename = os.path.join(full_path, filename)
            is_dir = os.path.isdir(full_filename)
            if is_dir != dirs:
                continue
            if is_dir:
                model_class = Directory
            else:
                model_class = self.get_file_class(full_filename)
            ret.append(model_class.thinRef(
                    bucket=bucket,
                    path=os.path.join(path, filename),
            ))
        return ret


class FileManager(BaseManager):
    def _build_object(self, bucket, path, full_path):
        if not os.path.isfile(full_path):
            abort(400, f"{bucket}/{path} is not a file!")

        mimetype, _ = mimetypes.guess_type(full_path)
        content = open(full_path, "rb").read()
        stat = os.stat(full_path)
        file_class = File
        kwargs = {}
        if mimetype and mimetype.startswith("text/"):
            file_class = TextFile
            detection = chardet.detect(content)
            if detection["confidence"] > 0.8:
                kwargs["encoding"] = detection["encoding"]
            else:
                kwargs["encoding"] = "utf-8"
        elif mimetype and mimetype.startswith("image/"):
            file_class = ImageFile
            image_data = self._ffprobe(full_path)
            kwargs["image_size"] = image_data["streams"][0]["width"], image_data["streams"][0]["height"]
        elif mimetype and mimetype.startswith("video/"):
            file_class = VideoFile
            video_data = self._ffprobe(full_path)
            kwargs["duration"] = float(video_data["format"]["duration"])
            kwargs["video_size"] = image_data["streams"][0]["width"], image_data["streams"][0]["height"]

        return file_class.fromdb(
            bucket=bucket,
            path=path,
            created=datetime.datetime.fromtimestamp(stat.st_ctime, tz=UTC),
            last_modified=datetime.datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            mimetype=mimetype,
            content=content,
            size=stat.st_size,
            **kwargs
        )

    def _ffprobe(self, filename):
        out = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filename],
            stdout=subprocess.PIPE
        )
        return json.loads(out.stdout)


def set_managers():
    Directory.manager = DirectoryManager()
    File.manager = FileManager()


set_managers()


def _model_response(obj):
    return app.response_class(
        response=obj.serialize_json(),
        status=200,
        mimetype="application/json"
    )


@app.route('/<bucket>/directory/<path:dirname>/', methods=["GET"])
def get_directory(bucket, dirname):
    if dirname == "-root-":
        dirname = "/"
    directory = Directory.manager.findByPrimaryKey((bucket, dirname))
    return _model_response(directory)


@app.route('/<bucket>/file/<path:dirname>/', methods=["GET"])
def get_file(bucket, dirname):
    file = File.manager.findByPrimaryKey((bucket, dirname))
    return _model_response(file)


# Conecta el log de Flask con el de Gunicorn
if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
