# sqlalchemy_cubrid/dialect.py:238
# Commented out as the attribute is no longer used in SQLAlchemy 2.x
# and does not affect INSERT/RETURNING behavior
# implicit_returning = False

class CubridDialect(Dialect):
    # ...
    insert_returning = False
    # ...