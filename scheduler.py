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


def publish(content):
    log(content)
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


def log(content):
    print('{}: {}'.format(datetime.datetime.now(), content))


if __name__ == '__main__':
    if '--get-twitter-credentials' in sys.argv:
        get_twitter_credentials()
        sys.exit(0)

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
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
                        kwargs = {
                            'args': [content],
                            'run_date': tweet['date']
                            # 'timezone': timezone,
                        }

                        job = scheduler.add_job(
                            publish,
                            'date',
                            **kwargs
                        )
                    else:
                        now = datetime.datetime.now()
                        time_period = PERIOD_ARG[period]

                        if tweet.get('strict', False):
                            # respect the period as it is
                            kwargs = {}
                            kwargs.update({
                                'args': [content],
                                time_period: 1,
                                # 'timezone': timezone,
                            })

                            for attr in ('start_date', 'end_date'):
                                if tweet.get(attr, False):
                                    kwargs.update({attr: tweet[attr]})

                            job = scheduler.add_job(
                                publish,
                                'interval',
                                **kwargs
                            )
                        else:
                            # TODO: if the tweet already has
                            # 'start_date' we need to adds to this
                            # calculation
                            start_date = now + relativedelta(**{time_period: i+1})

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

                            job = scheduler.add_job(
                                publish,
                                'interval',
                                **kwargs
                            )

    try:
        scheduler.start()
        jobs = scheduler.get_jobs()

        print('\nNEXT 5/({}) TWEET to publish:'.format(len(jobs)))
        for job in jobs[:5]:
            print('{}: {} ...'.format(
                job.next_run_time,
                job.args[0][:50].replace('\n', '\\n'))
            )

        print('{}: Press Ctrl+C to exit'.format(now), end='\n\n')

        while True:
            time.sleep(2)

    except (KeyboardInterrupt, SystemExit):
        print('Finishing scheduler...')
        print('Bye.')
