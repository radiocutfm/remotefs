from invoke import task, Collection
from py_docker_k8s_tasks import docker_tasks
from py_docker_k8s_tasks.docker_tasks import docker_exec
from py_docker_k8s_tasks.util_tasks import add_tasks

ns = Collection()
add_tasks(ns, docker_tasks)


@ns.add_task
@task
def gunicorn(c):
    docker_tasks.docker_exec(
        c, "/usr/local/bin/gunicorn --config /usr/local/app/gunicorn.conf.py "
        "--log-config /usr/local/app/logging.conf "
        "-b :8000 app.server:app"
    )


@ns.add_task
@task
def flask(c, port=8000):
    docker_exec(c, "flask run -h 0.0.0.0")


@ns.add_task
@task
def kill_flask(c):
    docker_exec(c, "killall flask")


@ns.add_task
@task
def test(c, coverage=False):
    docker_exec(c, "pytest -v {} --pyargs app".format(
        "--cov=app --cov-config=app/.coveragerc" if coverage else ""
    ))
