from typing import Callable

class MessageBus:
    """
    Bus de messages utilisé par les capteurs et l'interface.
    Permet d'échanger les valeurs lues par les capteurs avec l'interface.
    """
    def __init__(self):
        # Dictionnaire où la clé est le "channel" (ex: "car/engine/temp")
        # et la valeur est une liste de fonctions callbacks.
        self._subscribers = {}

    def subscribe(self, channel: str, callback: Callable):
        """Abonne une fonction callback à un channel spécifique."""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        if callback not in self._subscribers[channel]:
            self._subscribers[channel].append(callback)

    def unsubscribe(self, channel: str, callback: Callable):
        """Désabonne une fonction d'un channel."""
        if channel in self._subscribers and callback in self._subscribers[channel]:
            self._subscribers[channel].remove(callback)

    def publish(self, channel: str, data: any):
        """Publie une donnée sur un channel. Appelle tous les callbacks abonnés."""
        if channel in self._subscribers:
            for callback in self._subscribers[channel]:
                callback(data)

    def get_channels(self) -> list[str]:
        """Renvoie la liste de tous les channels actuellement utilisés."""
        return list(self._subscribers.keys())