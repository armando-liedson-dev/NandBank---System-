from __future__ import annotations
import os,hashlib,hmac,secrets,time,uuid
from datetime import datetime,timedelta,timezone
import jwt
from fastapi import HTTPException,Header

PRIVATE_KEY = os.getenv("PRIVATE_KEY", "/certs/jwt-private.pem")
PUBLIC_KEY = os.getenv("PUBLIC_KEY", "/certs/jwt-public.pem")

def password_hash(password):
    salt=secrets.token_bytes(16)
    key=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,310000)
    return 'pbkdf2_sha256$310000$'+salt.hex()+'$'+key.hex()

def password_verify(password, stored):
    try:
        method,iterations,salt,expected=stored.split('$')
        if method!='pbkdf2_sha256':return False
        k=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),bytes.fromhex(salt),int(iterations))
        return hmac.compare_digest(k,bytes.fromhex(expected))
    except (ValueError,TypeError):return False

def issue_token(user_id,role,region=None,branch=None,ttl=3600):
    now=datetime.now(timezone.utc)
    data=dict(sub=str(user_id),role=role,region=region,branch=branch,iat=now,exp=now+timedelta(seconds=ttl),iss='globalscale',jti=str(uuid.uuid4()))
    return jwt.encode(data,open(PRIVATE_KEY,'rb').read(),algorithm='RS256')

def service_token():
    return issue_token('global-coordinator','system',ttl=60)

def verify_token(raw):
    try:
        return jwt.decode(raw,open(PUBLIC_KEY,'rb').read(),algorithms=['RS256'],issuer='globalscale',options={'require':['exp','sub','iss']})
    except (jwt.PyJWTError,ValueError,OSError):
        raise HTTPException(status_code=401,detail='Sessão expirada ou token inválido')

def bearer(authorization:str|None=Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401,detail='Autenticação necessária')
    return verify_token(authorization[7:])

def permitted(claims, *roles,region=None,branch=None):
    role=claims.get('role')
    if role not in roles and role!='global_manager':
        raise HTTPException(403,'Permissões insuficientes')
    if role=='regional_manager' and region and claims.get('region')!=region:raise HTTPException(403,'Fora da sua região')
    if role in ('branch_manager','teller') and branch and claims.get('branch')!=branch:raise HTTPException(403,'Fora da sua filial')
    if role in ('branch_manager','teller') and region and claims.get('region')!=region:raise HTTPException(403,'Fora da sua região')

def hmac_signature(raw:bytes):
    return hmac.new(os.environ['INTEGRITY_KEY'].encode(),raw,'sha256').hexdigest()
