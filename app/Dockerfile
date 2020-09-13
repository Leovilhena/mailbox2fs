FROM python:3.8-alpine

LABEL maintainer="Leonardo Silva Vilhena <leosvilhena@icloud.com>"

RUN set -x \
    && addgroup -g 101 -S python \
    && adduser -S -D -H -u 101 -h /usr/src/app -s /sbin/nologin -G python -g python python \
    && mkdir /mailbox \
    && chown python:python /mailbox \
    && chmod 777 /mailbox

WORKDIR /usr/src/app

COPY --chown=python:python main.py .

USER python:python

CMD [ "python", "./main.py" ]
