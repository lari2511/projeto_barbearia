"""
Limite do município de São Paulo (capital) e região de um ponto, para o anúncio de vagas de diária.

Dados em app/dados/sao_paulo_capital.json:
- municipio: limite oficial do IBGE (código 3550308). É ele que decide se um ponto está na capital,
  então Guarulhos, Osasco, Santo André, São Bernardo etc. ficam de fora mesmo encostados na divisa.
- subprefeituras: as 32 subprefeituras do GeoSampa (Prefeitura de SP), cada uma com a região oficial
  em 5 (Centro, Leste, Norte, Oeste, Sul). Só dizem a região; não decidem se o ponto está na capital.

Os polígonos foram simplificados (~10 m). Um ponto dentro do município que caia numa fresta entre
subprefeituras recebe a região da subprefeitura mais próxima.

Só o fluxo de vagas de diária usa este módulo. Presença na barbearia, chamados, clientes e demais
regras de proximidade continuam com os próprios raios.
"""
import json
import os
import re
from functools import lru_cache
from typing import List, Optional, Tuple

REGIOES = ("Centro", "Zona Leste", "Zona Norte", "Zona Oeste", "Zona Sul")

# Nome das subprefeituras com acentuação (o GeoSampa entrega em maiúsculas, sem acento).
_NOMES = {
    "ARICANDUVA-FORMOSA-CARRAO": "Aricanduva/Formosa/Carrão",
    "BUTANTA": "Butantã",
    "CAMPO LIMPO": "Campo Limpo",
    "CAPELA DO SOCORRO": "Capela do Socorro",
    "CASA VERDE-LIMAO-CACHOEIRINHA": "Casa Verde/Limão/Cachoeirinha",
    "CIDADE ADEMAR": "Cidade Ademar",
    "CIDADE TIRADENTES": "Cidade Tiradentes",
    "ERMELINO MATARAZZO": "Ermelino Matarazzo",
    "FREGUESIA-BRASILANDIA": "Freguesia/Brasilândia",
    "GUAIANASES": "Guaianases",
    "IPIRANGA": "Ipiranga",
    "ITAIM PAULISTA": "Itaim Paulista",
    "ITAQUERA": "Itaquera",
    "JABAQUARA": "Jabaquara",
    "JACANA-TREMEMBE": "Jaçanã/Tremembé",
    "LAPA": "Lapa",
    "M BOI MIRIM": "M'Boi Mirim",
    "MOOCA": "Mooca",
    "PARELHEIROS": "Parelheiros",
    "PENHA": "Penha",
    "PERUS-ANHANGUERA": "Perus/Anhanguera",
    "PINHEIROS": "Pinheiros",
    "PIRITUBA-JARAGUA": "Pirituba/Jaraguá",
    "SANTANA-TUCURUVI": "Santana/Tucuruvi",
    "SANTO AMARO": "Santo Amaro",
    "SAO MATEUS": "São Mateus",
    "SAO MIGUEL": "São Miguel",
    "SAPOPEMBA": "Sapopemba",
    "SE": "Sé",
    "VILA MARIA-VILA GUILHERME": "Vila Maria/Vila Guilherme",
    "VILA MARIANA": "Vila Mariana",
    "VILA PRUDENTE": "Vila Prudente",
}

_ARQUIVO = os.path.join(os.path.dirname(__file__), "dados", "sao_paulo_capital.json")


def _caixa(poligonos) -> Tuple[float, float, float, float]:
    xs = [x for poligono in poligonos for x, _ in poligono[0]]
    ys = [y for poligono in poligonos for _, y in poligono[0]]
    return min(xs), min(ys), max(xs), max(ys)


@lru_cache(maxsize=1)
def _dados() -> dict:
    with open(_ARQUIVO, encoding="utf-8") as arquivo:
        bruto = json.load(arquivo)
    municipio = bruto["municipio"]["poligonos"]
    subprefeituras = [
        {
            "nome": _NOMES.get(sub["subprefeitura"], sub["subprefeitura"].title()),
            "regiao": sub["regiao"],
            "poligonos": sub["poligonos"],
            "caixa": _caixa(sub["poligonos"]),
        }
        for sub in bruto["subprefeituras"]
    ]
    return {"municipio": municipio, "caixa": _caixa(municipio), "subprefeituras": subprefeituras}


