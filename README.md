# SSL Dojo

This is a relatively simple Docker image for use in testing applications' HTTP client SSL features. On startup, it will generate certificates and CAs as appropriate for the selected profile, and then start an Apache HTTPd service using the result. This httpd then hosts the certificates under `/ssl-config/` so the client can download and use them during tests. It also hosts a couple of diagnostic CGIs and another one used to push test content up to the server during test setup.

SSL profiles and other configurations can be managed when the Docker container is started using environment variables (`-e` options to the `docker run` command).

## SSL Profiles

*NOTE:* All CAs mentioned below will be generated on startup.

### Self-Signed

Specify `CA_TYPE=self`.

### Signed by root CA

Specify `CA_TYPE=single`.

### Signed by an intermediary CA

Specify `CA_TYPE=multi`.

## Specifying the host in the certificate CN

By default, the host is set to `test.myco.com`. If you want to change it, specify `CA_HOST=<hostname>`.

## Exposed ports

The image also exposes ports 80 and 443 for mapping.

## Pushing test content

To push content up to the server for testing, you might use something that approximates the following command:

    $ curl -i -X PUT --data-binary @myfile.txt http://172.17.0.1/cgi-bin/put.py/myfile.txt

Then, you should be able to retrieve the content again using either http or https:

    $ curl -i http://172.17.0.1/myfile.txt
