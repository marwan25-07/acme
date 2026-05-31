from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import FastAPI, Depends, HTTPException
from runner.config.settings import acme_settings
import requests
import json
import logging

logger = logging.getLogger(__name__)

keycloak_url = acme_settings.keycloak_url
realm_name = acme_settings.realm_name
issuer = f"{keycloak_url}/realms/{realm_name}"
jwks_url = f"{issuer}/protocol/openid-connect/certs"


security = HTTPBearer()

def get_public_key(token:str):
    header = jwt.get_unverified_header(token)
    kid = header.get("kid", None)

    if kid is not None:
        try:
            jwks = requests.get(jwks_url).json()
            for key in jwks["keys"]:
                if key["kid"]==kid:
                    return key
        except requests.RequestException as e:
            logger.error(f"Error fetching jwks: {e}")
            raise HTTPException(status_code=401, detail="Error fetching JWKS")
    else:
        logger.error("key id could not be found in token header")
        raise HTTPException(status_code=401, detail = "token could not be verified")

def validate_token(token:str):

    try:
        public_key=get_public_key(token)

        payload = jwt.decode(
            token, 
            public_key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False}
        )
        return payload
    except JWTError as e:
        logger.error(f"jwt error: {e}")
        raise HTTPException(status_code=401, detail="invalid token")
