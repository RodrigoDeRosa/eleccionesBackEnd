import mongomock
from datetime import datetime
from src.db.Mongo import Mongo
from src.db.dao.RawFollowerDAO import RawFollowerDAO
from src.exception.NoDocumentsFoundError import NoDocumentsFoundError
from src.exception.NonExistentRawFollowerError import NonExistentRawFollowerError
from src.model.followers.RawFollower import RawFollower
from src.util.CSVUtils import CSVUtils
from test.meta.CustomTestCase import CustomTestCase


class TestRawFollowerDAO(CustomTestCase):

    def setUp(self) -> None:
        super(TestRawFollowerDAO, self).setUp()
        Mongo().db = mongomock.database.Database(mongomock.MongoClient(), 'elections', _store=None)
        self.target = RawFollowerDAO()

    def tearDown(self) -> None:
        # This has to be done because we are testing a Singleton
        RawFollowerDAO._instances.clear()

    def test_put_new_raw_follower(self):
        date = datetime.strptime('1996-03-15', CSVUtils.DATE_FORMAT)
        raw_follower = RawFollower(**{'id': 'test', 'downloaded_on': date, 'follows': 'bodart'})
        self.target.put(raw_follower)
        stored = self.target.get('test')
        assert stored is not None
        assert stored.follows == ['bodart']
        assert stored.downloaded_on == date
        assert not stored.is_private

    def test_update_raw_follower(self):
        date = datetime.strptime('1996-03-15', CSVUtils.DATE_FORMAT)
        raw_follower = RawFollower(**{'id': 'test', 'downloaded_on': date, 'follows': 'bodart'})
        self.target.put(raw_follower)
        raw_follower = RawFollower(**{'id': 'test', 'downloaded_on': date, 'follows': 'the_commander'})
        self.target.put(raw_follower)
        stored = self.target.get('test')
        assert stored is not None
        assert 'bodart' in stored.follows
        assert 'the_commander' in stored.follows
        assert stored.downloaded_on == date

    def test_get_non_existent_raw_follower(self):
        with self.assertRaises(NonExistentRawFollowerError) as context:
            _ = self.target.get('test')
        assert context.exception is not None
        assert context.exception.message == "There is no raw follower with id 'test' in the database."

    def test_finish_candidate_check_if_was_loaded(self):
        self.target.finish_candidate('test')
        assert self.target.candidate_was_loaded('test')

    def test_candidate_was_loaded_false(self):
        assert not self.target.candidate_was_loaded('test')

    def test_get_candidates_followers_ids(self):
        for i in range(20):
            self.target.put(RawFollower(**{'id': i, 'follows': 'bodart'}))
        result = self.target.get_candidate_followers_ids('bodart')
        assert len(result) == 20
        assert {i for i in range(20)} == result

    def test_put_public_on_private_user_stays_private(self):
        private_follower = RawFollower(**{'id': 'test', 'is_private': True})
        self.target.put(private_follower)
        public_follower = RawFollower(**{'id': 'test'})
        self.target.put(public_follower)
        stored = self.target.get('test')
        assert stored is not None
        assert stored.is_private

    def test_tag_as_private_ok(self):
        public_follower = RawFollower(**{'id': 'test'})
        self.target.put(public_follower)
        self.target.tag_as_private(public_follower)
        stored = self.target.get('test')
        assert stored.is_private

    def test_get_public_users(self):
        private_follower = RawFollower(**{'id': 'test_1', 'is_private': True})
        self.target.put(private_follower)
        public_follower = RawFollower(**{'id': 'test_2'})
        self.target.put(public_follower)
        stored = self.target.get_public_users()
        assert stored is not None
        assert stored == {'test_2'}

    def test_get_public_users_empty(self):
        # This should never happen anyway
        private_follower = RawFollower(**{'id': 'test_1', 'is_private': True})
        self.target.put(private_follower)
        stored = self.target.get_public_users()
        assert not stored

    def test_get_all_with_cursor(self):
        # Add many followers
        for i in range(0, 20):
            self.target.put(RawFollower(**{'id': i}))
        # Get first 10
        first_10 = self.target.get_all_with_cursor(0, 10)
        assert len(first_10) == 10
        for follower in first_10:
            assert follower['id'] < 10
        # Get last 10
        last_10 = self.target.get_all_with_cursor(10, 10)
        assert len(last_10) == 10
        for follower in last_10:
            assert 10 <= follower['id'] < 20
        # Check there are no overlaps
        assert {follower['id'] for follower in last_10}.intersection({follower['id'] for follower in first_10}) == set()

    def test_get_following_with_cursor(self):
        # Add many followers
        for i in range(0, 20):
            if i % 2 == 0:
                follower = RawFollower(**{'id': i, 'follows': 'bodart'})
            else:
                follower = RawFollower(**{'id': i, 'follows': 'the_commander'})
            self.target.put(follower)
        # Get first 10
        first_10 = self.target.get_following_with_cursor('bodart', 0, 100)
        assert len(first_10) == 10
        assert {follower['id'] for follower in first_10} == {i for i in range(0, 20) if i % 2 == 0}
        # Check there are only 10
        next_followers = self.target.get_following_with_cursor('bodart', 10, 10)
        assert len(next_followers) == 0

    def test_get_following_with_cursor_non_existent_candidate_raises_exception(self):
        with self.assertRaises(NoDocumentsFoundError) as context:
            _ = self.target.get_following_with_cursor('bodart', 0, 100)
        assert context.exception is not None
        message = 'No documents found on collection raw_followers with query screen_name=bodart.'
        assert context.exception.message == message
