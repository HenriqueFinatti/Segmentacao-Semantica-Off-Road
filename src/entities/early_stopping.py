class EarlyStopping:
    def __init__(self, patience=10, min_delta=0.0):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_miou = None
        self.should_stop = False

    def __call__(self, current_miou):
        if self.best_miou is None:
            self.best_miou = current_miou
        elif current_miou < self.best_miou + self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
        else:
            self.best_miou = current_miou
            self.counter = 0