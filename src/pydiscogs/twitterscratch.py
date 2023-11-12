import os
from datetime import datetime, timedelta

import tweepy

twitter = tweepy.Client(
    bearer_token=os.environ["TWITTER_BEARER_TOKEN"], wait_on_rate_limit=True
)


# Function to return yesterday's date in YYYY-MM-DDTHH:mm:ssZ format
def get_yesterday():
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%dT%H:%M:%SZ")


# Function to return timestamp of 1 hour ago in the YYYY-MM-DDTHH:mm:ssZ format
def get_hour_ago():
    hour_ago = datetime.now() - timedelta(hours=1)
    return hour_ago.strftime("%Y-%m-%dT%H:%M:%SZ")


# Function to get the top tweets from a user over the past 24 hours
# not including retweets or replies, and the count of likes and retweets
def get_top_tweets(user, count=10):
    tweets = twitter.search_recent_tweets(
        f"from:{user} -is:retweet -is:reply",
        start_time=get_yesterday(),
        end_time=get_hour_ago(),
        max_results=count,
        expansions="author_id,referenced_tweets.id,attachments.media_keys",
        tweet_fields="created_at,public_metrics",
        user_fields="username",
        media_fields="duration_ms,height,media_key,preview_image_url,type,url,width",
    )
    return tweets


# Function to print items from a list on separate lines with separators
def print_list(list, separator="\n"):
    for item in list:
        print(f"###TWEET###\n{item.public_metrics}\n{item}\n\n", end=separator)


# Function to sort a list of tweets by number of likes
def sort_by_likes(tweets):
    return sorted(
        tweets, key=lambda tweet: tweet.public_metrics["like_count"], reverse=True
    )


print_list(sort_by_likes(get_top_tweets("charlieINTEL").data))
