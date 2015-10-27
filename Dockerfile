FROM centos
MAINTAINER John Casey <jdcasey@commonjava.org>

RUN yum makecache fast
RUN yum -y update
RUN yum -y install openssl httpd mod_ssl hostname

RUN cp -rf /var/www /var/www-ssl
RUN mkdir -p /var/www/html/ssl-config /etc/httpd

ADD config/openssl.cnf /var/www/html/ssl-config/openssl-files/openssl.cnf.in
ADD config/httpd.conf /etc/httpd/conf/httpd.conf
ADD config/welcome.conf /etc/httpd/conf.d/welcome.conf
ADD config/ssl.conf /etc/httpd/conf.d/ssl.conf

ENV CA_TYPE=self CA_HOST=test.myco.com

EXPOSE 80 443

ADD start.py /usr/local/bin/start.py
RUN chmod +x /usr/local/bin/start.py

#CMD /bin/bash
ENTRYPOINT /usr/local/bin/start.py
