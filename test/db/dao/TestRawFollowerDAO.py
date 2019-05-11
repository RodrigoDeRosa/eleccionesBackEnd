import mongomock
from datetime import datetime
from unittest import TestCase
from src.db.Mongo import Mongo
from src.db.dao.RawFollowerDAO import RawFollowerDAO
from src.exception.NonExistentRawFollowerError import NonExistentRawFollowerError
from src.model.followers.RawFollower import RawFollower
from src.util.CSVUtils import CSVUtils


class TestCandidateDAO(TestCase):

    def setUp(self) -> None:
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
