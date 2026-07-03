"""Environment-driven configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_domain: str          # e.g. https://<prefix>.auth.<region>.amazoncognito.com
    cognito_region: str
    allowed_subs: frozenset[str] # empty => allow any authenticated user in the pool
    auth_disabled: bool          # local dev only
    wiki_bucket: str | None      # set from Phase 1 onward

    @property
    def issuer(self) -> str:
        return (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com/"
            f"{self.cognito_user_pool_id}"
        )

    @property
    def jwks_uri(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"


def load_config() -> Config:
    subs = {s.strip() for s in os.environ.get("ALLOWED_SUBS", "").split(",") if s.strip()}
    return Config(
        cognito_user_pool_id=os.environ.get("COGNITO_USER_POOL_ID", ""),
        cognito_client_id=os.environ.get("COGNITO_CLIENT_ID", ""),
        cognito_domain=os.environ.get("COGNITO_DOMAIN", "").rstrip("/"),
        cognito_region=os.environ.get("COGNITO_REGION", os.environ.get("AWS_REGION", "us-west-2")),
        allowed_subs=frozenset(subs),
        auth_disabled=os.environ.get("AUTH_DISABLED", "").lower() in ("1", "true", "yes"),
        wiki_bucket=os.environ.get("WIKI_BUCKET") or None,
    )
