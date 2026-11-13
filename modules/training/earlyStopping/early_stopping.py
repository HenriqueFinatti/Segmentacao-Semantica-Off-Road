class EarlyStopping:
    def __init__(self, settings):
        self.settings = settings

        self.patience = self.settings.get_patience()
        self.min_delta = 0.0
        self.counter = 0
        self.best_miou = None
        self.should_stop = False


    def __call__(self, current_miou):
        if not self.settings.is_early_stopping_on():
            return

        if self.best_miou is None:
            self.best_miou = current_miou
            return
        
        if current_miou <= self.best_miou + self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
            return
        
        self.best_miou = current_miou
        self.counter = 0