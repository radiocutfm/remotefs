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
    bucket = m9g.StringField()
    path = m9g.StringField()
    created = m9g.DateTimeField()  # TODO: default as function
    last_modified = m9g.DateTimeField()  # TODO: default as function
    size = m9g.IntField(default=0)
    content = m9g.BytesField(default=b'')

    primary_key_fields = ("bucket", "path")
