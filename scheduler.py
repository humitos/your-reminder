#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © 2015 Manuel Kaufmann.

# This program is based on https://github.com/jjconti/saer-tweets


import os
import sys
import pytz
import yaml
import time
import datetime
from dateutil.relativedelta import relativedelta

from twitter import *
from config import CONSUMER_KEY, CONSUMER_SECRET

from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler


TIMEZONE = pytz.timezone('America/Lima')
OAUTH_FILENAME = os.environ.get(
    'HOME',
    os.environ.get('USERPROFILE', '')
) + os.sep + '.twitter_your_reminder_oauth'
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MEDIA_DIR = os.path.join(BASE_DIR, 'media')
TWEETS_YAML = os.path.join(BASE_DIR, 'tweets.yaml')
PERIOD_ARG = {
    'once': None,
    'hourly': 'hours',
    'daily': 'days',
    'weekly': 'weeks',
    'monthly': 'months',
    'yearly': 'years',
}


def get_twitter_credentials():
    if not os.path.exists(OAUTH_FILENAME):
        oauth_dance(
            "YourReminder",
            CONSUMER_KEY,
            CONSUMER_SECRET,
            OAUTH_FILENAME,
        )

    return read_token_file(OAUTH_FILENAME)


def publish_images(content, filenames):
    oauth_token, oauth_token_secret = get_twitter_credentials()
    auth = OAuth(
        oauth_token,
        oauth_token_secret,
        CONSUMER_KEY,
        CONSUMER_SECRET
    )
    twitter_upload = Twitter(auth=auth, domain='upload.twitter.com')

    id_imgs = []
    for f in filenames:
        with open(os.path.join(MEDIA_DIR, f), 'rb') as imagefile:
            imagedata = imagefile.read()
        id_img = twitter_upload.media.upload(media=imagedata)['media_id_string']
        id_imgs.append(id_img)

    twitter = Twitter(auth=auth, domain='api.twitter.com')
    twitter.statuses.update(status=content, media_ids=','.join(id_imgs))


def publish(content):
    oauth_token, oauth_token_secret = get_twitter_credentials()
    auth = OAuth(
        oauth_token,
        oauth_token_secret,
        CONSUMER_KEY,
        CONSUMER_SECRET
    )
    twitter = Twitter(auth=auth, domain='api.twitter.com')
    # TODO: handle every possible error here
    response = twitter.statuses.update(status=content)


def add_job(scheduler, trigger_type, func, **kwargs):
    scheduler.add_job(
        func,
        trigger_type,
        **kwargs
    )


def log_job(event):
    job = scheduler.get_job(event.job_id)
    print('* JOB_EXECUTED * {}: "{}" - "{}"'.format(datetime.datetime.now(), job.name, job.args))
    if event.exception:
        print('* Exception * {}'.format(event.exception))


if __name__ == '__main__':
    if '--get-twitter-credentials' in sys.argv:
        get_twitter_credentials()
        sys.exit(0)

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_listener(log_job, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    data = yaml.load(open(TWEETS_YAML))
    for category in data:
        for subcategory in data[category]:
            for period in data[category][subcategory]:
                if data[category][subcategory][period] is None:
                    # exclude categories with no tweets
                    continue

                # README: exclude 'strict' tweets when calculated
                # interval period for _no_ 'strict' ones
                tweets_for_period = []
                for tweet in data[category][subcategory][period]:
                    if not tweet.get('strict', False):
                        tweets_for_period.append(tweet)
                nro_tweets_for_period = len(tweets_for_period)

                for i, tweet in enumerate(data[category][subcategory][period]):
                    content = tweet['content']

                    if period == 'once':
                        args = ['date', publish]
                        kwargs = {
                            'args': [content],
                            'run_date': tweet['date']
                            # 'timezone': timezone,
                        }
                    else:
                        now = datetime.datetime.now()
                        time_period = PERIOD_ARG[period]

                        if tweet.get('strict', False):
                            # respect the period as it is
                            args = ['interval', publish]
                            kwargs = {
                                'args': [content],
                                time_period: 1,
                                # 'timezone': timezone,
                            }

                            for attr in ('start_date', 'end_date'):
                                if tweet.get(attr, False):
                                    kwargs[attr] = tweet[attr]
                        else:
                            # TODO: if the tweet already has
                            # 'start_date' we need to adds to this
                            # calculation
                            start_date = now + relativedelta(**{time_period: i+1})

                            args = ['interval', publish]
                            kwargs = {}
                            # TODO: handle other cases here
                            if period == 'monthly':
                                kwargs['weeks'] = nro_tweets_for_period * 4
                            else:
                                kwargs[time_period] = nro_tweets_for_period

                            kwargs.update({
                                'args': [content],
                                'start_date': start_date,
                                # 'timezone': timezone,
                            })

                    if tweet.get('media', False):
                        args[1] = publish_images
                        kwargs['args'].append(tweet['media'])
                    add_job(scheduler, *args, **kwargs)
    try:
        scheduler.start()
        jobs = scheduler.get_jobs()

        print('\nNOW: {}'.format(datetime.datetime.now()))
        print('NEXT 5/({}) TWEET to publish:'.format(len(jobs)))
        for job in jobs[:5]:
            print('{}: "{}" - {} ...'.format(
                job.next_run_time,
                job.name,
                job.args[0][:50].replace('\n', '\\n'))
            )

        print('{}: Press Ctrl+C to exit'.format(now), end='\n\n')

        while True:
            time.sleep(2)

    except (KeyboardInterrupt, SystemExit):
        print('Finishing scheduler...')
        print('Bye.')
