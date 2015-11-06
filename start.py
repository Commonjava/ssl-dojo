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

EXT_CA="-extensions v3_ca"
EXT_NONE=""

CA_ROOT_KEYTYPE='root'
CA_WEB_KEYTYPE='web'
CA_SITE_KEYTYPE='site'
CA_CLIENT_KEYTYPE='client'

SUBJ_BASE="/C=US/ST=Kansas/L=Smallville/O=Test"
ROOT_SUBJECT="-subj '%s/CN=Root/emailAddress=it@{host}'" % SUBJ_BASE
WEB_SUBJECT="-subj '%s/OU=Web/CN=Web Admin/emailAddress=webadmin@{host}'" % SUBJ_BASE
SITE_SUBJECT="-subj '%s/OU=Web/CN={host}/emailAddress=siteadmin@{host}'" % SUBJ_BASE
CLIENT_SUBJECT="-subj '%s/OU=Clients/CN=client/emailAddress=client@{host}'" % SUBJ_BASE

SITE_SAN = "IP.1:{ip_address},DNS.1:localhost,DNS.2:{ip_address}"

KEY_FORMAT=            ("openssl genrsa "
						"-passout 'pass:test' "
						"-out {dir}/{keytype}.key 2048")

CA_ROOT_SIGN_FORMAT=   ("openssl req -config {openssl_cnf} "
						"-passin 'pass:test' "
						"-new "
						"-days 3650 "
						"-key {dir}/root.key "
						"-out {dir}/root.crt "
						"-extensions v3_ca "
						"%s -x509" % ROOT_SUBJECT)

CSR_FORMAT=            ("openssl req -config {openssl_cnf} "
						"-passin 'pass:test' "
						"-nodes "
						"-new "
						"-days {days} "
						"-key {dir}/{keytype}.key "
						"-out {dir}/{keytype}.csr "
						"{subject}")

SITE_CSR_FORMAT=       ("openssl req -config {openssl_cnf} "
						"-nodes "
						"-newkey rsa:2048 "
						"-days 365 "
						"-keyout {dir}/site.key "
						"-out {dir}/site.csr "
						"%s" % SITE_SUBJECT)

CLIENT_SELFSIGN_FORMAT=("openssl req -config {openssl_cnf} "
						"-passout 'pass:test' "
						"-newkey rsa:2048 "
						"-days 365 "
						"-keyout {dir}/client.key "
						"-out {dir}/client.crt "
						"%s -x509" % CLIENT_SUBJECT)

SITE_SELFSIGN_FORMAT=  ("openssl req -config {openssl_cnf} "
						"-nodes "
						"-newkey rsa:2048 "
						"-days 365 "
						"-keyout {dir}/site.key "
						"-out {dir}/site.crt "
						"%s -x509" % SITE_SUBJECT)


SIGN_FORMAT=           ("openssl ca -config {openssl_cnf} "
					    "-passin 'pass:test' "
					    "-batch "
					    "-keyfile {dir}/{catype}.key "
					    "-cert {dir}/{catype}.crt "
					    "{ext} "
					    "-out {dir}/{keytype}.crt "
					    "-infiles {dir}/{keytype}.csr")

P12_FORMAT=            ("openssl pkcs12 "
						"-export "
						"-CAfile {dir}/{catype}.crt "
						"-passin 'pass:test' "
						"-passout 'pass:test' "
						"-in {dir}/{keytype}.crt "
						"-inkey {dir}/{keytype}.key "
						"-out {dir}/{keytype}.p12")

# PEM_FORMAT=            ("openssl pkcs12 "
# 						"-clcerts "
# 						"-passin 'pass:test' "
# 						"-passout 'pass:test' "
# 						"-in {dir}/{keytype}.p12 "
# 						"-out {dir}/{keytype}.pem")


CA_TYPE_ENVAR='CA_TYPE'
HOST_ENVAR='CA_HOST'
#DEFAULT_HOST='test.myco.com'
NET_IFC='eth0'

OPENSSL_CONF=os.path.join(OSSL_DIR, 'openssl.cnf')
HTTPD_CONF='/etc/httpd/conf/httpd.conf'
SSL_CONF='/etc/httpd/conf.d/ssl.conf'

def cat_keycert(basename):
	with open(os.path.join(OUT_DIR, "%s.pem" % basename), 'w') as outfile:
		for fname in (os.path.join(OUT_DIR, "%s.crt" % basename), 
					  os.path.join(OUT_DIR, "%s.key" % basename)):
			with open(fname,'r') as infile:
				outfile.write(infile.read())

