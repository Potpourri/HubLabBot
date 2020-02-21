FROM potpourri/hublabbot

COPY hublabbot.json /opt/hublabbot/

# Pass Heroku http port to hublabbot
ENTRYPOINT ["/bin/sh", "-c"]
CMD ["HUBLABBOT_PORT=$PORT exec hublabbot"]
