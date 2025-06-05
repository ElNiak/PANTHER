"""
Event Store Module

This module defines all store event classes used in the PANTHER framework's observer system.
"""

from datetime import datetime
from typing import Generic, Any, TypeVar

from panther.core.observer.core.core_events import TestEvent

T = TypeVar("T")  # Define the type variable T


class TestResultEvent(TestEvent):
    """
    Specialized event for test results.

    This event type carries structured test result data and metadata
    for easier aggregation and reporting.
    """

    def __init__(
        self,
        name: str,
        test_name: str,
        result: bool,
        data: dict[str, Any] = None,
        metadata: dict[str, Any] = None,
    ):
        """
        Initialize a new TestResultEvent.

        Args:
            name: Result event name/identifier
            test_name: Name of the test that produced this result
            result: Boolean indicating test success/failure
            data: Test result data
            metadata: Additional metadata about the test
        """
        super().__init__(name, data or {})
        self.test_name = test_name
        self.result = result
        self.metadata = metadata or {}

        # Add standard result data
        self.data.update(
            {
                "test_name": test_name,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def is_success(self) -> bool:
        """
        Check if this result represents a successful test.

        Returns:
            bool: True if the test was successful, False otherwise
        """
        return self.result

    def get_type(self) -> str:
        """
        Get the event type.

        Returns:
            str: The event type, prefixed with 'test.result.'
        """
        return f"test.result.{self.name}"


class EnhancedResultEvent(TestEvent, Generic[T]):
    """
    Enhanced specialized event for test results with strong typing.

    This event type carries strongly typed result data along with
    additional metadata for improved aggregation and reporting.
    Supports generic type parameters for result data.
    """

    def __init__(
        self,
        name: str,
        test_name: str,
        result: bool,
        result_data: T = None,
        metadata: dict[str, Any] = None,
        tags: list[str] = None,
        category: str = None,
    ):
        """
        Initialize a new EnhancedResultEvent.

        Args:
            name: Result event name/identifier
            test_name: Name of the test that produced this result
            result: Boolean indicating test success/failure
            result_data: Strongly typed test result data
            metadata: Additional metadata about the test
            tags: List of tags for categorizing results
            category: Main category for this result
        """
        # Initialize with empty data dict that will be filled below
        super().__init__(name, {})

        self.test_name = test_name
        self.result = result
        self.result_data = result_data
        self.metadata = metadata or {}
        self.tags = tags or []
        self.category = category or "default"
        self.timestamp = datetime.now()

        # Add standard result data
        self.data.update(
            {
                "test_name": test_name,
                "result": result,
                "timestamp": self.timestamp.isoformat(),
                "tags": self.tags,
                "category": self.category,
            }
        )

        # Add result data if provided
        if result_data is not None:
            self.data["result_data"] = result_data

    def is_success(self) -> bool:
        """
        Check if this result represents a successful test.

        Returns:
            bool: True if the test was successful, False otherwise
        """
        return self.result

    def get_type(self) -> str:
        """
        Get the event type.

        Returns:
            str: The event type, prefixed with 'enhanced.result.'
        """
        return f"enhanced.result.{self.name}"

    def get_result_data(self) -> T:
        """
        Get the strongly typed result data.

        Returns:
            T: The result data with its original type
        """
        return self.result_data

    def add_tag(self, tag: str) -> None:
        """
        Add a tag to this result event.

        Args:
            tag: The tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)
            self.data["tags"] = self.tags
