#!/usr/bin/python
#
# Copyright (C) 2015 John Casey (jdcasey@commonjava.org)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import sys
from optparse import (OptionParser,BadOptionError,AmbiguousOptionError)
import socket
import fcntl
import struct
import time

OUT_DIR='/var/www/html/ssl-config'
OSSL_DIR=os.path.join(OUT_DIR, 'openssl-files')

CA_ROOT_KEYTYPE='root'
CA_WEB_KEYTYPE='web'

KEY_FORMAT="openssl genrsa -des3 -passout 'pass:test' -out {dir}/{keytype}.key 2048"

CA_ROOT_SIGN_FORMAT=("openssl req -config {openssl_cnf} -new -x509 -passin 'pass:test' -days 3650 -key {dir}/root.key -out {dir}/root.crt"
					 " -subj '/C=US/ST=Kansas/L=Smallville/O=Test/CN=Root/emailAddress=it@{host}'")

CA_WEB_CSR_FORMAT=("openssl req -config {openssl_cnf} -new -passin 'pass:test' -days 1095 -key {dir}/web.key -out {dir}/web.csr"
				   " -subj '/C=US/ST=Kansas/L=Smallville/O=Test/OU=Web/CN=Web Admin/emailAddress=webadmin@{host}'")

CA_WEB_SIGN_FORMAT="openssl ca -config {openssl_cnf} -passin 'pass:test' -batch -name CA_root -extensions v3_ca -out {dir}/web.crt -infiles {dir}/web.csr"

SITE_CRT_FORMAT=("openssl req -config {openssl_cnf} -nodes -newkey rsa:2048 -keyout {dir}/site.key -out {dir}/site.csr -days 365"
				 " -subj '/C=US/ST=Kansas/L=Smallville/O=Test/OU=Web/CN={host}/emailAddress=webadmin@{host}/subjectAltName=IP={ip_address}'")

SITE_SIGN_FORMAT="openssl ca -config {openssl_cnf} -passin 'pass:test' -batch -name CA_{keytype} -out {dir}/site.crt -infiles {dir}/site.csr"

SITE_SELFSIGN_FORMAT=("openssl req -config {openssl_cnf} -nodes -x509 -newkey rsa:2048 -keyout {dir}/site.key -out {dir}/site.crt -days 365"
					  " -subj '/C=US/ST=Kansas/L=Smallville/O=Test/OU=Web/CN={host}/emailAddress=webadmin@{host}/subjectAltName=IP={ip_address}'")


CA_TYPE_ENVAR='CA_TYPE'
HOST_ENVAR='CA_HOST'
#DEFAULT_HOST='test.myco.com'
NET_IFC='eth0'

OPENSSL_CONF=os.path.join(OSSL_DIR, 'openssl.cnf')
HTTPD_CONF='/etc/httpd/conf/httpd.conf'
SSL_CONF='/etc/httpd/conf.d/ssl.conf'

def create_conf(conf_file, host):
	infile = "%s.in" % conf_file
	if os.path.exists(infile):
		with open(infile, 'r') as fi:
			output = fi.read().replace('{{host}}', host).replace('{{dir}}', OUT_DIR).replace('{{openssl_dir}}', OSSL_DIR)
			with open(conf_file, 'w') as fo:
				fo.write(output)
	else:
		print "SKIP: No such template: %s" % infile

# Function adapted from: http://stackoverflow.com/questions/24196932/how-can-i-get-the-ip-address-of-eth0-in-python
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', NET_IFC[:15])
    )[20:24])

def run(cmd, fail=True):
	"""Run the given command, first printing the command to be run.
	By default, fail the script if the command fails. Return the
	exit value if it returns successfully or if fail=False.
	"""
	print cmd
	ret = os.system(cmd)
	if fail and ret != 0:
		print "%s (failed with code: %s)" % (cmd, ret)
		sys.exit(ret)
		return ret

flavor=os.environ.get(CA_TYPE_ENVAR) or None
if flavor is not None:
	flavor = flavor.lower()

if flavor != 'single' and flavor != 'multi':
	flavor = None

ip_address=get_ip_address()
host=os.environ.get(HOST_ENVAR) or ip_address

create_conf(OPENSSL_CONF, host)
create_conf(HTTPD_CONF, host)
create_conf(SSL_CONF, host)

for d in ('certs', 'crl', 'newcerts', 'private'):
	path = os.path.join(OSSL_DIR, d)
	if os.path.exists(path) is not True:
		os.makedirs(path)

init_contents = {'index.txt': '', 'serial': str((int)(time.time()))}
for filename in init_contents:
	with open(os.path.join(OSSL_DIR, filename), 'w') as f:
		f.write(init_contents[filename])

if flavor is not None:
  	# Generate the root CA
  	# Set the root CA as the signing entity
	print "Generate root CA"
	run(KEY_FORMAT.format(dir=OUT_DIR, keytype=CA_ROOT_KEYTYPE))
	run(CA_ROOT_SIGN_FORMAT.format(host=host, dir=OUT_DIR, openssl_cnf=OPENSSL_CONF ))

	key=CA_ROOT_KEYTYPE

  	if flavor == 'multi':
		# Generate the intermediate CA, signed by root CA
		# Set intermediate CA as the signing entity
		print "Generate multi-layer CA"
		run(KEY_FORMAT.format(dir=OUT_DIR, keytype=CA_WEB_KEYTYPE, openssl_cnf=OPENSSL_CONF ))
		run(CA_WEB_CSR_FORMAT.format(host=host, dir=OUT_DIR, openssl_cnf=OPENSSL_CONF))
		run(CA_WEB_SIGN_FORMAT.format(dir=OUT_DIR, openssl_cnf=OPENSSL_CONF ))

		key=CA_WEB_KEYTYPE

	print "Generate site certificate"
	run(SITE_CRT_FORMAT.format(host=host, ip_address=ip_address, dir=OUT_DIR, openssl_cnf=OPENSSL_CONF))
	
	print "Sign site certificate with CA: %s" % key
	run(SITE_SIGN_FORMAT.format(dir=OUT_DIR, openssl_cnf=OPENSSL_CONF, keytype=key))

else:
	# Generate a self-signed certificate without a CA
	print "Generate self-signed certificate"
	run(SITE_SELFSIGN_FORMAT.format(host=host, ip_address=ip_address, dir=OUT_DIR, openssl_cnf=OPENSSL_CONF))

run("httpd -D FOREGROUND")
