from pymongo.errors import DuplicateKeyError

from src.db.dao.RawTweetDAO import RawTweetDAO
from src.db.dao.UserHashtagDAO import UserHashtagDAO
from src.util.logging.Logger import Logger


class UserHashtagService:

    @classmethod
    def insert_hashtags_of_already_downloaded_tweets(cls):
        """ This methods run over all downloaded tweets until 21/05 and insert every hash tag
        which appear in a specific user.
        """
        # TODO activate this
        # thread = Thread(target=cls.insert_hashtags)
        # thread.start()
        cls.insert_hashtags()

    @classmethod
    def insert_hashtags(cls):
        """ """
        tweets_cursor = RawTweetDAO().get_all({"in_user_hashtag_collection": True})
        x = 0
        for tweet in tweets_cursor:
            cls.insert_hashtags_of_one_tweet(tweet)
            cls.get_logger().info(f'Tweets updated: {tweet["_id"]}')
            # RawTweetDAO().update_first({'_id': tweet['_id']}, {'in_user_hashtag_collection': True})
            if x % 10000 == 0:
                cls.get_logger().info(f'Tweets updated: {x}')


    @classmethod
    def insert_hashtags_of_one_tweet(cls, tweet):
        """ create (user, hashtag, timestap) pairs from a given tweet. """
        user_hashtags = tweet['entities']['hashtags']
        user = tweet['user_id']
        for hashtag in user_hashtags:
            try:
                timestamp = tweet['created_at']
                hashtag_text = hashtag['text'].lower()
                UserHashtagDAO().insert({
                    '_id': user + hashtag_text + timestamp,
                    'user': user,
                    'hashtag': hashtag_text,
                    'timestamp': timestamp
                })
            except DuplicateKeyError:
                cls.get_logger().info(f'Trying to insert duplicated pair: {user} - {hashtag_text}')

    @classmethod
    def get_logger(cls):
        return Logger('TweetUpdateService')
