#!/usr/bin/python
import os
import sys

BASE_PATH = '/var/www/html'

method = os.environ.get('REQUEST_METHOD')
# sanity-check method
if method is None or method.lower() != 'put':
  status='error'

else:
  path = os.environ.get('PATH_INFO').split('/').pop()
  status = 'exists'

  filepath = os.path.join(BASE_PATH, path)
  filedir = os.path.dirname(filepath)
  if not os.path.exists(filedir):
    os.makedirs(filedir)

  if not os.path.exists(filepath):
    status='new'

  content=sys.stdin.read()
  with open(filepath, 'w') as f:
    f.write(content)

if status == 'error':
  print """Status: 400
Content-Type: text/plain

Only PUT requests are supported.
"""
elif status == 'new':
  print """Status: 201
Content-Type: text/plain
Location: /{path}

Created /{path}
""".format(path=path)
else:
  print """Status: 200
Content-Type: text/plain

Modified /{path}
""".format(path=path)
