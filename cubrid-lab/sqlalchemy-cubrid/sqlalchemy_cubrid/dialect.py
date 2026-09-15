```python
# sqlalchemy_cubrid/dialect.py

# Remove the following line as it is not used in SQLAlchemy 2.x and was likely a leftover from SQLAlchemy 1.x
# implicit_returning = False

# Ensure that the insert_returning flag is set to False as it controls the INSERT...RETURNING behavior
insert_returning = False
```