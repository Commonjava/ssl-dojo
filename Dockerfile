FROM centos
MAINTAINER John Casey <jdcasey@commonjava.org>

RUN yum makecache fast
RUN yum -y update
RUN yum -y install openssl httpd mod_ssl hostname

RUN mkdir -p /var/www/html/ssl-config /etc/httpd

ENV CA_TYPE=self CA_HOST=test.myco.com

EXPOSE 80 443

ADD config/welcome.conf /etc/httpd/conf.d/welcome.conf

ADD config/openssl.cnf /var/www/html/ssl-config/openssl-files/openssl.cnf.in
ADD config/httpd.conf /etc/httpd/conf/httpd.conf.in
ADD config/ssl.conf /etc/httpd/conf.d/ssl.conf.in

ADD cgi/*.py /var/www/cgi-bin/
RUN chmod +x /var/www/cgi-bin/*.py
RUN chmod o+rwx /var/www/html
RUN mkdir -p /var/www/html/private
RUN chmod o+rwx /var/www/html/private

ADD start.py /usr/local/bin/start.py
RUN chmod +x /usr/local/bin/start.py

CMD /bin/bash
#ENTRYPOINT /usr/local/bin/start.py
