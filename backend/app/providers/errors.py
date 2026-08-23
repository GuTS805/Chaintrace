"""Provider failure taxonomy.

The router treats these differently, so they are distinct types rather than one
error with a flag:

- ``ProviderRateLimited`` and ``ProviderUnavailable`` are *transient*: retry this
  provider, then fail over. They count toward opening the circuit.
- ``ProviderBadResponse`` means the provider answered but the answer was not
  usable. Retrying an identical request will produce the identical garbage, so it
  fails over immediately without burning the retry budget.
- ``ProviderNotCapable`` is not a failure at all: the provider structurally cannot
  answer this kind of question. It must never open a circuit or be retried.
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for every provider-layer failure."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class ProviderUnavailable(ProviderError):
    """Transport failure, timeout, or a 5xx from the upstream."""


class ProviderRateLimited(ProviderUnavailable):
    """Upstream asked us to slow down.

    ``retry_after`` carries the server's own guidance when it sent any; honouring
    it beats our backoff curve, which is only a guess about the server's state.
    """

    def __init__(
        self, provider: str, message: str, retry_after: float | None = None
    ) -> None:
        self.retry_after = retry_after
        super().__init__(provider, message)


class ProviderBadResponse(ProviderError):
    """The response parsed as HTTP but not as the data we asked for."""


class ProviderNotCapable(ProviderError):
    """This provider cannot serve this operation at all.

    Raised by, for example, a plain JSON-RPC node asked for an address's
    transaction history: no amount of retrying gives a node an index it does not
    maintain.
    """


class AllProvidersFailed(ProviderError):
    """Every capable provider in the chain failed.

    Carries the individual failures so an operator can see whether this was one
    upstream having a bad day or a systemic outage.
    """

    def __init__(self, operation: str, failures: dict[str, Exception]) -> None:
        self.operation = operation
        self.failures = failures
        detail = "; ".join(f"{name}: {err}" for name, err in failures.items())
        super().__init__("router", f"{operation} failed on all providers -- {detail}")
