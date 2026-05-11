from enum import Enum


class TipoVestidoEnum(str, Enum):
    VESTIDO_DE_NOVIA = "vestido_de_novia"
    VESTIDO_DE_CIVIL = "vestido_de_civil"
    VESTIDO_DE_15_ANOS = "vestido_de_15_años"
    VESTIDO_DE_FIESTA_O_EVENTO = "vestido_de_fiesta_o_evento"
    VESTIDO_DE_NINA = "vestido_de_niña"
    DAMAS = "damas"
    OTRO = "otro"


class CopaTallaVestidoBoutiqueEnum(str, Enum):
    COPA_AA = "copa_aa"
    COPA_A = "copa_a"
    COPA_B = "copa_b"
    COPA_C = "copa_c"
    COPA_D = "copa_d"
    COPA_DD = "copa_dd"
    COPA_E = "copa_e"
    COPA_F = "copa_f"
    COPA_G = "copa_g"


class TallaVestidoBoutiqueEnum(str, Enum):
    TALLA_XXS = "talla_xxs"
    TALLA_XS = "talla_xs"
    TALLA_S = "talla_s"
    TALLA_M = "talla_m"
    TALLA_L = "talla_l"
    TALLA_XL = "talla_xl"
    TALLA_XXL = "talla_xxl"
    TALLA_XXXL = "talla_xxxl"


class MetodoPagoEnum(str, Enum):
    EFECTIVO = "efectivo"
    QR = "qr"
    TRANSACCION = "transaccion"
    TARJETA = "tarjeta"
    TICKET_O_VALE = "ticket_o_vale"


class MotivoDescVentaBoutiqueEnum(str, Enum):
    REBAJA = "rebaja"
    PROMOCION = "promocion"
    BONIFICACION = "bonificacion"
    ADMINISTRATIVO = "administrativo"


class EstadoVentaBoutiqueEnum(str, Enum):
    ACTIVA = "activa"
    CANCELADA = "cancelada"
    ANULADA = "anulada"


class MotivoEntradaItemEnum(str, Enum):
    ENTRADA_STOCK = "entrada_stock"
    PRODUCCION_INTERNA = "produccion_interna"
    DEVOLUCION = "devolucion"
    AJUSTE_POSITIVO = "ajuste_positivo"
    REGISTRO_INICIAL = "registro_inicial"
    OTRO = "otro"


class UnidadMedidaEnum(str, Enum):
    METRO = "metro"
    CENTIMETRO = "centimetro"
    ROLLO = "rollo"
    CAJA = "caja"
    KILOGRAMO = "kilogramo"
    GRAMO = "gramo"
    YARDA = "yarda"
    RANDA = "randa"
    UNIDAD = "unidad"
    OTRO = "otro"


class MotivoEntradaTallerEnum(str, Enum):
    ENTRADA_STOCK = "entrada_stock"
    DEVOLUCION = "devolucion"
    AJUSTE_POSITIVO = "ajuste_positivo"
    REGISTRO_INICIAL = "registro_inicial"
    OTRO = "otro"
