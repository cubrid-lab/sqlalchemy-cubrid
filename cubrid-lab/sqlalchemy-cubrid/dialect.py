# Remove the implicit_returning attribute as it is no longer used in SQLAlchemy 2.x
# and does not affect the INSERT/RETURNING behavior on CUBRID.
# Comment preserved for historical reference if needed.
# implicit_returning = False

# The insert_returning attribute controls the implicit INSERT...RETURNING behavior.
# It is already set to False at dialect.py:291 and does not need to be duplicated.
insert_returning = False