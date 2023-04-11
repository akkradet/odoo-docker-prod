from odoo import api, fields, models, modules, _
from odoo.exceptions import UserError, ValidationError
import json
import urllib.request
import uuid
import hmac
import hashlib
import requests
import urllib.parse
import base64
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
from Crypto.Signature import PKCS1_v1_5
from base64 import b64encode, b64decode

class PosOrder(models.Model):
    _inherit='pos.order'
    
    @api.model
    def make_signature_api(self, private_key, data):
        pkey = RSA.importKey(private_key)
        h = SHA256.new(data.encode())
        signature = PKCS1_v1_5.new(pkey).sign(h)
        signature = base64.b64encode(signature).decode()
        return signature
    
    
