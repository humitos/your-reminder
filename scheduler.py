#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © 2015 Manuel Kaufmann.

# This program is based on https://github.com/jjconti/saer-tweets


import os
import sys
import yaml
import time
import datetime
import encodings
from daemonize import Daemonize
from dateutil.relativedelta import relativedelta

from twitter import *
from config import (
    TIMEZONE, MEDIA_DIR, TWEETS_YAML, PID_FILE,
    CONSUMER_KEY, CONSUMER_SECRET,
    SHOW_NEXT_TWEET_TO_PUBLISH,
)

from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler


OAUTH_FILENAME = os.environ.get(
    'HOME',
    os.environ.get('USERPROFILE', '')
) + os.sep + '.twitter_your_reminder_oauth'
PERIOD_ARG = {
    'once': None,
    'hourly': 'hours',
    'daily': 'days',
    'weekly': 'weeks',
    # these period are not supported by apscheduler; we need to
    # replace them by "weeks"
    'monthly': 'weeks',
    'yearly': 'weeks',
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
        with encodings.codecs.open(os.path.join(MEDIA_DIR, f), mode='rb') as imagefile:
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


# def log_job(event):
#     # TODO: send this also to a logging file. I want to know what was
#     # posted by YourReminder.
#     job = scheduler.get_job(event.job_id)
#     print('* JOB_EXECUTED * {}: "{}" - "{}"'.format(datetime.datetime.now(), job.name, job.args))
#     if event.exception:
#         print('* Exception * {}'.format(event.exception))


def main():
    if '--get-twitter-credentials' in sys.argv:
        get_twitter_credentials()
        sys.exit(0)

    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    # scheduler.add_listener(log_job, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    data = yaml.load(encodings.codecs.open(TWEETS_YAML, mode='r', encoding='utf-8'))
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
                        args = ['interval', publish]
                        kwargs = {}

                        starting_on = tweet.get('start_date', now)
                        start_date = starting_on + relativedelta(**{time_period: i+1})

                        if period == 'monthly':
                            multiplier = 4  # weeks
                        elif period == 'yearly':
                            # FIXME: how many weeks are in a year?
                            multiplier = 4 * 12  # weeks
                        else:
                            multiplier = 1
                        kwargs[time_period] = nro_tweets_for_period * multiplier

                        if tweet.get('strict', False):
                            # respect the period as it is
                            kwargs.update({
                                'args': [content],
                                time_period: multiplier,
                                # 'timezone': timezone,
                            })

                            for attr in ('start_date', 'end_date'):
                                if tweet.get(attr, False):
                                    kwargs[attr] = tweet[attr]
                        else:
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
        now = datetime.datetime.now(tz=TIMEZONE)
        print('\nNOW: {}'.format(now))
        print('NEXT {} ({}) TWEET to publish:'.format(SHOW_NEXT_TWEET_TO_PUBLISH, len(jobs)))

        for job in jobs[:SHOW_NEXT_TWEET_TO_PUBLISH]:
            print('{}: "{}" - {} ...'.format(
                job.next_run_time,
                job.name,
                job.args[0][:50].replace('\n', '\\n'))
            )

        print('Press Ctrl+C to exit', end='\n\n')

        while True:
            time.sleep(2)

    except (KeyboardInterrupt, SystemExit):
        print('Finishing scheduler...')
        print('Bye.')

if __name__ == '__main__':
    if '--daemon' in sys.argv:
        daemon = Daemonize(app='scheduler', pid=PID_FILE, action=main)
        daemon.start()
    else:
        main()
