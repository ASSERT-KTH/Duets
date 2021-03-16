FROM maven:3-jdk-8

RUN apt-get update
RUN apt-get install -y python3 python3-pip git

COPY requirements.txt requirements.txt
RUN pip3 install --requirement requirements.txt 

RUN mkdir results
ENV M2_HOME=/usr/share/maven
ENV GITHUB_OAUTH=''

COPY maven-proxy.xml maven-proxy.xml
COPY *.py ./


CMD [ "./main.py" ]
