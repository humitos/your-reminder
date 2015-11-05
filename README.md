YourReminder
============


## Installation

```
pip install -r requirements.txt
```

Then run:

```
python scheduler.py --get-twitter-credentials
```

to authorize the YourReminder App into your Twitter account. Read and
Write permissions are needed.

## Tweet other stuff or adding more quotes

Copy `tweets.yaml.template` to `tweets.yaml` and edit it by respecting
the structure of categories/subcategories/schedule period and make
sure each tweet is no longer than 140 characters.

## Run it!

```
python scheduler.py
```

