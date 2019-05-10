from pymongo import ReturnDocument


class GenericDAO:

    def __init__(self, collection):
        self.collection = collection

    def create_indexes(self):
        # Subclass responsibility
        pass

    def get_first(self, query):
        """
        Get first entry matching the given query.
            :returns Full document
        """
        return self.collection.find_one(query)

    def get_all(self, query=None):
        """
        Get all entries matching the given query. If there is no query, full collection is returned.
            :returns List of full documents
        """
        return self.collection.find({} if query is None else query)

    def insert(self, element):
        """
        Insert given element into collection.
            :returns An instance of InsertOneResult (ior.inserted_id gives the created id)
        """
        return self.collection.insert_one(element)

    def delete_first(self, query):
        """
        Delete first element matching the given query from collection.
            :returns An instance of DeleteResult (dr.delete_count returns the amount of deleted documents)
        """
        return self.collection.find_one_and_delete(query)

    def delete_all(self, query=None):
        """
        Delete all entries matching the given query. If there is no query, collection is cleared.
            :returns An instance of DeleteResult (dr.delete_count returns the amount of deleted documents)
        """
        return self.collection.delete_many({} if query is None else query)

    def update_first(self, query, updated_fields_dict):
        """
        Update first entry matching given query with the given dictionary.
            :returns Updated document
        """
        return self.collection.find_one_and_update(filter=query,
                                                   update={'$set': updated_fields_dict},
                                                   return_document=ReturnDocument.AFTER)

    def add_fields_first(self, query, added_fields_dict):
        """
        Add given fields to first entry matching given query.
            :returns Updated document
        """
        return self.collection.find_one_and_update(filter=query,
                                                   update={'$push': added_fields_dict},
                                                   return_document=ReturnDocument.AFTER)

    def remove_fields_first(self, query, removed_fields_dict):
        """
        Add given fields to first entry matching given query.
            :returns Updated document
        """
        return self.collection.find_one_and_update(filter=query,
                                                   update={'$unset': removed_fields_dict},
                                                   return_document=ReturnDocument.AFTER)
