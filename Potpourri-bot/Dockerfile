ARG HUBLABBOT_VERSION=latest
FROM potpourri/hublabbot:$HUBLABBOT_VERSION

COPY hublabbot.json /opt/hublabbot/

# Pass Heroku http port to hublabbot
ENTRYPOINT ["/bin/sh", "-c"]
CMD HUBLABBOT_PORT=$PORT exec hublabbot
