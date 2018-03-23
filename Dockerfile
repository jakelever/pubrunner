FROM python:3

RUN git clone https://github.com/jakelever/pubrunner.git
RUN pip install -e ./pubrunner/

CMD [ "echo", "Success." ]

