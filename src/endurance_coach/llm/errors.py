"""Safe error types exposed by the local-model runtime."""


class AgentRuntimeError(RuntimeError):
    """Base error for safely reportable failures in the local agent runtime."""


class AgentClientError(AgentRuntimeError):
    """Raised when the configured local model client cannot complete a request."""


class AgentProtocolError(AgentRuntimeError):
    """Raised when the model returns an unsupported or malformed message."""


class AgentToolError(AgentRuntimeError):
    """Raised when a validated tool request cannot be completed safely."""


class AgentIterationLimitError(AgentRuntimeError):
    """Raised when the model does not return a final answer within the configured steps."""
