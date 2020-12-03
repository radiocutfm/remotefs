# -*- coding: utf-8 -*-
import os
import datetime
import zoneinfo
# from flask import Flask, jsonify, request, abort, send_file
from flask import Flask, abort

import logging
from environs import Env

from .fsmodel import Directory, File

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

    def _get_files(self, bucket, path, full_path, dirs):
        ret = []
        for filename in os.listdir(full_path):
            is_dir = os.path.isdir(os.path.join(full_path, filename))
            if is_dir != dirs:
                continue
            ret.append((Directory if is_dir else File).thinRef(
                    bucket=bucket,
                    path=os.path.join(path, filename),
            ))
        return ret


class FileManager(BaseManager):
    def _build_object(self, bucket, path, full_path):
        if not os.path.isfile(full_path):
            abort(400, f"{bucket}/{path} is not a file!")

        stat = os.stat(full_path)

        return File.fromdb(
            bucket=bucket,
            path=path,
            created=datetime.datetime.fromtimestamp(stat.st_ctime, tz=UTC),
            last_modified=datetime.datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            size=stat.st_size,
            content=open(full_path, "rb").read()
        )


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
