from abc import ABC, abstractmethod

from models.user_state import UserState


class BaseAgent(ABC):
    name: str

    @abstractmethod
    def build_chat_system_prompt(self, user_state: UserState) -> str:
        raise NotImplementedError
