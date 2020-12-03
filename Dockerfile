FROM python:3.9

ENV GUNICORN_WORKERS 1
ENV GUNICORN_WORKER_CLASS "gevent"
ENV GUNICORN_WORKER_CONNECTIONS "100"
ENV GUNICORN_MAX_REQUESTS "50000"
ENV GUNICORN_ACCESSLOG -

RUN apt-get install -y tzdata
RUN pip install --no-cache-dir Flask \
                               gunicorn[gevent] \
                               requests \
                               environs

RUN pip install --no-cache-dir m9g
RUN pip install --no-cache-dir future_fstrings  # remove when fixed in m9g

# Installs some utils for debugging
ARG DEV_ENV="0"
RUN if [ $DEV_ENV -ne 0 ]; then pip install ipdb rpdb colorama pytest pytest-cov responses; fi

ENV BUCKETS "bucket1:/dir1,bucket2:/dir2"
ENV DEV_ENV $DEV_ENV

ADD gunicorn.py server.py client.py fsmodel.py __init__.py .coveragerc /usr/local/app/

ADD tests/ /usr/local/app/tests

WORKDIR /usr/local

EXPOSE 8000

CMD ["/usr/local/bin/gunicorn", "--config", "/usr/local/app/gunicorn.py", "-b", ":8000", "app.server:app"]
