from datetime import datetime

from src.db.Mongo import Mongo
from src.db.dao.GenericDAO import GenericDAO
from src.util.logging.Logger import Logger
from src.util.meta.Singleton import Singleton


class PartyRelationshipsDAO(GenericDAO, metaclass=Singleton):

    def __init__(self):
        super(PartyRelationshipsDAO, self).__init__(Mongo().get().db.party_relationships)
        self.logger = Logger(self.__class__.__name__)

    def store(self, party, result_vector):
        self.insert({'party': party, 'vector': result_vector, 'date': datetime.now().date()})

    def last_party_vector(self, party):
        documents = self.get_all({'party': party})
        return sorted(documents, key=lambda d: d['date'], reverse=True)[0]