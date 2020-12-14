import m9g

m9g_module = "fs"


class Directory(m9g.Model):
    bucket = m9g.StringField()
    path = m9g.StringField()
    created = m9g.DateTimeField()  # TODO: default as function
    last_modified = m9g.DateTimeField()  # TODO: default as function

    subdirs = m9g.ListField(m9g.ReferenceField("fs.Directory"))
    files = m9g.ListField(m9g.ReferenceField("fs.File"))

    primary_key_fields = ("bucket", "path")


class File(m9g.Model):
    polymorphic_base = True
    bucket = m9g.StringField()
    path = m9g.StringField()
    created = m9g.DateTimeField()  # TODO: default as function
    last_modified = m9g.DateTimeField()  # TODO: default as function
    size = m9g.IntField(default=0)
    content = m9g.BytesField(default=b'')
    mimetype = m9g.StringField(allow_none=True)

    primary_key_fields = ("bucket", "path")


class TextFile(File):
    encoding = m9g.StringField()

    def get_text(self):
        return self.content.decode(self.encoding)


class ImageFile(File):
    image_size = m9g.TupleField([m9g.IntField, m9g.IntField])


class AudioFile(File):
    duration = m9g.FloatField()


class VideoFile(File):
    video_size = m9g.TupleField([m9g.IntField, m9g.IntField])
    duration = m9g.FloatField()
