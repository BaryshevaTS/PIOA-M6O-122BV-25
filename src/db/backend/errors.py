class DatabaseError(ValueError):
    pass

class TableExistsError(DatabaseError):
    pass

class TableNotFoundError(DatabaseError):
    pass

class RecordNotFoundError(DatabaseError):
    pass

class ValidationError(DatabaseError):
    pass

class FileStorageError(DatabaseError):
    pass