def create_conf(conf_file, host, subjectAltNames=None):
	infile = "%s.in" % conf_file
	if os.path.exists(infile):
		with open(infile, 'r') as fi:
			output = fi.read().replace('{{host}}', host).replace('{{dir}}', OUT_DIR).replace('{{openssl_dir}}', OSSL_DIR)
			if subjectAltNames is not None:
				output = output.replace('{{subjectAltNames}}', subjectAltNames)
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

create_conf(OPENSSL_CONF, host, SITE_SAN.format(ip_address=ip_address))
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
	cas = [key]

  	if flavor == 'multi':
		# Generate the intermediate CA, signed by root CA
		# Set intermediate CA as the signing entity
		print "Generate multi-layer CA"
		run(KEY_FORMAT.format(dir=OUT_DIR, keytype=CA_WEB_KEYTYPE, openssl_cnf=OPENSSL_CONF ))
		run(CSR_FORMAT.format(days=1000,host=host, dir=OUT_DIR, openssl_cnf=OPENSSL_CONF, keytype=CA_WEB_KEYTYPE, subject=WEB_SUBJECT.format(host=host)))
		run(SIGN_FORMAT.format(dir=OUT_DIR, openssl_cnf=OPENSSL_CONF,catype=CA_ROOT_KEYTYPE,keytype=CA_WEB_KEYTYPE,ext=EXT_CA))
		cat_keycert(CA_WEB_KEYTYPE)

		key=CA_WEB_KEYTYPE
		cas.append(key)

	print "Generate site certificate"
	run(SITE_CSR_FORMAT.format(host=host, ip_address=ip_address, dir=OUT_DIR, openssl_cnf=OPENSSL_CONF))
	
	print "Sign site certificate with CA: %s" % key
	run(SIGN_FORMAT.format(dir=OUT_DIR, openssl_cnf=OPENSSL_CONF,catype=key,keytype=CA_SITE_KEYTYPE,ext=EXT_NONE))

	print "Generate client key/certificate"
	run(KEY_FORMAT.format(dir=OUT_DIR, keytype=CA_CLIENT_KEYTYPE, openssl_cnf=OPENSSL_CONF ))
	run(CSR_FORMAT.format(days=365,host=host, dir=OUT_DIR, openssl_cnf=OPENSSL_CONF, keytype=CA_CLIENT_KEYTYPE, subject=CLIENT_SUBJECT.format(host=host)))
	run(SIGN_FORMAT.format(dir=OUT_DIR, openssl_cnf=OPENSSL_CONF,catype=key,keytype=CA_CLIENT_KEYTYPE,ext=EXT_NONE))
	cat_keycert(CA_CLIENT_KEYTYPE)
	run(P12_FORMAT.format(dir=OUT_DIR, openssl_cnf=OPENSSL_CONF,catype=key,keytype=CA_CLIENT_KEYTYPE))
	# run(PEM_FORMAT.format(dir=OUT_DIR, openssl_cnf=OPENSSL_CONF,keytype=CA_CLIENT_KEYTYPE))

	with open(os.path.join(OUT_DIR, 'ca-chain.crt'), 'w') as outfile:
		for ca in reversed(cas):
			with open(os.path.join(OUT_DIR, "%s.crt" % ca), 'r') as infile:
				outfile.write(infile.read())

else:
	# Generate a self-signed certificate without a CA
	print "Generate self-signed certificate"
	run(SITE_SELFSIGN_FORMAT.format(host=host, ip_address=ip_address, dir=OUT_DIR, openssl_cnf=OPENSSL_CONF))

	with open(os.path.join(OUT_DIR, 'ca-chain.crt'), 'w') as outfile:
		with open(os.path.join(OUT_DIR, 'site.crt'), 'r') as infile:
			outfile.write(infile.read())

	#### This seems like it won't work without a lot of hacks on the server side, so let's just disable it for now.
	# print "Generate self-signed client key/certificate"
	# run(CLIENT_SELFSIGN_FORMAT.format(host=host,ip_address=ip_address,dir=OUT_DIR,openssl_cnf=OPENSSL_CONF))
	# run(P12_FORMAT.format(dir=OUT_DIR, openssl_cnf=OPENSSL_CONF,keytype=CA_CLIENT_KEYTYPE))
	# run(PEM_FORMAT.format(dir=OUT_DIR, openssl_cnf=OPENSSL_CONF,keytype=CA_CLIENT_KEYTYPE))

run("httpd -D FOREGROUND")
