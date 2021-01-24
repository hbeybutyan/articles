# Deploy your model to production.

Machine learning gathers more and more attention with each day. With that, demand for production ready deployments of ML models increases drastically.
In this article we are going to dicsuss how to deply your machine learning model to production.
We'll start with simple approach which is not something to do in production.
Will increase the complexity of the solution.
And, at the end, after torturing you with all these nightmare, we'll finish with the right way to deploy and serve your models.

## Prerequisites
1. We use linux
2. Python 3
3. Flask
4. uwsgi
5. docker
6. Ray


The most part of resources available in net suggest you to deploy ML model behind a Flask API and serve it.
Something like this [Thanks to Luigi Patruno for good series of articles](https://mlinproduction.com/):


```
import logging

from flask import Flask, request

app = Flask(__name__)

model = None

@app.before_first_request
def load_model():
    global model
    model = some_fancy_loading_logic()

@app.route('/predict', methods=['POST'])
def predict():
    """Return a machine learning prediction."""
    global model
    data = request.get_json()
    loginfo('Incoming data: {}'.format(data))
    prediction = model.predict(data)
    inp_out = {'input': data, 'prediction': prediction}
    loginfo(inp_out)
    return inp_out

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
```

It's incredible. Isn't it?
Short answer: No.
Mid size long answer:
Flask internal server is not supposed to be used for production.
Here is a short article describing why: [Flask Is Not Your Production Server](https://build.vsupalov.com/flask-web-server-in-production/)
and [Official documentation](https://flask.palletsprojects.com/en/1.1.x/tutorial/deploy/#run-with-a-production-server) clearly stating not to use flask internal server but rather use a production WSGI server. So we'll start with that. 
To acomplish this task, keeping in mind the golden rule (If somebody has done it - use it, don't invent it again!) we'll use [this] https://github.com/tiangolo/uwsgi-nginx-flask-docker as a parent docker image (thanks to [Sebastián Ramírez](https://github.com/tiangolo)). As described in the repo, there are better alternatives, but as we are going to use this for demonstrativon puporses, the image suffices all our needs.
And here is the final Dockerfile we'll use to create image:
```
FROM tiangolo/uwsgi-nginx-flask:python3.6

COPY ./requirements.txt /tmp
RUN pip3 install --upgrade pip \
  && pip3 install -r /tmp/requirements.txt

COPY ./app /app

#COPY entry.sh /entrypoint.sh
#RUN chmod +x /entrypoint.sh
```
As usual, requirements.txt will contain all the building boxex for our project (Tensorflow, Numpy, etc.).
The entrypoint.sh is used by parent image as an ENTRYPOINT (sounds too philosophyc), still if you want to understand what is entrypoint in dockerfil - google it, or read [this](https://docs.docker.com/engine/reference/builder/#understand-how-cmd-and-entrypoint-interact).
Basicaly  this is what your container will do once started. So if you want to customize the behavior of container customize the file. Otherwise leave it as is.
And the meat of the dockerfile - /app directory.
This is there all the magic will happen. This is the app which will be run in wsgi to serve our model.
To understand fancy things happening when deploying your flask app wioth nginx and wsgi look at [this](https://flask.palletsprojects.com/en/1.0.x/deploying/uwsgi/).

Let's create a simple main.py with following content:

```

import sys

from flask import Flask

app = Flask(__name__)


@app.route("/")
def are_you_sure():
    return "Still want to continue?"


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=80)
```

