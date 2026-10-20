import os
import sys
import importlib.util
import inspect

def find_gui(folder_path):
    """Cherche dynamiquement la classe qui hérite de AbstractSystemGUI dans un dossier, 
    cette fonction est utilisé par SimLauchController dans controller.py."""
    
    # on check si le dossier est dans le path systeme pour eviter les erreurs d'import, sinon on l'ajoute
    if folder_path not in sys.path:
        sys.path.insert(0, folder_path)

    # boucle qui parcourt tous les fichiers presents dans le repertoire cible
    for filename in os.listdir(folder_path):
        
        # on filtre pour cibler seulement les scripts python normaux en excluant le init
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            try:
                file_path = os.path.join(folder_path, filename)
                
                # on load le module en memoire directement depuis son chemin
                # importlib est utile ici pour forcer l'execution et l'importation de code python a la volée
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # boucle qui recupere et isole toutes les classes definies dans le script qu'on vient de charger
                # inspect permet de faire de l'introspection pour lire la nature des elements d'un code
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    
                    # on lit les bases de l'objet pour verifier si c'est bien la classe enfant qu'on cherche
                    if any(base.__name__ == 'AbstractSystemGUI' for base in obj.__bases__):
                        return obj  
            except Exception:
                # si le fichier a un souci de syntaxe on passe simplement au suivant sans crash
                continue 
                
    return None