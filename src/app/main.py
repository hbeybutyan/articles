from flask import Flask, request, Response
import uuid
import json
import uwsgi

CACHE_NAME = "mcache"

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


app = Flask(__name__)


@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    return process_request(data)
