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

Example estructure of `.yaml` file:
```
Category A:
  Subcategory AA:
    once:
      - date: 2015-11-10 22:15:30 GMT-5
        content: "I'm using YourReminder to tweet this."
  Subcategory AB:
    monthly:
      - content: "This tweet will be ran once each 2 months"
      - content: "This tweet will be ran once each 2 months"

Category B:
  Subcategory BB:
    daily:
      - strict: true  # this option is not implemented yet
        content: "This tweet will be posted once a day"

      - content: "Once each 2 days"
```

## Run it!

```
python scheduler.py
```

