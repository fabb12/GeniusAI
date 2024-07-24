import os
import subprocess
import shutil


class Wav2LipSync:
    def __init__(self, wav2lip_dir, checkpoint_file):
        """
        Inizializza la classe Wav2LipSync.

        :param wav2lip_dir: La directory del progetto Wav2Lip.
        :param checkpoint_file: Il percorso del file checkpoint Wav2Lip.
        """
        self.wav2lip_dir = wav2lip_dir
        self.checkpoint_file = checkpoint_file

        # Verifica se ffmpeg è installato
        if not shutil.which("ffmpeg"):
            raise EnvironmentError("FFmpeg non è installato o non è nel percorso di sistema. "
                                   "Installa FFmpeg e aggiungilo al percorso di sistema.")

    def sync(self, video_path, audio_path, output_path):
        """
        Esegue la sincronizzazione labiale utilizzando Wav2Lip.

        :param video_path: Il percorso del file video di input.
        :param audio_path: Il percorso del file audio di input.
        :param output_path: Il percorso del file video di output sincronizzato.
        :return: None
        :raises Exception: Se il processo di Wav2Lip fallisce.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Il file video non esiste: {video_path}")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Il file audio non esiste: {audio_path}")

        # Comando per eseguire lo script di inferenza di Wav2Lip
        command = [
            'python', os.path.join(self.wav2lip_dir, 'inference.py'),
            '--checkpoint_path', self.checkpoint_file,
            '--face', video_path,
            '--audio', audio_path,
            '--outfile', output_path
        ]

        # Esegui il comando e cattura l'output
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        # Controlla se il processo è terminato con successo
        if process.returncode != 0:
            raise Exception(f"Wav2Lip error: {stderr.decode('utf-8')}")

        print(f"Wav2Lip output: {stdout.decode('utf-8')}")


if __name__ == "__main__":
    # Percorsi di configurazione
    wav2lip_dir = "./Wav2Lip-master"
    checkpoint_file = os.path.join(wav2lip_dir, 'checkpoints', 'wav2lip_gan.pth')
    video_path = r"C:\temp\video.mp4"
    audio_path = r"C:\temp\audio.mp3"
    output_path = r"C:\temp\synced_video.mp4"

    # Istanzia la classe Wav2LipSync e esegui la sincronizzazione
    wav2lip = Wav2LipSync(wav2lip_dir, checkpoint_file)
    try:
        wav2lip.sync(video_path, audio_path, output_path)
        print(f"Video sincronizzato salvato in: {output_path}")
    except Exception as e:
        print(f"Errore durante la sincronizzazione: {e}")
