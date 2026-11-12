class SpeedController:
    """Throttle e freio do mathDriver: ajusta aos poucos para manter a velocidade na faixa."""

    LAUNCH_STEPS = 10
    THROTTLE_UP = 0.01
    THROTTLE_DOWN = 0.001
    OVERSPEED_BRAKE = 0.5

    # Em curvas, freia acima desta velocidade
    CORNER_STEERING = 0.1
    CORNER_SPEED = 5.0
    CORNER_BRAKE = 2.0

    def __init__(self, min_speed, max_speed):
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.throttle = 0.5
        self.step = 0


    def update(self, speed, steering):
        self.step += 1

        if self.step <= self.LAUNCH_STEPS:
            return 1.0, 0.0

        brake = 0.0

        if speed > self.max_speed:
            self.throttle -= self.THROTTLE_DOWN
            brake = (speed - self.max_speed) * self.OVERSPEED_BRAKE
        elif speed < self.min_speed:
            self.throttle += self.THROTTLE_UP
        else:
            self.throttle -= self.THROTTLE_DOWN

        if abs(steering) > self.CORNER_STEERING and speed > self.CORNER_SPEED:
            brake = abs(steering) * self.CORNER_BRAKE

        self.throttle = min(max(self.throttle, 0.0), 1.0)
        return self.throttle, min(brake, 1.0)
