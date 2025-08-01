from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm.attributes import InstrumentedAttribute

from utils.db_helpers import get_db_attribute, is_db_value_equal


@pytest.fixture
def mock_db_object():
    """A fixture to create a simple mock object simulating a database model."""
    obj = type("MockDbObject", (), {})()
    obj.id = 1
    obj.name = "Test Object"
    obj.owner_id = 123
    obj.nullable_field = None
    return obj


def test_is_db_value_equal_success():
    """
    Tests that the function returns True when the database attribute
    and the comparison value are equal.
    """
    assert is_db_value_equal(123, 123) is True
    assert is_db_value_equal("test", "test") is True

def test_is_db_value_equal_failure_not_equal():
    """
    Tests that the function returns False when the values are not equal.
    """
    assert is_db_value_equal(123, 456) is False
    assert is_db_value_equal("test", "different") is False

def test_is_db_value_equal_failure_db_attr_is_none():
    """
    Tests that the function returns False when the database attribute is None.
    This is a critical check for handling nullable fields in the database.
    """
    assert is_db_value_equal(None, 123) is False

def test_is_db_value_equal_with_instrumented_attribute(mock_db_object):
    """
    Simulates comparing against a SQLAlchemy InstrumentedAttribute.
    SQLAlchemy's `__eq__` overload handles the comparison at runtime,
    and our helper ensures the result is a clean boolean.
    """
    instrumented_attr = MagicMock(spec=InstrumentedAttribute)
    instrumented_attr.__eq__.side_effect = lambda other: (123 == other)

    assert is_db_value_equal(instrumented_attr, 123) is True
    assert is_db_value_equal(instrumented_attr, 456) is False


def test_get_db_attribute_success(mock_db_object):
    """
    Tests that the function successfully retrieves an existing attribute.
    """
    assert get_db_attribute(mock_db_object, "name") == "Test Object"
    assert get_db_attribute(mock_db_object, "owner_id") == 123

def test_get_db_attribute_returns_none_for_missing_attribute(mock_db_object):
    """
    Tests that the function returns None for an attribute that does not exist,
    preventing an AttributeError.
    """
    assert get_db_attribute(mock_db_object, "non_existent_field") is None

def test_get_db_attribute_returns_none_for_none_object():
    """
    Tests that the function safely returns None if the object itself is None,
    preventing an AttributeError.
    """
    assert get_db_attribute(None, "any_field") is None

def test_get_db_attribute_returns_actual_none_value(mock_db_object):
    """

    Tests that the function correctly returns None when the attribute's value
    is genuinely None, distinguishing it from a non-existent attribute.
    """
    assert get_db_attribute(mock_db_object, "nullable_field") is None
