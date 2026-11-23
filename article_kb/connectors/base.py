from abc import ABC, abstractmethod


class BaseConnector(ABC):
    source_name = "unknown"

    def __init__(self, session, logger):
        self.session = session
        self.logger = logger

    @abstractmethod
    def discover(self, tag, config):
        """Return normalized Article objects for a tag."""
        raise NotImplementedError
