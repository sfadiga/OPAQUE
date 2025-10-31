"""
Example Data Service
"""
from typing import Dict, Any, List
from opaque.core.services import BaseService


class DataService(BaseService):
    """Service that provides data management functionality to features."""
    
    def __init__(self):
        super().__init__("DataService")
        self._data_store = {}
    
    def initialize(self, **kwargs):
        """Initialize the data service."""
        super().initialize(**kwargs)
        # Load any initial data here
    
    def add_data(self, key: str, data: Any) -> None:
        """
        Add data to the store.
        
        Args:
            key: Unique identifier for the data
            data: Data to store
        """
        self._data_store[key] = data
    
    def get_data(self, key: str) -> Any:
        """
        Get data from the store.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            Stored data or None if not found
        """
        return self._data_store.get(key)
    
    def remove_data(self, key: str) -> bool:
        """
        Remove data from the store.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            True if removed, False if not found
        """
        if key in self._data_store:
            del self._data_store[key]
            return True
        return False
    
    def get_all_data(self) -> List[Dict[str, Any]]:
        """
        Get all stored data as a list.
        
        Returns:
            List of all stored data items
        """
        return list(self._data_store.values())
    
    def clear_data(self) -> None:
        """Clear all stored data."""
        self._data_store.clear()
    
    def data_exists(self, key: str) -> bool:
        """
        Check if data exists for a key.
        
        Args:
            key: Unique identifier to check
            
        Returns:
            True if data exists, False otherwise
        """
        return key in self._data_store
    
    def get_data_count(self) -> int:
        """Get the count of stored data items."""
        return len(self._data_store)
    
    def get_info(self) -> dict:
        """Get service information."""
        info = super().get_info()
        info['data_count'] = self.get_data_count()
        info['keys'] = list(self._data_store.keys())
        return info

    def cleanup(self):
        """Clean up the service."""
        pass
