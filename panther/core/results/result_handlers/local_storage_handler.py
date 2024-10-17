
from core.results.result_handler import ResultHandler


class LocalStorageHandler(ResultHandler):
    """
    Concrete implementation of ResultHandler for storing results in a local database.
    Attributes:
        db (Database): The local database to store the results in.
    Methods:
        __init__(db: Database) -> None:
            Initializes the StorageHandler with the given local database.
        handle(request) -> None:
            Stores the request in the local database.
    """
    
    def __init__(self, db) -> None:
        self.db = db
        
    def handle(self, request) -> None:
        self.db.store(request)