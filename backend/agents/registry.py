from agents.xiaoke import XiaoKeAgent


class AgentRegistry:
    def __init__(self):
        self._agents = {}

    def register(self, agent):
        self._agents[agent.name] = agent

    def get(self, name: str):
        return self._agents[name]


agent_registry = AgentRegistry()
agent_registry.register(XiaoKeAgent())
