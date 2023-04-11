# -*- coding: utf-8 -*-
import os
import firebase_admin
from firebase_admin import credentials
from datetime import datetime
def resource_filename(filename):
    """Returns the absolute path to a test resource."""
    return os.path.join(os.path.dirname(__file__), filename)


CREDENTIAL = credentials.Certificate(
    resource_filename('serviceAccountKey.json'))
    
firebase_admin.initialize_app(CREDENTIAL)

from . import controllers
from . import models