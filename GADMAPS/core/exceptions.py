class NotIdentifierError(Exception):
    """Exception levée lorsqu'un nom de composant ou d'observable n'est pas un identifiant Python valide."""
    pass

class DuplicateNameError(Exception):
    """Exception levée lorsqu'il y a un conflit de noms dans les composants ou observables."""
    pass

class InvalidHierarchyError(Exception):
    """Exception levée lorsqu'il y a une hiérarchie invalide entre composants (ex: un composant est son propre enfant, un composant est son propre parent, etc.)."""
    pass