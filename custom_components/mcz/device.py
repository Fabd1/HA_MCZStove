import logging
from datetime import timedelta, datetime
from homeassistant.helpers.event import async_track_time_interval
from .pid import PIDController
from enum import Enum


_LOGGER = logging.getLogger(__name__)
# Mode debug : si True, les trames ne sont pas envoyées mais juste loguées
DEBUG_MODE = True


class StoveState(Enum):
    OFF = 0
    STARTUP = 1
    HEATING = 2
    IDLE = 3
    SHUTDOWN = 4

class MczStove:
    """Représente un poêle MCZ contrôlé via son ID."""   
    STARTUP_DURATION = timedelta(minutes=15)  # durée fixe du cycle de démarrage
    SHUTDOWN_DURATION = timedelta(minutes=2)  # durée d'extinction simulée

    

    def __init__(self, hass, device_id: str, name: str = "Poêle MCZ"):
        self.hass = hass
        self._device_id = device_id
        self._name = name
        self._pid = PIDController(kp=1.0, ki=0.1, kd=0.05)

        # États internes simulés
        self._is_on = False
        self._current_temp = 21.5
        self._target_temp = 22.0

        # Modes et réglages
        self._mode = 0          # 0=off, 1=manuel, 2=auto, 3=eco
        self._flame_power = 3   # 1-5
        self._fan1 = 3          # 1-5, 6=auto
        self._fan2 = 3          # 1-5, 6=auto
        self._beep = True       # True=on, False=off

        # Sauvegarde de la dernière trame envoyée
        self._last_frame = None

                # Protection anti-cyclage
        self._last_off_time: datetime | None = None
        self._min_off_duration = timedelta(minutes=30)  # par défaut 30 min

                # Planifie l’envoi périodique
        async_track_time_interval(hass, self._async_keep_alive, timedelta(minutes=5))

        self._state = StoveState.OFF



    # --- Accesseurs ---
    @property
    def id(self) -> str:
        return self._device_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def current_temperature(self) -> float:
        return self._current_temp

    @property
    def target_temperature(self) -> float:
        return self._target_temp

    @property
    def mode(self):
        """Retourne le mode courant sous forme de preset."""
        mapping = {0: "off", 1: "manual", 2: "auto", 3: "eco", 4: "comfort", 5: "sleep", 6: "away", 7: "boost"}
        return mapping.get(self._mode, "manual")
    
    @property
    def is_auto(self) -> bool:   # <-- ajouté pour Climate
        return self._mode == 2

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def mode(self) -> int:
        """Mode global: 0=off,1=manuel,2=auto,3=eco"""
        return self._mode

    @property
    def flame_power(self) -> int:
        return self._flame_power

    @property
    def fan1(self) -> int:
        return self._fan1

    @property
    def fan2(self) -> int:
        return self._fan2

    @property
    def beep(self) -> bool:
        return self._beep
    
    @property
    def state(self) -> StoveState:
        return self._state

     # ----------------
    # Helpers
    # ----------------
    def _get_next_frame_counter(self) -> int:
        """Incrémente le compteur de trame de 0 à 99 cycliquement."""
        if not hasattr(self, "_frame_counter"):
            self._frame_counter = 0
        self._frame_counter = (self._frame_counter + 1) % 100
        return self._frame_counter

    def _encode_device_id(self) -> bytes:
        """
        Encode l'ID du poêle (6 chiffres) en 3 octets BCD.
        Par exemple : "123456" → b'\x12\x34\x56'
        """
        if len(self._device_id) != 6 or not self._device_id.isdigit():
            raise ValueError("device_id doit contenir exactement 6 chiffres.")
        return bytes.fromhex(self._device_id)


    def build_frame(self) -> bytes:
        """
        Construit la trame binaire à envoyer au poêle MCZ.
        Format : 0C4302YYXXXXXXAABBCCDDEE80
        """
        header = bytes.fromhex("0C4302")
        counter = self._get_next_frame_counter().to_bytes(1, 'big')  # YY
        device_id = self._encode_device_id()  # 3 octets

        aa = b'\x01' if self._beep else b'\x00'  # Beep
        bb = self._fan1.to_bytes(1, 'big')      # Fan1
        cc = self._fan2.to_bytes(1, 'big')      # Fan2
        dd = self._flame_power.to_bytes(1, 'big')  # Flamme
        ee = self._mode.to_bytes(1, 'big')   # Mode

        footer = bytes.fromhex("80")

        frame = header + counter + device_id + aa + bb + cc + dd + ee + footer

        _LOGGER.debug("Trame binaire construite: %s", frame.hex().upper())
        return frame

    async def _send_frame(self):
        """Envoie la trame via RFXTRX plusieurs fois."""
        frame = self.build_frame()    
        self._last_frame = frame
        _LOGGER.debug("Trame construite pour %s: %s", self._device_id, frame)

        if DEBUG_MODE:
            _LOGGER.warning("[DEBUG MODE] Trame non envoyée, seulement loguée: %s", frame)
            return

        for i in range(3):  # 3 répétitions
            _LOGGER.debug("Envoi trame MCZ (%s): %s", i+1, frame)
            await self.hass.services.async_call(
                "rfxtrx", "send",
                {"event": frame.hex()}  # ⚠️ à adapter selon format attendu
            )

    async def _async_keep_alive(self, now):
        """Réémet périodiquement la dernière trame et met à jour l’état du poêle."""
        _LOGGER.debug("Keep-alive appelé pour %s", self._device_id)

        now = datetime.now()

        # Vérification fin de démarrage
        if self._state == StoveState.STARTUP:
            if self._startup_end_time and now >= self._startup_end_time:
                self._set_state(StoveState.HEATING)

        # Vérification fin d’extinction
        if self._state == StoveState.SHUTDOWN:
            if self._shutdown_end_time and now >= self._shutdown_end_time:
                self._set_state(StoveState.OFF)

        # Réémet la dernière trame si dispo
        if self._last_frame:
            _LOGGER.debug("Réémission périodique de la trame")
            await self._send_frame()


   # --- Helpers internes ---
    def _set_state(self, new_state: StoveState):
        if self._state != new_state:
            _LOGGER.info("Changement d'état du poêle %s: %s → %s", self._device_id, self._state.name, new_state.name)
            self._state = new_state
            if new_state == StoveState.STARTUP:
                self._startup_end_time = datetime.now() + self.STARTUP_DURATION
            elif new_state == StoveState.SHUTDOWN:
                self._shutdown_end_time = datetime.now() + self.SHUTDOWN_DURATION
            elif new_state == StoveState.OFF:
                self._startup_end_time = None
                self._shutdown_end_time = None

    # --- Commandes asynchrones ---

    async def async_turn_on(self):
        _LOGGER.debug("Envoi ON pour l’appareil %s", self._device_id)
        self._is_on = True
        self._mode = 2  # Mode AUTO par défaut quand on allume
        self._set_state(StoveState.STARTUP)
        await self._send_frame()

    async def async_apply_pid(self, pid_power: float):
        now = datetime.now()
        if self._state == StoveState.STARTUP:
            if self._startup_end_time and now >= self._startup_end_time:
                self._set_state(StoveState.HEATING)
            else:
                return  # on ne touche à rien pendant le démarrage

        if pid_power <= 0:
            # anti-cyclage
            if self._last_off_time and now - self._last_off_time < self.min_off_duration:
                return
            await self.async_turn_off()
        else:
            self._set_state(StoveState.HEATING)
            await self.async_turn_on()


    async def async_turn_off(self):
        """Éteint le poêle."""
        _LOGGER.debug("Envoi OFF pour l’appareil %s", self._device_id)
        self._is_on = False
        self._mode = 0  # Mode OFF par défaut quand on éteint
        self._set_state(StoveState.SHUTDOWN)
        self._last_off_time = datetime.now()  # mémorise l'heure de l'arrêt
        await self._send_frame()


    async def async_set_temperature(self, temperature: float):
        """Change la température cible."""
        _LOGGER.debug("Envoi température=%s pour %s", temperature, self._device_id)
        self._target_temp = temperature
        await self._send_frame()

    async def async_set_mode(self, mode: str):
        mapping = {
            "eco": 3,
            "comfort": 4,
            "sleep": 5,
            "away": 6,     # <-- ajouté
            "boost": 7,    # <-- ajouté
        }
        if mode in mapping:
            self._mode = mapping[mode]
            _LOGGER.debug("Changement de mode=%s (%s) pour %s", mode, self._mode, self._device_id)
            if mode == "eco":
                self._target_temp = 19
            elif mode == "comfort":
                self._target_temp = 21
            elif mode == "sleep":
                self._target_temp = 18
            elif mode == "away":
                self._target_temp = 16
            elif mode == "boost":
                self._target_temp = 23
        else:
            _LOGGER.warning("Mode inconnu: %s", mode)

        await self._send_frame()

    async def async_set_flame_power(self, power: int):
        """Réglage de la puissance de la flamme (1-5)."""
        if 1 <= power <= 5:
            _LOGGER.debug("Envoi flame_power=%s pour %s", power, self._device_id)
            self._flame_power = power
        else:
            _LOGGER.warning("Flame power invalide %s", power)

    async def async_set_fan(self, fan_num: int, value: int):
        """Réglage du ventilateur 1 ou 2 (1-5, 6=auto)."""
        if fan_num == 1 and 1 <= value <= 6:
            _LOGGER.debug("Envoi fan1=%s pour %s", value, self._device_id)
            self._fan1 = value
        elif fan_num == 2 and 1 <= value <= 6:
            _LOGGER.debug("Envoi fan2=%s pour %s", value, self._device_id)
            self._fan2 = value
        else:
            _LOGGER.warning("Fan %s valeur invalide %s", fan_num, value)

    async def async_set_beep(self, on: bool):
        """Active ou désactive le beep."""
        _LOGGER.debug("Envoi beep=%s pour %s", on, self._device_id)
        self._beep = on
    
    async def async_set_manual(self):  # <-- ajouté
        self._mode = 1
        _LOGGER.debug("Mode manuel activé pour %s", self._device_id)
        await self._send_frame()

    async def async_set_auto(self):  # <-- ajouté
        self._mode = 2
        _LOGGER.debug("Mode auto activé pour %s", self._device_id)
        await self._send_frame()
