# sqlalchemy_cubrid/dialect.py

class CubridDialect:
    # Other class attributes and methods

    insert_returning = False  # Existing attribute controlling INSERT...RETURNING behavior

    # The 'implicit_returning' attribute is no longer used and can be removed
    # It was intended to control INSERT...RETURNING behavior, but SQLAlchemy's
    # CRUD compiler now uses 'insert_returning' for this purpose.
    # Therefore, this attribute is unnecessary and has been marked as dead.

    # TODO: Remove this attribute and its comment once confirmed to be unused
    # (See acceptance criteria in issue #391)
    # implicit_returning = False