from training import (
    DeepLabV3Trainer,
    FCNTrainer
)
from metrics import Charts

deeplab_v3_trainer = DeepLabV3Trainer()
fcn_trainer = FCNTrainer()

charts = Charts()

class TrainingService():

    def __init__(self):
        pass

    def train_models(self):
        self.train_fcn()
        self.train_deep_lab()

    def train_deep_lab(self):
        deeplab_v3_trainer.train_model()
        deeplab_v3_trainer.save_results()
        charts.plot_charts(deeplab_v3_trainer.metrics_tracker)

    def train_fcn(self):
        fcn_trainer.train_model()
        fcn_trainer.save_results()