FROM python:3.7

COPY . app

RUN cd app && pip install .
RUN pip install requests

EXPOSE 8080
ENTRYPOINT [ "webhook-relay" ]
CMD [] 
