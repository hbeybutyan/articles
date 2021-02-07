from FancyModel import FancyModel
import uwsgi
import json

if __name__ == '__main__':
    fnc = FancyModel()
    while True:
        uwsgi.mule_get_msg()
        req = uwsgi.queue_pull()
        if req is None:
            continue
        json_in = json.loads(req.decode("utf-8"))
        text = json_in["text"]
        # to store transliterations
        json_out = {"res": fnc.predict(text)}
        uwsgi.cache_update(json_in.get("id"), json.dumps(json_out, ensure_ascii=False), 0, "mcache")