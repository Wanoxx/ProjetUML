from core.AbstractUpdatable import AbstractUpdatable
from core.AbstractObservable import AbstractObservable
from core.MessageBus import MessageBus

class Sensor(AbstractUpdatable):
    """
    Capteur de base. Génère un envoi de donnée sur le bus de message dès que
    son intervalle temporel de lecture est dépassé lors de l'appel à update(dt).
    """
    def __init__(self, target_observable: AbstractObservable, bus: MessageBus, interval: float, channel_name: str):
        if not isinstance(target_observable, AbstractObservable):
            raise TypeError("target_observable doit hériter d'un AbstractObservable.")
        if not isinstance(bus, MessageBus):
            raise TypeError("bus doit être une instance de MessageBus.")
        if not isinstance(channel_name, str):
            raise TypeError("channel_name doit être une chaine de caractères.")
        
        self.target_observable = target_observable
        self.bus = bus
        self.interval = interval
        self.channel_name = channel_name
        self._time_since_last_read = 0.0

    def update(self, dt: float) -> None:
        """
        Appelé à chaque avancement de l'horloge/simulation.
        On ajoute dt au compteur et si la fréquence de lecture est atteinte ou dépassée,
        on lit et on publie.
        """

        # on arrondit le temps pour éviter les problèmes d'imprécision flottante
        self._time_since_last_read = round(self._time_since_last_read + dt, 5)
        
        if self._time_since_last_read >= self.interval:
            self._read_and_publish()
            self._time_since_last_read -= self.interval

    def _read_and_publish(self):
        """Récupère la valeur de l'observable ciblé et l'envoie via le bus."""
        # On sait que c'est un observable, donc on peut appeler get_value() dessus.
        val = self.target_observable.get_value()
        
        # On publie sur le bus géré par le contrôleur
        self.bus.publish(self.channel_name, val)
