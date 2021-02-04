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

This is toop simple to comment something.
Now lets create a class which will represent our trained model.
We'll load the model once an instace is created and make predictions per user request. If translated to Python:

```
from time import sleep

class FancyModel:
  def __init__(self):
    # Here we load pretrained model. It lasts some long period
    sleep(0.05)

  def predict(self, text):
    sleep(0.005)
    return "Can't tell anything smart about: {}".format(text)
```

The article is not about any particular model or ML probem. That is why we modeled a result of long sleepless nights, of tremedous work you have done to obtain a model which at last behaves somewhat reasonable, with this simple class.
In real life you will use your favorite lib to load pretrained model here. Will, maybe, do some input validation also.
Here we keep it simple. We assume that loading a model takes 50mls and making prediction takes 5 mls.


Glueing all this together we have this:

```
import sys
from FancyModel import FancyModel

from flask import Flask

app = Flask(__name__)


@app.route("/")
def are_you_sure():
    fnc = FancyModel()
    return fnc.predit(request.get_json().text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=80)
```

This is ugly. With each incoming request we load the model.
This is like if you'll call tech support of your TV provider and they'll keep you on line for an hour.
I bet they'll miss your sign on next year contract.
So let's go little further and do another ugly thing.

```
import sys
from FancyModel import FancyModel

from flask import Flask

fnc = FancyModel()
app = Flask(__name__)


@app.route("/")
def are_you_sure():
    return fnc.predit(request.get_json().text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=80)
```

