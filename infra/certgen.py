"""GlobalScale: emite certificados TLS válidos nas versões recentes do OpenSSL.

Compatibilidade: a primeira versão da PKI criava uma CA sem KeyUsage e folhas sem
AuthorityKeyIdentifier. OpenSSL recente rejeita essa cadeia. Corrigir automaticamente
os certificados existentes sem tocar nos volumes PostgreSQL ou nas chaves JWT.
"""
import os
import ipaddress
import datetime
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12

OUT = Path('/certs')
OUT.mkdir(exist_ok=True)
NOW = datetime.datetime.now(datetime.timezone.utc)

def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)

def dumpkey(path, k):
    path.write_bytes(k.private_bytes(serialization.Encoding.PEM,
                                   serialization.PrivateFormat.TraditionalOpenSSL,
                                   serialization.NoEncryption()))
    os.chmod(path, 0o600)

def dumpcrt(path, crt):
    path.write_bytes(crt.public_bytes(serialization.Encoding.PEM))

def name(label):
    return x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'GlobalScale Academic'),
        x509.NameAttribute(NameOID.COMMON_NAME, label),
    ])

def ca_certificate(k):
    return (x509.CertificateBuilder()
        .subject_name(name('GlobalScale Test CA'))
        .issuer_name(name('GlobalScale Test CA'))
        .public_key(k.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(NOW-datetime.timedelta(minutes=5))
        .not_valid_after(NOW+datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False,
            key_encipherment=False, data_encipherment=False,
            key_agreement=False, key_cert_sign=True, crl_sign=True,
            encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(k.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(k.public_key()), critical=False)
        .sign(k, hashes.SHA256()))

ca_keypath = OUT/'ca.key'
ca_crtpath = OUT/'ca.crt'
renew_ca = False
if ca_keypath.exists() and ca_crtpath.exists():
    ca_key = serialization.load_pem_private_key(ca_keypath.read_bytes(), password=None)
    ca = x509.load_pem_x509_certificate(ca_crtpath.read_bytes())
    try:
        valid_ku = ca.extensions.get_extension_for_class(x509.KeyUsage).value.key_cert_sign
        ca.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
        ca.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier)
        if not valid_ku or ca.not_valid_after_utc < NOW + datetime.timedelta(days=1):
            renew_ca = True
    except x509.ExtensionNotFound:
        renew_ca = True
else:
    ca_key = key()
    dumpkey(ca_keypath, ca_key)
    renew_ca = True

if renew_ca:
    ca = ca_certificate(ca_key)
    dumpcrt(ca_crtpath, ca)
    print('CA de demonstração renovada com KeyUsage e AKI/SKI; chave privada preservada.')

# Não reemitir os certificados em execuções futuras, salvo mudança de IP ou
# presença de extensões inválidas. Quando a CA mudou, todos os serviços
# devem reiniciar para carregar as novas cadeias TLS.
def should_refresh(path, keypath, label):
    if renew_ca or not (path.exists() and keypath.exists()):
        return True
    try:
        c = x509.load_pem_x509_certificate(path.read_bytes())
        c.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier)
        c.extensions.get_extension_for_class(x509.KeyUsage)
        if c.not_valid_after_utc < NOW + datetime.timedelta(days=1):
            return True
        if label == 'gateway':
            sans = c.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            ip = ipaddress.ip_address(os.environ.get('LAN_IP', '127.0.0.1'))
            if ip not in sans.get_values_for_type(x509.IPAddress):
                return True
    except (ValueError, x509.ExtensionNotFound, OSError):
        return True
    return False

def issue(label, dns, ips=(), client=False):
    crt_path = OUT/f'{label}.crt'
    key_path = OUT/f'{label}.key'
    if not should_refresh(crt_path, key_path, label):
        k = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        c = x509.load_pem_x509_certificate(crt_path.read_bytes())
        return c, k, False
    k = key()
    sans = [x509.DNSName(dnsname) for dnsname in dns]
    for addr in ips:
        try:
            sans.append(x509.IPAddress(ipaddress.ip_address(addr)))
        except ValueError:
            continue
    c = (x509.CertificateBuilder()
        .subject_name(name(label))
        .issuer_name(ca.subject)
        .public_key(k.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(NOW-datetime.timedelta(minutes=5))
        .not_valid_after(NOW+datetime.timedelta(days=1095))
        .add_extension(x509.SubjectAlternativeName(sans), critical=False)
        .add_extension(x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.CLIENT_AUTH if client else ExtendedKeyUsageOID.SERVER_AUTH
        ]), critical=False)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False,
            key_encipherment=True, data_encipherment=False,
            key_agreement=False, key_cert_sign=False, crl_sign=False,
            encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(k.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256()))
    dumpkey(key_path, k)
    dumpcrt(crt_path, c)
    return c, k, True

issue('gateway', ['localhost','gateway'], ['127.0.0.1',os.environ.get('LAN_IP','127.0.0.1')])
issue('client', ['globalscale-client'], client=True)
for code in ('af','eu','as','na','sa','oc'):
    issue(f'region-{code}', [f'region-{code}',f'{code}-primary',f'{code}-standby'])
for code in ('global','af','eu','as','na','sa','oc'):
    issue(f'db-{code}', [f'db-{code}'])
    try:
        os.chown(OUT/f'db-{code}.key',70,70)
    except (OSError,PermissionError):
        pass

legacy_cert,legacy_key,changed = issue('legacy',['legacy'])
legacy_file = OUT/'legacy.p12'
if renew_ca or changed or not legacy_file.exists():
    password = os.environ.get('CERT_PASSWORD','ChangeThisCertificatePassword!')
    legacy_file.write_bytes(pkcs12.serialize_key_and_certificates(
        b'legacy', legacy_key, legacy_cert, [ca],
        serialization.BestAvailableEncryption(password.encode())))
    os.chmod(legacy_file, 0o600)

# Chaves JWT existentes não são alteradas, para preservar as contas e sessões.
jwt_private = OUT/'jwt-private.pem'
jwt_public = OUT/'jwt-public.pem'
if not jwt_private.exists():
    jwt_key = key()
    dumpkey(jwt_private,jwt_key)
    jwt_public.write_bytes(jwt_key.public_key().public_bytes(
        serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
elif not jwt_public.exists():
    jwt_key = serialization.load_pem_private_key(jwt_private.read_bytes(),password=None)
    jwt_public.write_bytes(jwt_key.public_key().public_bytes(
        serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))

print('Certificados TLS prontos (mTLS, AKI, SKI, KeyUsage). Dados PostgreSQL intactos.')
