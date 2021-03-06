import mongomock

from datetime import datetime
from unittest import mock

from src.db.Mongo import Mongo
from src.db.dao.CandidateDAO import CandidateDAO
from src.exception.CandidateCurrentlyAvailableForUpdateError import CandidateCurrentlyAvailableForUpdateError
from src.exception.FollowerUpdatingNotNecessaryError import FollowerUpdatingNotNecessaryError
from src.service.candidates.CandidateService import CandidateService
from src.model.Candidate import Candidate
from src.util.concurrency.ConcurrencyUtils import ConcurrencyUtils
from test.meta.CustomTestCase import CustomTestCase


class TestCandidateService(CustomTestCase):

    def setUp(self) -> None:
        super(TestCandidateService, self).setUp()
        # Mocking the whole database is not unit testing but we don't care because this is done to only to
        # make target's initialization easier
        Mongo().db = mongomock.database.Database(mongomock.MongoClient(), 'elections', _store=None)
        # Now we override whatever the DB would answer
        candidate1 = Candidate(**{'screen_name': 'sn1', 'nickname': 'n1'})
        candidate2 = Candidate(**{'screen_name': 'sn2', 'nickname': 'n2'})
        CandidateService().candidates = [candidate1, candidate2]
        # Get the object
        self.target = CandidateService()

    def tearDown(self) -> None:
        # This has to be done because we are testing a Singleton
        CandidateService._instances.clear()

    @mock.patch.object(ConcurrencyUtils, 'acquire_lock')
    @mock.patch.object(ConcurrencyUtils, 'release_lock')
    def test_get_for_follower_updating_all_available_none_updated(self, release_lock, acquire_lock):
        candidate = self.target.get_for_follower_updating()
        assert candidate is not None
        assert candidate.screen_name == 'sn1'
        assert candidate.nickname == 'n1'
        assert acquire_lock.call_count == 1
        assert release_lock.call_count == 1

    @mock.patch.object(ConcurrencyUtils, 'acquire_lock')
    @mock.patch.object(ConcurrencyUtils, 'release_lock')
    def test_get_for_follower_updating_all_available_one_updated(self, release_lock, acquire_lock):
        # Set first candidate as already updated
        self.target.candidates[0].last_updated_followers = datetime.now()
        candidate = self.target.get_for_follower_updating()
        assert candidate is not None
        assert candidate.screen_name == 'sn2'
        assert candidate.nickname == 'n2'
        assert acquire_lock.call_count == 1
        assert release_lock.call_count == 1

    @mock.patch.object(ConcurrencyUtils, 'acquire_lock')
    @mock.patch.object(ConcurrencyUtils, 'release_lock')
    def test_get_for_follower_updating_all_available_all_updated(self, release_lock, acquire_lock):
        # Set all candidates as already updated
        self.target.candidates[0].last_updated_followers = datetime.now()
        self.target.candidates[1].last_updated_followers = datetime.now()
        with self.assertRaises(FollowerUpdatingNotNecessaryError) as context:
            _ = self.target.get_for_follower_updating()
        assert context.exception is not None
        assert context.exception.message == 'Followers have been updated for every candidate.'
        assert acquire_lock.call_count == 1
        assert release_lock.call_count == 1

    @mock.patch.object(ConcurrencyUtils, 'acquire_lock')
    @mock.patch.object(ConcurrencyUtils, 'release_lock')
    def test_get_for_follower_updating_one_available(self, release_lock, acquire_lock):
        _ = self.target.get_for_follower_updating()
        candidate = self.target.get_for_follower_updating()
        assert candidate is not None
        assert candidate.screen_name == 'sn2'
        assert candidate.nickname == 'n2'
        assert acquire_lock.call_count == 2
        assert release_lock.call_count == 2

    @mock.patch.object(ConcurrencyUtils, 'acquire_lock')
    @mock.patch.object(ConcurrencyUtils, 'release_lock')
    def test_get_for_follower_updating_none_available(self, release_lock, acquire_lock):
        _ = self.target.get_for_follower_updating()
        _ = self.target.get_for_follower_updating()
        with self.assertRaises(FollowerUpdatingNotNecessaryError) as context:
            _ = self.target.get_for_follower_updating()
        assert context.exception is not None
        assert context.exception.message == 'Followers have been updated for every candidate.'
        assert acquire_lock.call_count == 3
        assert release_lock.call_count == 3

    @mock.patch.object(CandidateDAO, 'overwrite')
    def test_finish_follower_updating_candidate_being_used(self, overwrite_mock):
        # Add to mock already processing
        self.target.updating_followers.add(self.target.candidates[0])
        self.target.finish_follower_updating(self.target.candidates[0])
        assert len(self.target.updating_followers) == 0
        assert overwrite_mock.call_count == 1

    def test_finish_follower_updating_candidate_not_being_used(self):
        with self.assertRaises(CandidateCurrentlyAvailableForUpdateError) as context:
            self.target.finish_follower_updating(self.target.candidates[0])
        assert context.exception is not None
        assert context.exception.message == 'Candidate sn1 is currently available for updating.'
