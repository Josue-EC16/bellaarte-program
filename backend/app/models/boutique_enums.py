from enum import Enum


class TamanoEnum(str, Enum):
    PEQUENO = "PEQUEÑO"
    MEDIANO = "MEDIANO"
    GRANDE = "GRANDE"


class TipoVestidoEnum(str, Enum):
    VESTIDO_DE_NOVIA = "VESTIDO DE NOVIA"
    VESTIDO_DE_CIVIL = "VESTIDO DE CIVIL"
    VESTIDO_DE_15_ANOS = "VESTIDO DE 15 AÑOS"
    VESTIDO_DE_FIESTA_O_EVENTO = "VESTIDO DE FIESTA O EVENTO"
    VESTIDO_DE_NINA = "VESTIDO DE NIÑA"
    DAMAS = "DAMAS"
    OTRO = "OTRO"


class CopaTallaVestidoBoutiqueEnum(str, Enum):
    COPA_AA = "COPA AA"
    COPA_A = "COPA A"
    COPA_B = "COPA B"
    COPA_C = "COPA C"
    COPA_D = "COPA D"
    COPA_DD = "COPA DD"
    COPA_E = "COPA E"
    COPA_F = "COPA F"
    COPA_G = "COPA G"


class TallaVestidoBoutiqueEnum(str, Enum):
    TALLA_XXS = "TALLA XXS"
    TALLA_XS = "TALLA XS"
    TALLA_S = "TALLA S"
    TALLA_M = "TALLA M"
    TALLA_L = "TALLA L"
    TALLA_XL = "TALLA XL"
    TALLA_XXL = "TALLA XXL"
    TALLA_XXXL = "TALLA XXXL"