def _no_anel(x: float, y: float, anel: List[List[float]]) -> bool:
    """Ray casting (par/ímpar). Coordenadas em [longitude, latitude]."""
    dentro = False
    j = len(anel) - 1
    for i in range(len(anel)):
        xi, yi = anel[i]
        xj, yj = anel[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def _nos_poligonos(x: float, y: float, poligonos) -> bool:
    for poligono in poligonos:
        externo, *buracos = poligono
        if _no_anel(x, y, externo) and not any(_no_anel(x, y, buraco) for buraco in buracos):
            return True
    return False


def _na_caixa(x: float, y: float, caixa) -> bool:
    return caixa[0] <= x <= caixa[2] and caixa[1] <= y <= caixa[3]


def _coordenadas_validas(latitude, longitude) -> bool:
    try:
        return latitude is not None and longitude is not None and -90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180
    except (TypeError, ValueError):
        return False


def esta_na_capital(latitude: Optional[float], longitude: Optional[float]) -> bool:
    """True se o ponto está dentro do limite oficial (IBGE) do município de São Paulo."""
    if not _coordenadas_validas(latitude, longitude):
        return False
    x, y = float(longitude), float(latitude)
    dados = _dados()
    return _na_caixa(x, y, dados["caixa"]) and _nos_poligonos(x, y, dados["municipio"])


_CIDADE_UF = re.compile(r"^(?P<cidade>.+?)\s*[/-]\s*(?P<uf>[A-Za-z]{2})$")
_NUMERO = re.compile(r"^(n[º°o.]?\s*)?\d+[\w-]*$|^s/?n$", re.IGNORECASE)
_NUMERO_E_BAIRRO = re.compile(r"^(n[º°o.]?\s*)?\d+[\w-]*\s+-\s+(?P<bairro>.+)$", re.IGNORECASE)


def bairro_do_endereco(endereco: Optional[str]) -> Optional[str]:
    """
    Bairro escrito no endereço cadastrado da barbearia, ou None quando não dá para saber.

    O cadastro e o "endereço pelo CEP" gravam "Logradouro[, número], Bairro, Cidade/UF" (bairro do
    ViaCEP). A subprefeitura de localizar_na_capital NÃO é bairro: Artur Alvim, por exemplo, fica na
    subprefeitura da Penha. Sem bairro reconhecível (endereço por GPS, texto livre), devolve None e a
    tela mostra só a região, em vez de um bairro errado.
    """
    partes = [parte.strip() for parte in str(endereco or "").split(",") if parte.strip()]
    if len(partes) < 3:  # pelo menos logradouro, bairro e cidade/UF
        return None
    cidade_uf = _CIDADE_UF.match(partes[-1])
    if not cidade_uf:
        return None
    candidato = partes[-2]
    combinado = _NUMERO_E_BAIRRO.match(candidato)  # "123 - Artur Alvim"
    if combinado:
        candidato = combinado.group("bairro").strip()
    elif len(partes) == 3 and _NUMERO.match(partes[1]):
        return None  # "Rua X, 123, São Paulo/SP": sem bairro
    if not candidato or _NUMERO.match(candidato) or re.fullmatch(r"\d{5}-?\d{3}", candidato):
        return None
    if candidato.casefold() == cidade_uf.group("cidade").strip().casefold():
        return None
    return candidato


def localizar_na_capital(latitude: Optional[float], longitude: Optional[float]) -> Optional[dict]:
    """
    {"regiao": "Zona Sul", "subprefeitura": "Santo Amaro"} para um ponto na capital; None fora dela
    (ou sem coordenadas).
    """
    if not esta_na_capital(latitude, longitude):
        return None
    x, y = float(longitude), float(latitude)
    subprefeituras = _dados()["subprefeituras"]

    for sub in subprefeituras:
        if _na_caixa(x, y, sub["caixa"]) and _nos_poligonos(x, y, sub["poligonos"]):
            return {"regiao": sub["regiao"], "subprefeitura": sub["nome"]}

    # Fresta da simplificação ou divergência de traçado na divisa: subprefeitura mais próxima.
    def _distancia2(sub) -> float:
        return min(
            (px - x) ** 2 + (py - y) ** 2
            for poligono in sub["poligonos"]
            for px, py in poligono[0]
        )

    mais_proxima = min(subprefeituras, key=_distancia2)
    return {"regiao": mais_proxima["regiao"], "subprefeitura": mais_proxima["nome"]}
