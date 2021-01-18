# Deploy your model to produciton.

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
Something like:


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
