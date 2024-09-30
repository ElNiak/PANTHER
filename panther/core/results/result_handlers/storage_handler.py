
from core.results.result_handler import ResultHandler


class StorageHandler(ResultHandler):
    """
    Concrete implementation of ResultHandler for storing results in a database.
    Attributes:
        db (Database): The database to store the results in.
    Methods:
        __init__(db: Database) -> None:
            Initializes the StorageHandler with the given database.
        handle(request) -> None:
            Stores the request in the database.
    """
    
    def __init__(self, db) -> None:
        self.db = db
        
    def handle(self, request) -> None:
        self.db.store(request)