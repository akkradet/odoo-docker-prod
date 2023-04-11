FROM odoo:15.0

LABEL MAINTAINER Akkradet K.<akkradet7@gmail.com>
USER root

ENV TZ=Asia/Bangkok
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
   
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y --no-install-recommends awscli python3-wheel locales tzdata git curl fonts-thai-tlwg gcc libpython3-dev
RUN pip3 install --upgrade pip
RUN pip3 install unicodecsv unidecode pysftp psycopg2 pysftp zeep paramiko odoo-test-helper flanker num2words==0.5.12 xlwt xlrd openpyxl promptpay pyOpenSSL barcode bahttext netifaces numpy zxcvbn flanker pandas bs4 PyJWT validators html2text openai regex cryptography xmlsig phonenumbers jsonschema --no-cache-dir

USER odoo 
