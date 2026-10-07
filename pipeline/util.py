"""Funções auxiliares compartilhadas."""
import re
import shutil
import unicodedata
import urllib.request
from pathlib import Path


def sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c))


def nome_coluna(texto: str) -> str:
    """'Competência Concessão' -> 'competencia_concessao'."""
    t = sem_acento(texto).lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def baixar(url: str, destino: Path, forcar: bool = False) -> Path:
    """Baixa um arquivo (http ou ftp) se ainda não existir no disco."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0 and not forcar:
        print(f"  já existe: {destino.name}")
        return destino
    print(f"  baixando {url}")
    tmp = destino.with_suffix(destino.suffix + ".part")
    with urllib.request.urlopen(url, timeout=600) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f)
    tmp.rename(destino)
    return destino


def extrair_7z(arquivo: Path, pasta: Path) -> list[Path]:
    import py7zr

    pasta.mkdir(parents=True, exist_ok=True)
    with py7zr.SevenZipFile(arquivo, "r") as z:
        nomes = z.getnames()
        z.extractall(pasta)
    return [pasta / n for n in nomes]
