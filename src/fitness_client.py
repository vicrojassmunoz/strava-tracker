from abc import ABC, abstractmethod


class FitnessClient(ABC):
    """Abstract interface for fitness tracking app integrations."""

    @abstractmethod
    def get_activities(self, limit: int = 1) -> list:
        """Return a list of recent activities (most recent first)."""

    @abstractmethod
    def get_activity_details(self, activity_id: int) -> dict:
        """Return the full detail payload for a given activity ID."""
