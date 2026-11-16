"""Identity validation shared by collaborator contracts and temporary credentials."""

import re
import unicodedata


def clean_user_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    if any(unicodedata.category(char) in {"Cf", "Cs", "Co"} for char in value):
        raise ValueError("No se permiten caracteres invisibles o de control.")
    if any(unicodedata.category(char) == "Cc" and not char.isspace() for char in value):
        raise ValueError("No se permiten caracteres de control.")
    return " ".join(value.split())


def meaningful_user_text(value: str) -> str:
    value = clean_user_text(value)
    if not any(char.isalnum() for char in value):
        raise ValueError("Debe ingresar contenido válido; los espacios no cuentan.")
    return value


def user_name(value: str) -> str:
    value = meaningful_user_text(value)
    if not all(char.isalpha() or unicodedata.category(char).startswith("M") or char == " " for char in value):
        raise ValueError("Solo se permiten letras y espacios entre nombres o apellidos.")
    if any(not word[0].isalpha() for word in value.split(" ")):
        raise ValueError("Cada nombre o apellido debe comenzar con una letra.")
    return value.upper()


def collaborator_ci(value: str) -> str:
    # Identity is text: never coerce to int or discard leading zeroes/invalid input.
    if not re.fullmatch(r"[0-9]{7,30}", value):
        raise ValueError("El CI debe contener entre 7 y 30 dígitos, sin letras ni espacios.")
    return value


def generate_temporary_password(user) -> str:
    names = user_name(user.nombres)
    surname = user_name(user.apellido_paterno)
    return names[0] + surname[0] + collaborator_ci(user.ci)
