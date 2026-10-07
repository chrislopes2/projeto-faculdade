"""Funções auxiliares compartilhadas."""
import re
import shutil
import subprocess
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
    print(f"  baixando {url}", flush=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    if shutil.which("curl"):
        # O FTP do PDET derruba conexões longas (arquivos da RAIS têm GB); o curl
        # tenta de novo e continua de onde parou (-C -).
        for _ in range(5):
            r = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--retry", "5",
                                "--retry-all-errors", "--retry-delay", "15", "-C", "-",
                                "-o", str(tmp), url])
            if r.returncode == 0:
                break
            if r.returncode == 78:  # arquivo não existe no servidor (ex.: mês ainda não publicado)
                tmp.unlink(missing_ok=True)
                raise FileNotFoundError(url)
        else:
            raise RuntimeError(f"falha ao baixar {url} (curl saiu com {r.returncode})")
    else:
        with urllib.request.urlopen(url, timeout=600) as resp, open(tmp, "wb") as f:
            shutil.copyfileobj(resp, f)
    tmp.rename(destino)
    return destino


def extrair_7z(arquivo: Path, pasta: Path) -> list[Path]:
    """Extrai um .7z. Usa o 7z do sistema quando existe: os arquivos da RAIS usam
    compressão que o py7zr não lê ("invalid header data")."""
    pasta.mkdir(parents=True, exist_ok=True)
    antes = set(pasta.iterdir())
    if shutil.which("7z"):
        subprocess.run(["7z", "x", "-y", f"-o{pasta}", str(arquivo)], check=True, stdout=subprocess.DEVNULL)
    else:
        import py7zr

        with py7zr.SevenZipFile(arquivo, "r") as z:
            z.extractall(pasta)
    return sorted(p for p in set(pasta.iterdir()) - antes if p.is_file())
