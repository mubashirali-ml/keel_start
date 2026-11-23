# ADR-0011: External service ports: RDAP domain checks and Netlify hosting

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-23 |
| **Deciders** | Supervisor |
| **Tickets** | T-001 (protocols + fakes), T-007 (RDAP adapter), T-008 (Netlify adapter), T-016 (selection) |
| **Scope** | `launch_agents/ports/`, `launch_agents/adapters/` |

## Context

The Name Agent must check `.com`, `.co`, `.io` availability live through free RDAP
lookups and report available / taken / unknown honestly. The Website Agent must deploy
live to a hosting provider configured by environment variables, and still build, preview
and offer a download when no token is set. Tests and recorded runs need no network.

## Decision

### Domain checks (`ports/domain_check.py`)

```python
class DomainChecker(Protocol):
    name: str                                   # "rdap" | "fake"
    def check(self, domain: str) -> DomainCheck: ...      # never raises for lookup failures

class FakeDomainChecker:
    name = "fake"
    def __init__(self, taken: Iterable[str] = DEFAULT_FAKE_TAKEN, unknown: Iterable[str] = ()): ...
    calls: list[str]
DEFAULT_FAKE_TAKEN = frozenset({"acme.com", "launch.com", "startup.com", "google.com", "apple.com"})
```

The fake answers `taken` for domains in `taken`, `unknown` for `unknown`, otherwise
`available`, with `source="fake"`.

**Live adapter** `adapters/rdap.py` (T-007): `RdapDomainChecker(client: httpx.Client | None = None,
timeout_s: float = 5.0)`. It resolves the RDAP base URL per TLD from the IANA bootstrap
file `https://data.iana.org/rdap/dns.json` (fetched once and cached in memory), falling
back to `https://rdap.org/domain/{domain}` when the TLD is not listed. `GET
{base}domain/{domain}`: HTTP 200 -> `taken`; 404 -> `available`; anything else, timeouts
and connection errors -> `unknown` with a short `detail` (e.g. "registry did not answer").
It sends `Accept: application/rdap+json` and a generic User-Agent, and never retries in a
loop. "Available" is reported as "available at the registry (not reserved or premium
checks)" in the UI copy.

State business-name availability cannot be checked through a free API: the Name Agent
returns `StateNameCheck(status="check_manually", search_url=state_info(code).name_search_url, ...)`
and the USPTO trademark search link. That is product behaviour, not a port.

### Hosting (`ports/hosting.py`)

```python
class SiteHost(Protocol):
    name: str                                   # "netlify" | "fake" | "none"
    configured: bool
    def deploy(self, site_slug: str, bundle: SiteBundle) -> DeployResult: ...   # never raises for provider errors

class FakeSiteHost:          # configured=True, url = f"https://{site_slug}.fake-host.test", records deploys
class UnconfiguredSiteHost:  # configured=False, returns DeployResult(status="not_configured",
                             #   message="Deploy isn't set up yet: add a NETLIFY_AUTH_TOKEN to publish. "
                             #           "You can preview and download the site meanwhile.")
```

**Provider: Netlify.** Live adapter `adapters/netlify.py` (T-008):
`NetlifySiteHost(token: str, client: httpx.Client | None = None, poll_timeout_s: float = 60)`.

1. Find the site by name (`GET /api/v1/sites?name={slug}`), else create it
   (`POST /api/v1/sites` `{"name": slug}`); on a name clash retry once with a 6-char suffix.
2. Upload the bundle as a zip: `POST /api/v1/sites/{site_id}/deploys`,
   `Content-Type: application/zip`, body `bundle.to_zip()`.
3. Poll `GET /api/v1/deploys/{deploy_id}` until `state == "ready"` (or `error`, or timeout).
4. Return `DeployResult(status="deployed", url=ssl_url, deploy_id=..., provider="netlify")`;
   any failure returns `status="failed"` with a friendly `message`.

Base URL `https://api.netlify.com`, header `Authorization: Bearer {token}`.

### Selection (`composition.py`, T-016)

| Setting | Value | Adapter |
|---|---|---|
| `LAUNCH_FAKE_SERVICES=1` | — | `FakeDomainChecker`, `FakeSiteHost` (but an explicitly set `HOSTING_PROVIDER` still wins for hosting, so `HOSTING_PROVIDER=none` shows the not-configured path with everything else faked) |
| `DOMAIN_CHECKER` | `rdap` (default) / `fake` | `RdapDomainChecker` / `FakeDomainChecker` |
| `HOSTING_PROVIDER` | `netlify` / `fake` / `none` | `NetlifySiteHost` / `FakeSiteHost` / `UnconfiguredSiteHost` |
| default hosting | `netlify` when `NETLIFY_AUTH_TOKEN` is set, else `none` | |

## Options considered

| Option | Pros | Cons |
|---|---|---|
| A. Netlify zip deploy (chosen) | Free tier; one REST call deploys a static zip; token-only setup; HTTPS URL out of the box | Netlify account needed for live deploys |
| B. Cloudflare Pages direct upload | Fast CDN | Direct upload API needs a manifest/hash protocol; more code |
| C. GitHub Pages | Free | Needs a repo per site and git pushes; slow to go live |
| D. Vercel | Good DX | File-by-file upload with SHA manifest; more code |
| RDAP via IANA bootstrap (chosen) vs. a paid WHOIS API | Free, authoritative | Some registries rate-limit: reported as `unknown`, honestly |

## Consequences

- Without keys the product still works end to end (fake or "not configured" paths).
- The founder sees `unknown` rather than a guess when a registry does not answer.
- Changing hosting provider means a new adapter behind the same `SiteHost` protocol.
