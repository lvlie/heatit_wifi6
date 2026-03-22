import jwt
from datetime import datetime, timedelta

def create_token():
    payload = {
        "iss": "22222222222222222222222222222222", # token id
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=3650)
    }
    # HA jwt uses HS256 with the user's refresh token jwt_key as the secret
    token = jwt.encode(payload, "dummy_key_for_testing_12345", algorithm="HS256")
    print(token)

create_token()
