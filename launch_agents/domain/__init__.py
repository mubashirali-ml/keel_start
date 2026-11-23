"""Shared domain vocabulary (ADR-0008 and the contracts of ADR-0026, ADR-0028..ADR-0032, ADR-0038).

``domain`` imports nothing else from ``launch_agents``. Every public name of the submodules
is re-exported here, so ``from launch_agents.domain import CaseFacts`` works.
"""

from .accounts import *  # noqa: F401,F403
from .billing import *  # noqa: F401,F403
from .cap_table import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .documents import *  # noqa: F401,F403
from .email import *  # noqa: F401,F403
from .errors import *  # noqa: F401,F403
from .guide import *  # noqa: F401,F403
from .helpers import *  # noqa: F401,F403
from .jobs import *  # noqa: F401,F403
from .messages import *  # noqa: F401,F403
from .state import *  # noqa: F401,F403
from .states import *  # noqa: F401,F403
from .types import *  # noqa: F401,F403
from .views import *  # noqa: F401,F403
from .website import *  # noqa: F401,F403
from . import (
    accounts,
    billing,
    cap_table,
    constants,
    documents,
    email,
    errors,
    guide,
    helpers,
    jobs,
    messages,
    state,
    states,
    types,
    views,
    website,
)

__all__ = sorted(
    {
        name
        for module in (
            accounts, billing, cap_table, constants, documents, email, errors, guide,
            helpers, jobs, messages, state, states, types, views, website,
        )
        for name in module.__all__
    }
)
