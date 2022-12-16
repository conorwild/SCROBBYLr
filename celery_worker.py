import os
from rrecords import create_app

app = create_app()
app.app_context().push()

from rrecords import celery