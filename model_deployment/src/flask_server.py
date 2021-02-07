from flask import Flask, request

app = Flask(__name__)
model = None


def some_fancy_loading_logic():
    # Load your model here
    return None


@app.before_first_request
def load_model():
    global model
    model = some_fancy_loading_logic()


@app.route('/predict', methods=['POST'])
def predict():
    global model
    data = request.get_json()
    prediction = model.predict(data)
    inp_out = {'input': data, 'prediction': prediction}
    return inp_out


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
