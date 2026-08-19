from training import (
    Trainer
)
from metrics import Charts

charts = Charts()

class TrainingService():

    def __init__(self):
        pass

    def train_models(self):
        self.train_fcn()
        print('=======================================================================================')
        self.train_deep_lab()

    def train_deep_lab(self):
        trainer = Trainer('deeplabv3+')
        trainer.train_model()
        trainer.save_results()
        # charts.plot_charts(trainer.metrics_tracker)

    def train_fcn(self):
        trainer = Trainer('fcn')
        trainer.train_model()
        trainer.save_results()