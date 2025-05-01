import pytest
from unittest.mock import MagicMock, patch
from memory.persistent_memory import PersistentMemory


@pytest.fixture
def mock_db():
    """Create a mock database client."""
    mock = MagicMock()
    # Mock the table method to return itself for chaining
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=None
    )
    mock.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data={"id": "test-id"}
    )
    return mock


def test_persistent_memory_initialization(mock_db):
    """Test that PersistentMemory can be initialized with a database client."""
    memory = PersistentMemory(mock_db, "test-user-id")
    assert memory.db == mock_db
    assert memory.user_id == "test-user-id"
    assert memory._memory_cache == {}
    assert memory._is_loaded is False
    assert memory._is_dirty is False


@patch("memory.persistent_memory.logger")
async def test_persistent_memory_load(mock_logger, mock_db):
    """Test that PersistentMemory can load data from the database."""
    # Set up the mock to return data
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"memory_data": {"test_key": "test_value"}}]
    )
    
    memory = PersistentMemory(mock_db, "test-user-id")
    result = await memory.load()
    
    # Verify the result and state
    assert result is True
    assert memory._is_loaded is True
    assert memory._memory_cache == {"test_key": "test_value"}
    
    # Verify the database was called correctly
    mock_db.table.assert_called_once_with("user_memories")
    mock_db.table().select.assert_called_once_with("memory_data")
    mock_db.table().select().eq.assert_called_once_with("user_id", "test-user-id")
    mock_db.table().select().eq().execute.assert_called_once()
    
    # Verify logging
    mock_logger.info.assert_any_call(f"Loading memory for user test-user-id")
    mock_logger.info.assert_any_call(f"Successfully loaded memory for user test-user-id")
