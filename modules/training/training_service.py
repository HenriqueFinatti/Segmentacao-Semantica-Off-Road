from modules.models.registry import MODELS
from modules.training.trainer.trainer import Trainer

class TrainingService():

    def __init__(self):
        pass

    def train_models(self):
        for model_name in MODELS:
            self.train_model(model_name)

    def train_model(self, model_name):
        print(f'Treinando {model_name.upper()}...')
        trainer = Trainer(model_name)
        trainer.train_model()

    def train_deep_lab(self):
        self.train_model('deeplabv3+')

    def train_fcn(self):
        self.train_model('fcn')
