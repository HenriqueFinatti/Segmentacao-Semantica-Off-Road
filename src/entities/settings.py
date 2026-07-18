import json

class Settings():

    def __init__(self):
        with open('./settings.json', 'r', encoding='utf-8') as settings:
            self.settings = json.load(settings)

    def isEarlyStoppingOn(self):
        return self.settings["EarlyStopping"]
        
    def isChartsOn(self):  
        return self.settings["Charts"]
    
    def isFreiburgForestOn(self):
        return self.settings["Freiburg_Forest"]
    
    def isSyntheticOffRoadOn(self):
        return self.settings["Synthetic_Offroad"]
    
    def getEpochs(self):
        return self.settings["Epochs"]
    
    def getPatience(self): 
        return self.settings["Patience"]