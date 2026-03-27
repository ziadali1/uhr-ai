"""
Pipeline de anonimização de documentos médicos.

Fluxo:
  texto bruto → detecta entidades PII → substitui por tokens → texto anonimizado

Tokens usados:
  [PACIENTE]     → nomes de pessoas (paciente)
  [MÉDICO]       → nome do médico
  [CPF]          → CPF do paciente
  [CRM]          → CRM do médico
  [ENDEREÇO]     → endereços
  [TELEFONE]     → telefones
"""
import re
from models.document import ExtractedEntity

# Mapeamento categoria → token de substituição
_TOKEN_MAP = {
    "PersonName": "[PACIENTE]",
    "PersonId": "[CPF]",
    "MedicalRegistration": "[CRM]",
    "Address": "[ENDEREÇO]",
    "PhoneNumber": "[TELEFONE]",
}

# Categorias consideradas PII (não-médicas)
PII_CATEGORIES = set(_TOKEN_MAP.keys())


def anonymize(text: str, entities: list[ExtractedEntity]) -> str:
    """
    Substitui entidades PII no texto pelos tokens correspondentes.

    Estratégia: ordena entidades por posição de aparecimento no texto
    (maior → menor) para evitar deslocamento de índices ao substituir.
    """
    pii_entities = [e for e in entities if e.category in PII_CATEGORIES]

    # Substitui por texto — regex case-insensitive para pegar variações
    for entity in pii_entities:
        token = _TOKEN_MAP[entity.category]
        pattern = re.compile(re.escape(entity.text), re.IGNORECASE)
        text = pattern.sub(token, text)

    # Padrões fixos adicionais (CPF, CRM) por regex direta
    text = re.sub(r"\d{3}\.\d{3}\.\d{3}-\d{2}", "[CPF]", text)
    text = re.sub(r"\d{4,6}-[A-Z]{2}", "[CRM]", text)
    text = re.sub(r"\(\d{2}\)\s?\d{4,5}-\d{4}", "[TELEFONE]", text)

    return text


def run_pipeline(
    text: str,
    entities: list[ExtractedEntity],
) -> tuple[str, list[str]]:
    """
    Executa o pipeline completo de anonimização.

    Retorna:
        (texto_anonimizado, lista_de_substituicoes)
    """
    anonymized = anonymize(text, entities)

    substitutions = [
        f"{e.text} → {_TOKEN_MAP[e.category]}"
        for e in entities
        if e.category in PII_CATEGORIES
    ]

    return anonymized, substitutions
