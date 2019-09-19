FROM python:3.6.9

RUN pip install attrs toml
# XXX: Stop this after there is a pipenv version released after July 2019 when they've included the timeout environment variable
RUN pip install git+https://github.com/pypa/pipenv.git@3b9b7172293169ad5ce0b7be77e6f27e3dbcde7b

COPY pipenv_graph_to_build.py sort_pipfile_lock_graph.py /usr/bin/
RUN chmod a+x /usr/bin/*.py

RUN mkdir /io
WORKDIR /io
