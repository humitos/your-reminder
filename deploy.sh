#!/bin/bash

rsync -rav --delete-after --copy-links media tweets.yaml humitos@mkaufmann.com.ar:~/your-reminder
ssh mkaufmann.com.ar 'cd your-reminder; kill `cat scheduler.pid`; /home/humitos/.virtualenvs/your-reminder/bin/python scheduler.py --daemon'
