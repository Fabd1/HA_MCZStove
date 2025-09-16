import logging

_LOGGER = logging.getLogger(__name__)

class PIDController:
    """Calcul de la puissance à appliquer selon consigne et température actuelle."""

    def __init__(self, kp: float, ki: float = 0.0, kd: float = 0.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self._integral = 0.0
        self._last_error = 0.0

    def compute(self, target_temp: float, current_temp: float) -> float:
        error = target_temp - current_temp
        self._integral += error
        derivative = error - self._last_error
        self._last_error = error

        pid_value = self.kp * error + self.ki * self._integral + self.kd * derivative
        _LOGGER.debug("PID compute: target=%s current=%s pid=%s", target_temp, current_temp, pid_value)
        return max(0.0, min(1.0, pid_value))  # puissance normalisée 0-1
