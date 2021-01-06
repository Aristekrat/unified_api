FROM python:3.7

ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN rm /tmp/requirements.txt

ADD .env /opt/.env
ADD config /opt/config
ADD unifiedpost /opt/unifiedpost

ENV PYTHONPATH /opt/unifiedpost
WORKDIR /opt

EXPOSE 8080

ENTRYPOINT ["python", "-m", "unifiedpost", "--env=prod"]