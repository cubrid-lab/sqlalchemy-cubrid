# Refactored to use dialect.insert_returning instead of implicit_returning
class CubridDialect:
    insert_returning = False

    # Other methods and attributes...