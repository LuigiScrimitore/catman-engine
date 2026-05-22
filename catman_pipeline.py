# file: run_pipeline.py

import subprocess
import sys
import time
import datetime

from sqlalchemy import false

import utils as utl
import output
import converter
import read_data_from_db

readDBflag=True
convertFlag=False
pipelineFlag=False
pubblicazioneFlag=False

def main():
    """
    Funzione principale che orchestra l'esecuzione della pipeline.
    """

    print("=" * 50)
    print("🚀 Avvio CatManDo ",datetime.datetime.now())
    print("=" * 50)

    if readDBflag:
        ################################################
        # ESTRAZIONE DATI DAL DB
        ################################################
        print("\n" + "=" * 50)
        print("▶️  inizio download dati dal db")
        print("=" * 50)

        startDownload = time.time()
        read_data_from_db.downloadDataFromDB()

        print('Fine download dati dal db in %.1f minuti.'  % ((time.time() - startDownload)/60))
        print("=" * 50)

    if convertFlag:
        ################################################
        # CONVERSIONE FILE
        ################################################
        print("\n" + "=" * 50)
        print("▶️  inizio generazione file per Pipeline e Tableau")
        print("=" * 50)

        startConversion = time.time()

        converter.convertAllData()

        print('Fine generazione file in %.1f minuti.'  % ((time.time() - startConversion)/60))
        print("=" * 50)

    if pipelineFlag:
        ################################################
        # ELABORAZIONE DATI
        ################################################
        categories = utl.get_Categorie()
        print(f"Trovate {len(categories)} categorie da elaborare.")
        print(categories)

        configs = utl.get_Config()

        pipeline_list = utl.get_PipelineList()
        script_path = configs['paths']['script_path']
        print(pipeline_list)
        # print(script_path)

        if not categories:
            print("Nessuna categoria da elaborare. Uscita.")
            sys.exit(1)  # Esce con un codice di errore

        # Loop principale: itera su ogni categoria
        for i, category in enumerate(categories, 1):
            print("\n" + "=" * 70)
            print(f"▶️  Inizio elaborazione per la categoria: '{category}' ({i}/{len(categories)})")
            print("=" * 70)

            startCategoria = time.time()
            # script_principale_dir = Path(__file__).parent.resolve()

            # Per ogni categoria, esegue in sequenza tutti gli script della pipeline
            for script_name in pipeline_list:
                try:
                    start = time.time()
                    # print(f"   -> Esecuzione di '{script_name}' per '{category}'...")

                    script_name = script_path + script_name
                    print(f"   -> Esecuzione di '{script_name}' per '{category}'...")

                    # Costruisce il comando da eseguire: python script.py categoria
                    command = [sys.executable, script_name, category]

                    # Esegue il comando.
                    # 'check=True' fa sì che venga sollevata un'eccezione se lo script fallisce.
                    # 'capture_output=True' e 'text=True' catturano l'output dello script.
                    result = subprocess.run(
                        command,
                        check=True
                    )

                    # Stampa l'output dello script eseguito (utile per il debug)
                    #print(result.stdout)

                    print(f"   ✅ '{script_name}' completato con successo in %.1f secondi" % (time.time() - start))

                except FileNotFoundError:
                    print(f"   ❌ ERRORE: Lo script '{script_name}' non è stato trovato.")
                    print("   -> Interruzione della pipeline.")
                    return  # Interrompe tutto
                except subprocess.CalledProcessError as e:
                    # Questo blocco viene eseguito se lo script ritorna un errore
                    print(f"   ❌ ERRORE durante l'esecuzione di '{script_name}' per la categoria '{category}'.")
                    print(f"   Codice di errore: {e.returncode}")
                    print(f"   Output dell'errore:\n{e.stderr}")
                    print("   -> Interruzione della pipeline.")
                    return  # Interrompe tutto

            print(f"🎉 Elaborazione per la categoria '{category}' completata in %.1f secondi" % (time.time() - startCategoria))
            print("-" * 70)

        print("\n✨ Pipeline completata con successo per tutte le categorie! ",datetime.datetime.now())

    if pubblicazioneFlag:
        ################################################
        # PUBBLICAZIONE DATI
        ################################################
        print('generazione stima impatti per tutte le categorie')
        output.genaraStimaImpattiAll()


if __name__ == "__main__":
    main()
