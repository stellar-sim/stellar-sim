import json
import sys
import os

def load_json_config(config_path, config_name="Generic", is_critical=False):
    """
    Carica un file di configurazione JSON con gestione degli errori robusta.
    """
    if not os.path.exists(config_path):
        print(f"[ERRORE CONFIG] File '{config_path}' per '{config_name}' non trovato.")
        if is_critical:
            print(f"[ERRORE CRITICO] Impossibile proseguire senza il file {config_path}. Uscita.")
            sys.exit(1)
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"[CONFIG] '{config_name}' caricato con successo da '{config_path}'.")
        return config
    except json.JSONDecodeError:
        print(f"[ERRORE CONFIG] Il file '{config_path}' per '{config_name}' non è un JSON valido.")
        if is_critical:
            sys.exit(1)
        return None