Yeeehaa. It does not need to load model with each request now. Isn't this good? Definitely No.
The proiblem with this is that some frameworks you may use may be not thread safe.
For example google "tensorflow fork safety". And this may be the case not only with tensorflow and forking.
So let's go further. We need each model to live in it's own process.
Here we have multiple options. E.g. go ahead with pure python. Create a pool of long living processes, take care of lifetime of those etc. 
We'll not do so. Instead we'll use such a inhabitant of uwsgi as [mule](https://uwsgi-docs.readthedocs.io/en/latest/Mules.html).
And here is how the request will be servied now:

user -> nginx -> uwsgi -> app.main -> queue -> mules -> cache -> uwsgi -> ngnix -> user

Once http server gets the requst and forwards it to our application we:
    1. Generate a uuid for the request and put the request to the queue.
    2. Messege the mules. If all the tasks are complete the mules are waiting for aknowledgement that there is a taks to serve.
    3. Wait for results to apear in the cache
In their turn, mules:
    1. Listen for the aknopwledgement messege.
    2. Once it is received, poll the queue of tasks,
    3. Make prediction and add result to cache with request uuid as key


Let's add a mule to our project:
First, we now need to make some configuration changes to uwsgi. And here is the new configuration.

```
[uwsgi]
module = main
callable = app
mule=hard_working_mule.py
mule=hard_working_mule.py
mule=hard_working_mule.py
mule=hard_working_mule.py

master = true
queue = 100
queue-blocksize = 2097152
cache2 = name=fcache,items=10,blocksize=2097152
```

Let's go line by line.
uWSGI server needs to know where to find the application’s callable and the first 2 lines are about that.
Next we specify what will be run by each mule and, as you can see, we want 4 mules to be initialized.
Code run by each mule comes shortly.
Next uwsgi [queue](https://uwsgi-docs.readthedocs.io/en/latest/Queue.html) and [cache](https://uwsgi-docs.readthedocs.io/en/latest/Caching.html) are initialized.
Ok, I know you noticed it. We missed a line 
```
master = true
```
With this we initiate a thread called "the cache sweeper". It's purpose is to remove expired keys from cache. Kind of guard if we'll miss something.

As promissed, this is what each mule is going to do:

```
import uwsgi
import json
import os
from FancyModel import FancyModel
from serving.config import TEXT_KEY, CACHE_NAME


if __name__ == '__main__':
    fnc = FancyModel()
    while True:
        uwsgi.mule_get_msg()
        req = uwsgi.queue_pull()
        if req is None:
            continue
        json_in = json.loads(req.decode("utf-8"))
        text = json_in[TEXT_KEY]
        # to store transliterations
        json_out = {"res": fnc.predict(text)}
        uwsgi.cache_update(json_in.get("id"), json.dumps(json_out, ensure_ascii=False), 0, CACHE_NAME)
```
And the main logic:

```
app = Flask(__name__)
api = Api(app)

def process_request(json_in):
    uid = str(uuid.uuid4())
    json_in["id"] = uid
    uwsgi.queue_push(json.dumps(json_in))
    # Actual content of message does not really matter
    # This is just to triger mule execution
    uwsgi.mule_msg("s")
    while not uwsgi.cache_exists(uid, CACHE_NAME):
        continue
    res = uwsgi.cache_get(uid, CACHE_NAME)
    uwsgi.cache_del(uid, CACHE_NAME)
    return Response(response=res,
                            status=200,
                            mimetype="application/json")


@app.route('/predict', methods=['POST'])
def predict(source, target):
    return process_request(request.get_json())
```

Looks good, doesn't it? And again no. Let's see what's going on.
First of all: That ugly "while True:" in mule code. But let's assume we are good programmers and that is not a problem.
As specified we have 4 mules running to serve our needs.
But wait. Who says that 4 mules are good choice? How do we came up with this number. What if we have a very big request rate, so that 4 mules does not mangage to serve all requests in time. In that case the queue will fill up and we'll start loosing requests. This means that we also need to chose carefully the size of queue. But how? What must be the rationale behind that decision? No rationale other than practice, which can change and blow everything.
"But wait" - you can say. - "We can scale the app to serve more requests."
Ok. Package all this mess in docker and scale with replication. In that case the granularity of our scaling is 4 mules, plus processes running main code, etc. This is a classical wast of resources.
What if we have a lot of models which must be served (maybe we are providing translation from 45 languages and have separate model trained for each pair). What must be the strategy? Load all in a single mule and probably run out of queue? Keep another 4 mules for each model and waste as much resources as possible?
Another thing to take care: What if mule takes the request and dies during serving it. We hang waiting for the result to appear in the cache.
And it goes worse with each particular solution bringing new questions to the table.

So what to do? Tadaaaam: Meet (Ray)[https://docs.ray.io/en/master/index.html]
Lets not talk a lot about how good it is and start using it.
I am not going to describe all the steps of deploying Ray. It is well described in the documentation. Rahther we'll look into simple usecase convering what we had earlier with ngnix and uwsgi. BTW, ray has incrediblely responsive community. Try asking your questions on Slack channel if you have one.

We asuume that you have kubernates and kubectl configured to interact with it. If not, you can experiment with (minikube)[https://minikube.sigs.k8s.io/docs/start/].
It is well documented how you can (deploy Ray cluster on you kubernetes)[https://docs.ray.io/en/master/cluster/kubernetes.html].
To keep it short:
1. Download from (repo)[https://github.com/ray-project/ray/tree/master/doc/kubernetes] the configuration files:
2. Create namespace in the kubernates with
```
kubectl create -f ray/doc/kubernetes/ray-namespace.yaml
```
3. Deploy ray cluster with:
```
kubectl apply -f ray/doc/kubernetes/ray-cluster.yaml
```
Definitely you need to look little more into this yaml files to understand whats going on. But those are pretty self explanatory and with the little googling even not experienced user of kubernates can understand what's going on there.

We are done. Ray is up and running on your kubernates.
Check it if you want:
```
kubectl get pods -n ray
```
You can see 3 worker nodes there. Want to change it? Change the number of worker node replicas in above yaml, reapply the config and find out as much of workers as you want.
Go further and kill one of workers - it will rise again. Configure autoscaling - there is even a kubernates operator for autoscaling. And there is more of kubernates like nitty-gritty features.

Now, assuming there is aleady ray cluster launched deploying our model will be something like:

```
import ray
from ray import serve
from FancyModel import FancyModel
# connect to Ray cluster
ray.init(address="auto")
client = serve.start(detached=True, http_options={"host": "0.0.0.0"})
client.create_backend("lr:v1", FancyModel)
client.create_endpoint("fancy_predictor", backend="lr:v1", route="/predict")
```
Yeeehaaa. It is there. Try to request it. And you know what? It comes with candies: scaling, incremental rollout, splitting traffic between backends (say different versions of trained model), session affinity, monitoring and many more.

Lets talk a little about what's going on above.
First we initialize ray runtime. This assumes there is already a long living Ray cluster which can be reached and to which we connect.
Afterwards we start (Ray Serve)[https://docs.ray.io/en/master/serve/index.html] on it. (Serve)[https://docs.ray.io/en/master/serve/index.html] is the cream of our donut. It's created on top of (Ray actors)[https://docs.ray.io/en/master/actors.html#actor-guide], it is framework agnostic, it is python-first, it is Rayish. Some key concepts of serve we used here:
Backend - this is the business logic of the application. So in our case this is FancyModel with all it's structure, and interface.
Endpoint - this is what allows us to interact with backends via HTTP. Endpoints can have one or multiple backends (for example multiple models of translation from armenian to english can be served under one endpoint).
If you noticed when starting Ray Serve we specified "detached=True". This is because the lifecycle of Ray Serve is coupled with the client which is returned from serve.start().
Once it goes out of scope the serve instance will be destroyed. But as we remember we need long living models, so those are not loaded with each request. Detached Serve solves this issue.

## Summary

We started with a simple option of deploying ML model in a toy, non production grade Flask service. Than developed it to a more robust, produciton ready, still very messy solution. Finally we have used Ray, as it is advertised, - simple, universal API for building distributed applications. With all the tools it provides it is much easier now to deploy your models to the prodction. In conjuction with other ML R&D, Ops, tools (like MLFlow, aimhubio, etc..) it is now much easier to manage lifecycle of your ML product from training, evaluating your model to deploying it to production.
