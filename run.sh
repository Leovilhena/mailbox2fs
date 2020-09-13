#!/bin/bash

read -p "Enter Fastmail username: " FASTMAIL_USER
read -s -p "Enter Fastmail password: " FASTMAIL_PASSWD

export FASTMAIL_USER="${FASTMAIL_USER}"
echo -n "${FASTMAIL_PASSWD}" > ./.fmpasswd
docker-compose up --build

rm ./.fmpasswd
