from modules.training.trainer.trainer import Trainer

class TrainingService():

    def __init__(self):
        pass

    def train_models(self):
        print('Treinando FCN...')
        self.train_fcn()

        print('Treinando DeepLabV3+...')
        self.train_deep_lab()

    def train_deep_lab(self):
        trainer = Trainer('deeplabv3+')
        trainer.train_model()

    def train_fcn(self):
        trainer = Trainer('fcn')
        trainer.train_model()