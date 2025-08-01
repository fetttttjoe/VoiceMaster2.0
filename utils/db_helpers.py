from typing import Any, Optional, TypeVar, Union

from sqlalchemy.orm.attributes import InstrumentedAttribute

T = TypeVar("T")


def is_db_value_equal(db_attribute: Union[T, InstrumentedAttribute[T], None], value_to_compare: T) -> bool:
    """
    Safely compares a SQLAlchemy model attribute to a Python value.

    This function is crucial for preventing `Pylance` type-checking errors that
    can arise when directly comparing a potentially `None` SQLAlchemy attribute
    (which can be an `InstrumentedAttribute` before loading, or `None` if the
    database value is NULL) with a concrete Python value. It ensures a boolean
    is always returned, fulfilling static type checking requirements.

    Args:
        db_attribute: The SQLAlchemy model attribute to check (e.g., `vc.owner_id`).
                      Can be an `InstrumentedAttribute` (representing a column
                      that hasn't been loaded yet from the DB), the actual value,
                      or `None` if the column value is `NULL`.
        value_to_compare: The Python value to compare against the database attribute.

    Returns:
        True if the `db_attribute` is not `None` and its value equals `value_to_compare`,
        False otherwise (e.g., if `db_attribute` is `None` or the values don't match).
    """
    # If the database attribute itself is None (e.g., representing a NULL value
    # or an unloaded relationship that is None), it cannot be equal to any value.
    if db_attribute is None:
        return False

    # Explicitly cast the SQLAlchemy comparison result to bool.
    # This tells `Pylance` (and other static analysis tools) to trust that the
    # outcome of `db_attribute == value_to_compare` will indeed be a simple boolean,
    # even though `db_attribute` might technically be an `InstrumentedAttribute`
    # and not just the raw value at the time of static analysis. At runtime, SQLAlchemy
    # handles the comparison correctly.
    return bool(db_attribute == value_to_compare)


def get_db_attribute(obj: Any, attribute_name: str) -> Optional[Any]:
    """
    Safely retrieves an attribute from a database model object.

    This helps with static analysis by providing a clear way to access
    attributes that might not be loaded yet, returning None if the object
    is None or the attribute doesn't exist.

    Args:
        obj: The database model instance.
        attribute_name: The name of the attribute to retrieve.

    Returns:
        The attribute's value, or None if the object is None or the attribute
        is not present.
    """
    if obj is None:
        return None
    return getattr(obj, attribute_name, None)
