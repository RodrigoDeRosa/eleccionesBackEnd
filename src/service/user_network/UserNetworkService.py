import time

from twython import TwythonRateLimitError, TwythonAuthError

from src.db.dao.RawFollowerDAO import RawFollowerDAO
from src.db.dao.UsersFriendsDAO import UsersFriendsDAO
from src.exception.CredentialsAlreadyInUseError import CredentialsAlreadyInUseError
from src.model.Credential import Credential
from src.service.credentials.CredentialService import CredentialService
from src.util.concurrency.AsyncThreadPoolExecutor import AsyncThreadPoolExecutor
from src.util.InterleavedQueue import InterleavedQueue
from src.util.config.ConfigurationManager import ConfigurationManager
from src.util.logging.Logger import Logger
from src.util.twitter.TwitterUtils import TwitterUtils


class UserNetworkService:

    __parties = ['juntosporelcambio', 'frentedetodos', 'frentedespertar', 'consensofederal', 'frentedeizquierda']

    __pool = None
    __active_set = set()

    @classmethod
    def do_retrieval(cls):
        """ Use all possible credentials to download users' friends. """
        # Get credentials for service
        cls.get_logger().info('Starting user friends retrieval.')
        try:
            credentials = CredentialService().get_all_credentials_for_service(cls.__name__)
        except CredentialsAlreadyInUseError as caiue:
            cls.get_logger().error(caiue.message)
            return
        # Fill pool with users
        cls.__pool = InterleavedQueue(cls.retrieve_users_by_party())
        # Fill set of active users
        cls.populate_users_set()
        # Run follower update process
        AsyncThreadPoolExecutor().run(cls.retrieve_with_credential, credentials)
        cls.get_logger().info('Finished user friends retrieval.')

    @classmethod
    def retrieve_with_credential(cls, credential: Credential):
        """ Download users' friends with given credential. """
        user = cls.user_from_pool()
        while user:
            cls.store_active_friends_set(user, cls.active_friends(cls.user_friends(user.data, credential), cls.__active_set))
            cls.mark_as_used(user.data)
            user = cls.user_from_pool()

    @classmethod
    def retrieve_users_by_party(cls) -> dict:
        """ Retrieve users from database for friend downloading. """
        users_by_party = dict()
        for party in cls.__parties:
            documents = RawFollowerDAO().get_all({'is_private': False,
                                                  'has_tweets': True,
                                                  'retrieved_friends': False,
                                                  'probability_vector_support': {'$elemMatch': {'$gte': 0.8}},
                                                  'support': party,
                                                  'friends_count': {'$and': [{'$gt': 0}, {'$lt': 5000}]}},
                                                 {'_id': 1})
            users_by_party[party] = [document['_id'] for document in documents]
        return users_by_party

    @classmethod
    def populate_users_set(cls):
        """ Fill the active users set with the universe of users we care about. """
        documents = RawFollowerDAO().get_all({'is_private': False,
                                              'has_tweets': True,
                                              'probability_vector_support': {'$elemMatch': {'$gte': 0.8}},
                                              'friends_count': {'$and': [{'$gt': 0}, {'$lt': 5000}]}},
                                             {'_id': 1})
        cls.__active_set = {document['_id'] for document in documents}

    @classmethod
    def user_from_pool(cls):
        """ Get a user id from the pool to retrieve data. """
        return cls.__pool.pop()

    @classmethod
    def user_friends(cls, user_id: str, credential: Credential) -> set[str]:
        """ Retrieve user friend set. """
        return cls.do_download(user_id, -1, credential)

    @classmethod
    def active_friends(cls, friends: set[str], active_users: set[str]) -> set[str]:
        """ Intersect friends set with active users set. """
        return friends.intersection(active_users)

    @classmethod
    def store_active_friends_set(cls, user, active_friends: set[str]):
        """ Store set of active friends for given user in database. """
        UsersFriendsDAO().store_friends_for_user(user.data, user.key, active_friends)

    @classmethod
    def mark_as_used(cls, user_id: str):
        """ Update user document in DB to avoid retrieving again. """
        RawFollowerDAO().update_first({'_id': user_id}, {'$set': {'retrieved_friends': True}})

    @classmethod
    def do_download(cls, user_id: str, cursor: int, credential: Credential) -> set[str]:
        """ Use Twitter api to get all friends of the given user. """
        twitter = TwitterUtils.twitter(credential)
        try:
            # Do request
            response = twitter.get_friends_ids(user_id=user_id, stringify_ids=True, cursor=cursor)
        except TwythonRateLimitError:
            cls.get_logger().warning(f'Friends download limit reached for credential {credential.id}. Waiting.')
            time.sleep(ConfigurationManager().get_int('follower_download_sleep_seconds'))
            cls.get_logger().info(f'Friends download waiting done for credential {credential.id}. Resuming.')
            # Once we finished waiting, we try again
            return cls.do_download(user_id, cursor, credential)
        except TwythonAuthError:
            # This error means the user is private.
            RawFollowerDAO().mark_as_private(user_id)
            return set()
        # Extract list of friends
        friends = set(response['ids'])
        next_cursor = response['next_cursor']
        # Check if there are more friends to download
        if next_cursor == 0:
            return friends
        # If there are more friends do retrieval, join sets and return full set
        return friends.union(cls.do_download(user_id, next_cursor, credential))

    @classmethod
    def get_logger(cls):
        return Logger(cls.__name__)
