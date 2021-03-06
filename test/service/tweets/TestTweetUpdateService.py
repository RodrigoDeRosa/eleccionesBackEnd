from unittest import mock

import mongomock

from src.db.Mongo import Mongo
from src.db.dao.RawFollowerDAO import RawFollowerDAO
from src.db.dao.RawTweetDAO import RawTweetDAO
from src.service.credentials.CredentialService import CredentialService
from src.service.hashtags.HashtagCooccurrenceService import HashtagCooccurrenceService
from src.service.hashtags.HashtagOriginService import HashtagOriginService
from src.service.tweets.TweetUpdateService import TweetUpdateService
from src.util.concurrency.AsyncThreadPoolExecutor import AsyncThreadPoolExecutor
from src.util.slack.SlackHelper import SlackHelper
from src.util.twitter.TwitterUtils import TwitterUtils
from test.helpers.TweetUpdateHelper import TweetUpdateHelper
from test.meta.CustomTestCase import CustomTestCase


class TestTweetUpdateService(CustomTestCase):

    def setUp(self) -> None:
        super(TestTweetUpdateService, self).setUp()
        # We need this to avoid mocking some object creations
        Mongo().db = mongomock.database.Database(mongomock.MongoClient(), 'elections', _store=None)

    def test_get_formatted_date_invalid_date(self):
        date = TweetUpdateService.get_formatted_date('123123')

        assert date is None

    def test_check_if_continue_downloading_return_false(self):
        tweet = TweetUpdateHelper().get_mock_tweet_may_24_follower_1()
        min_date = TweetUpdateHelper().get_mock_min_date_may_25()

        result = TweetUpdateService.check_if_continue_downloading(tweet, min_date)

        assert result is False

    def test_check_if_continue_downloading(self):
        tweet = TweetUpdateHelper().get_mock_tweet_may_26_follower_1()
        min_date = TweetUpdateHelper().get_mock_min_date_may_25()

        result = TweetUpdateService.check_if_continue_downloading(tweet, min_date)

        assert result is True

    def test_check_if_continue_downloading_invalid_date(self):
        tweet = TweetUpdateHelper().get_mock_tweet_may_26_follower_1()
        min_date = TweetUpdateService.get_formatted_date('123123')

        result = TweetUpdateService.check_if_continue_downloading(tweet, min_date)

        assert result is False

    @mock.patch.object(RawTweetDAO, 'insert_tweet')
    def test_do_not_store_new_tweets(self, insert_mock):
        tweet2 = TweetUpdateHelper().get_mock_tweet_may_24_follower_1()
        download_tweets = [tweet2]
        min_date = TweetUpdateHelper().get_mock_min_date_may_25()

        TweetUpdateService.store_new_tweets(download_tweets, min_date)

        assert insert_mock.call_count == 0

    @mock.patch.object(RawTweetDAO, 'insert_tweet')
    @mock.patch.object(HashtagCooccurrenceService, 'process_tweet')
    @mock.patch.object(HashtagOriginService, 'process_tweet')
    def test_store_part_of_new_tweets(self, origin_mock, cooccurrence_mock, insert_mock):
        tweet1 = TweetUpdateHelper().get_mock_tweet_may_26_follower_1()
        tweet2 = TweetUpdateHelper().get_mock_tweet_may_24_follower_1()
        download_tweets = [tweet1, tweet2]
        min_date = TweetUpdateHelper().get_mock_min_date_may_25()

        TweetUpdateService.store_new_tweets(download_tweets, min_date)

        assert insert_mock.call_count == 1
        assert origin_mock.call_count == 1
        assert cooccurrence_mock.call_count == 1

    @mock.patch.object(RawTweetDAO, 'insert_tweet')
    @mock.patch.object(HashtagCooccurrenceService, 'process_tweet')
    @mock.patch.object(HashtagOriginService, 'process_tweet')
    def test_store_new_tweets(self, origin_mock, cooccurrence_mock, insert_mock):
        tweet1 = TweetUpdateHelper().get_mock_tweet_may_26_follower_1()
        tweet2 = TweetUpdateHelper().get_mock_tweet_may_24_follower_1()
        download_tweets = [tweet1, tweet2]
        min_date = TweetUpdateHelper().get_mock_min_date_may_24()

        TweetUpdateService.store_new_tweets(download_tweets, min_date)

        assert insert_mock.call_count == 2
        assert origin_mock.call_count == 2
        assert cooccurrence_mock.call_count == 2

    # @mock.patch.object(TwitterUtils, 'twitter', return_value={})
    # def test_download_tweets_with_no_results(self):
    #     follower = TweetUpdateHelper().get_mock_follower_1()
    #     is_first_request = True
    #     max_id = None
    #     twitter_mock = TwitterUtils().twitter_with_app_auth()
    #     TweetUpdateService.do_download_tweets_request(twitter_mock, follower, "timestamp", is_first_request, max_id)
    # 
    #     assert twitter_mock.call_count == 1

    @mock.patch.object(RawFollowerDAO, 'update_follower_data')
    @mock.patch.object(RawFollowerDAO, 'get', return_value=TweetUpdateHelper().get_mock_follower_private())
    def test_update_follower_with_no_tweets_private_user(self, get_mock, update_mock):
        TweetUpdateService.update_follower_with_no_tweets("dummyFollower")

        assert get_mock.call_count == 1
        assert update_mock.call_count == 0

    @mock.patch.object(RawFollowerDAO, 'update_follower_downloaded_on')
    @mock.patch.object(RawFollowerDAO, 'get', return_value=TweetUpdateHelper().get_mock_follower_not_private())
    def test_update_follower_with_no_tweets_not_private_user(self, get_mock, update_mock):
        TweetUpdateService.update_follower_with_no_tweets("dummyFollower")

        assert get_mock.call_count == 1
        assert update_mock.call_count == 1

    @mock.patch.object(RawFollowerDAO, 'update_follower_data')
    def test_update_follower_as_private(self, tag_mock):
        TweetUpdateService.update_follower_as_private("dummyFollower")

        assert tag_mock.call_count == 1

    @mock.patch.object(RawFollowerDAO, 'update_follower_data')
    def test_update_complete_follower(self, update_mock):
        tweet = TweetUpdateHelper().get_mock_tweet_may_26_follower_1()
        last_date = TweetUpdateHelper().get_mock_min_date_may_24()

        TweetUpdateService.update_complete_follower("dummyFollower", tweet, last_date)

        assert update_mock.call_count == 1

    @mock.patch.object(TwitterUtils, 'twitter', return_value={})
    @mock.patch.object(TweetUpdateService, 'do_download_tweets_request', return_value=[])
    def test_do_download_tweets_requests_with_no_results(self, download_tweets_mock, twitter_mock):
        follower = TweetUpdateHelper().get_mock_follower_1()
        is_first_request = True
        max_id = None

        result = TweetUpdateService().do_download_tweets_request(twitter_mock, follower, "timestamp", is_first_request,
                                                                 max_id)

        assert download_tweets_mock.call_count == 1
        assert len(result) == 0

    @mock.patch.object(TwitterUtils, 'twitter', return_value={})
    @mock.patch.object(TweetUpdateService, 'do_download_tweets_request',
                       return_value=[TweetUpdateHelper().get_mock_tweet_may_26_follower_1()])
    def test_do_download_tweets_requests_with_no_results(self, download_tweets_mock, twitter_mock):
        follower = TweetUpdateHelper().get_mock_follower_1()
        is_first_request = True
        max_id = None

        result = TweetUpdateService().do_download_tweets_request(twitter_mock, follower, "timestamp", is_first_request,
                                                                 max_id)
        assert download_tweets_mock.call_count == 1
        assert len(result) == 1

    @mock.patch.object(TwitterUtils, 'twitter', return_value={})
    @mock.patch.object(TweetUpdateService, 'do_download_tweets_request', return_value=[])
    def test_download_tweets_and_validate_with_no_results(self, download_tweets_mock, twitter_mock):
        follower = TweetUpdateHelper().get_mock_follower_1()
        follower_download_tweets = []
        min_tweet_date = TweetUpdateHelper().get_mock_min_date_may_25()
        is_first_request = True
        max_id = None

        TweetUpdateService().download_tweets_and_validate(twitter_mock, follower, min_tweet_date, is_first_request,
                                                          max_id)
        assert len(follower_download_tweets) == 0
        assert download_tweets_mock.call_count == 1

    @mock.patch.object(TwitterUtils, 'twitter', return_value={})
    @mock.patch.object(TweetUpdateService, 'do_download_tweets_request',
                       return_value=[TweetUpdateHelper().get_mock_tweet_may_26_follower_1()])
    def test_download_tweets_and_validate_with_results(self, download_tweets_mock, twitter_mock):
        follower = TweetUpdateHelper().get_mock_follower_1()
        min_tweet_date = TweetUpdateHelper().get_mock_min_date_may_25()
        is_first_request = True
        max_id = None

        result = TweetUpdateService().download_tweets_and_validate(twitter_mock, follower, min_tweet_date,
                                                                   is_first_request, max_id)
        assert len(result) == 1
        assert download_tweets_mock.call_count == 1
