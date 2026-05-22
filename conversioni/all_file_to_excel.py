import pandas as pd
import os


def crea_excel_da_cartella(cartella_input, file_output):
    """
    Legge tutti i file .csv e .parquet in una cartella e li unisce in un unico
    file Excel, con un foglio per ogni file.

    Args:
        cartella_input (str): Il percorso della cartella contenente i file.
        file_output (str): Il nome del file Excel da creare (es. 'report.xlsx').
    """

    # Controlla se la cartella di input esiste
    if not os.path.isdir(cartella_input):
        print(f"ERRORE: La cartella '{cartella_input}' non esiste.")
        return

    # Inizializza l'ExcelWriter di pandas, che permette di scrivere su più fogli
    try:
        with pd.ExcelWriter(file_output, engine='openpyxl') as writer:
            print(f"Creazione del file Excel: '{file_output}'...")

            # Itera su ogni file nella cartella specificata
            for nome_file in sorted(os.listdir(cartella_input)):
                percorso_completo = os.path.join(cartella_input, nome_file)

                # Estrae il nome del file senza estensione per usarlo come nome del foglio
                nome_foglio = os.path.splitext(nome_file)[0]

                if len(nome_foglio)>25:
                    nome_foglio=nome_foglio[-25:]

                #if len(nome_file)>20:
                #    nome_foglio=nome_foglio[:20]+len(nome_file)

                df = None  # Inizializza il DataFrame a None

                # Se è un file CSV, leggilo
                if nome_file.endswith('.csv'):
                    try:
                        df = pd.read_csv(percorso_completo, sep=";", decimal=',', encoding='latin-1')
                        print(f" -> Letto file CSV: '{nome_file}'")
                    except Exception as e:
                        print(f"ATTENZIONE: Impossibile leggere il file CSV '{nome_file}'. Errore: {e}")

                # Se è un file Parquet, leggilo
                elif nome_file.endswith('.parquet'):
                    try:
                        df = pd.read_parquet(percorso_completo)
                        print(f" -> Letto file Parquet: '{nome_file}'")
                    except Exception as e:
                        print(f"ATTENZIONE: Impossibile leggere il file Parquet '{nome_file}'. Errore: {e}")

                # Se il DataFrame è stato letto correttamente, scrivilo su un nuovo foglio
                if df is not None:
                    # 'index=False' evita di scrivere l'indice del DataFrame come prima colonna nel foglio Excel
                    df.to_excel(writer, sheet_name=nome_foglio, index=False)
                    print(f"    - Aggiunto foglio: '{nome_foglio}'")

        print(f"\nOperazione completata con successo! Il file '{file_output}' è stato creato.")

    except Exception as e:
        print(f"ERRORE: Si è verificato un problema durante la creazione del file Excel. Dettagli: {e}")


# --- CONFIGURAZIONE ---
# Modifica queste due righe con i tuoi percorsi
if __name__ == "__main__":
    # IMPORTANTE: Inserisci qui il percorso della cartella che contiene i tuoi file
    percorso_cartella_dati = '../scripts/output/BIRRE'

    # Inserisci qui il nome che vuoi dare al file Excel di output
    nome_file_excel_generato = '../scripts/output/BIRRE/all_data_BIRRE_0929.xlsx'
    # Esegui la funzione
    crea_excel_da_cartella(percorso_cartella_dati, nome_file_excel_generato)