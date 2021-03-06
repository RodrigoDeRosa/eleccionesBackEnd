import mongomock
from datetime import datetime
from os.path import abspath, join, dirname
from src.db.Mongo import Mongo
from src.db.dao.CandidateDAO import CandidateDAO
from src.exception.NonExistentCandidateError import NonExistentCandidateError
from src.model.Candidate import Candidate
from test.meta.CustomTestCase import CustomTestCase


class TestCandidateDAO(CustomTestCase):

    def setUp(self) -> None:
        super(TestCandidateDAO, self).setUp()
        Mongo().db = mongomock.database.Database(mongomock.MongoClient(), 'elections', _store=None)
        CandidateDAO.FILE_PATH = f"{abspath(join(dirname(__file__), '../../'))}/resources/candidates.json"
        self.target = CandidateDAO()

    def tearDown(self) -> None:
        # This has to be done because we are testing a Singleton
        CandidateDAO._instances.clear()

    def test_find_by_screen_name(self):
        CandidateDAO().save(Candidate(**{'screen_name': 'mauriciomacri', 'nickname': 'macri'}))
        # Get one and check it
        macri = CandidateDAO().find('mauriciomacri')
        assert macri is not None
        assert macri.nickname == 'macri'
        assert macri.screen_name == 'mauriciomacri'
        assert macri.last_updated_followers < datetime.now()

    def test_find_by_non_existent_screen_name_raises_exception(self):
        with self.assertRaises(NonExistentCandidateError) as context:
            _ = CandidateDAO().find('mauriciomacri')
        assert context.exception is not None
        assert context.exception.message == "There is no candidate with screen name 'mauriciomacri' in the database."

    def test_all(self):
        CandidateDAO().save(Candidate(**{'screen_name': 'mauriciomacri', 'nickname': 'macri'}))
        CandidateDAO().save(Candidate(**{'screen_name': 'CFKArgentina', 'nickname': 'cfk'}))
        candidates = CandidateDAO().all()
        assert len(candidates) == 2
        nicknames = ['macri', 'cfk']
        for candidate in candidates:
            assert candidate.nickname in nicknames

    def test_create_base_entries(self):
        # Check DB was empty
        assert CandidateDAO().get_all().count() == 0
        # Run initial creation
        self.target.create_base_entries()
        # Check DB now has values
        assert CandidateDAO().get_all().count() == 2

