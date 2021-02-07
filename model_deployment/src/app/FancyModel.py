from time import sleep


class FancyModel:
    def __init__(self):
        # Here we load pretrained model. It lasts some long period
        sleep(0.05)

    def predict(self, text):
        sleep(0.005)
        return "Can't tell anything smart about: {}".format(text)
