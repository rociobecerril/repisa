"""Transcribe las entrevistas con usuarios potenciales usando Whisper en local (sesión 13).

Uso (desde la carpeta del proyecto):
    pip install faster-whisper "av<17"
    python scripts/transcribir.py entrevistas

Nota: con Python 3.14, pip instala av 19, que es incompatible con faster-whisper
(TypeError: open() got an unexpected keyword argument 'metadata_errors'); por eso "av<17".

Lee los .m4a de la carpeta indicada y escribe transcripciones/entrevista_N.txt.
La carpeta transcripciones/ está en .gitignore: puede contener nombres o datos
personales y no se sube al repo. Al repo solo van las notas anonimizadas de
docs/research/.
"""

import sys
from pathlib import Path

from faster_whisper import WhisperModel

ORDEN = ["Avenida_San_Felipe.m4a", "Avenida_San_Felipe_2.m4a", "Avenida_San_Felipe_3.m4a"]


def main(carpeta: str = "entrevistas") -> None:
    origen = Path(carpeta).expanduser()
    destino = Path("transcripciones")
    destino.mkdir(exist_ok=True)

    # "small" es un buen equilibrio entre calidad en español y velocidad en una laptop.
    modelo = WhisperModel("small", device="cpu", compute_type="int8")

    for i, nombre in enumerate(ORDEN, start=1):
        audio = origen / nombre
        if not audio.exists():
            print(f"No encontré {audio}; lo salto.")
            continue
        print(f"Transcribiendo entrevista {i}: {audio.name} …")
        segmentos, info = modelo.transcribe(str(audio), language="es", vad_filter=True)
        lineas = [f"[{s.start:06.1f}s] {s.text.strip()}" for s in segmentos]
        salida = destino / f"entrevista_{i}.txt"
        salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        print(f"  → {salida} ({info.duration:.0f} s de audio, {len(lineas)} segmentos)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "entrevistas")
