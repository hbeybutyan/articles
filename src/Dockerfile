FROM tiangolo/uwsgi-nginx-flask:python3.6

COPY ./requirements.txt /tmp
RUN pip3 install --upgrade pip \
  && pip3 install -r /tmp/requirements.txt

COPY ./app /app