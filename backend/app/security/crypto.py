"""Cryptographic utilities for ECC signatures and AES encryption."""

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.exceptions import AgriIoTError, DecryptionError


def load_public_key_from_pem(pem_data: str) -> EllipticCurvePublicKey:
    """
    Load an ECC public key from a PEM string.
    
    Args:
        pem_data: The PEM encoded public key.
        
    Returns:
        The public key object.
        
    Raises:
        AgriIoTError: If the key cannot be parsed.
    """
    try:
        key = serialization.load_pem_public_key(pem_data.encode("utf-8"))
        if not isinstance(key, EllipticCurvePublicKey):
            raise AgriIoTError("Key is not an EllipticCurvePublicKey")
        return key
    except Exception as e:
        raise AgriIoTError(f"Failed to load public key: {str(e)}")


def verify_ecc_signature(
    public_key_pem: str, payload: str, signature_b64: str
) -> bool:
    """
    Verify an ECDSA signature using secp256r1 (P-256) and SHA-256.
    
    Args:
        public_key_pem: The device's public key in PEM format.
        payload: The raw string payload that was signed.
        signature_b64: The base64 encoded signature.
        
    Returns:
        True if valid, False otherwise.
    """
    try:
        public_key = load_public_key_from_pem(public_key_pem)
        signature = base64.b64decode(signature_b64)
        
        public_key.verify(
            signature,
            payload.encode("utf-8"),
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except InvalidSignature:
        return False
    except Exception:
        return False


def get_device_symmetric_key(master_secret: str, device_id: str) -> bytes:
    """
    Derive a 256-bit symmetric key for a device using the master secret.
    In a full production system, this would use HKDF. For this lightweight
    IoT framework, we use SHA-256(master_secret || device_id).
    """
    digest = hashes.Hash(hashes.SHA256())
    digest.update(master_secret.encode("utf-8"))
    digest.update(device_id.encode("utf-8"))
    return digest.finalize()


def decrypt_aes_gcm(key: bytes, ciphertext_b64: str) -> bytes:
    """
    Decrypt an AES-256-GCM ciphertext.
    Expects ciphertext_b64 to contain the 12-byte nonce followed by the ciphertext.
    """
    try:
        data = base64.b64decode(ciphertext_b64)
        if len(data) < 12:
            raise ValueError("Data too short to contain nonce")
        nonce = data[:12]
        ciphertext = data[12:]
        
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise DecryptionError(f"AES-GCM decryption failed: {str(e)}")
