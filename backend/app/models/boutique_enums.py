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


class EstadoFleteEnum(str, Enum):
    DISPONIBLE = "disponible"
    EN_FLETE = "en_flete"
    EN_REVISION = "en_revision"
    AGOTADO = "agotado"
    PASADO_PARA_VENTA = "pasado_para_venta"
    RETIRADO = "retirado"


class MotivoDescFleteEnum(str, Enum):
    REBAJA = "rebaja"
    PROMOCION = "promocion"
    BONIFICACION = "bonificacion"
    ADMINISTRATIVO = "administrativo"


class EstadoSalidaFleteEnum(str, Enum):
    RESERVADO = "reservado"
    EN_FLETE = "en_flete"
    DEVUELTO = "devuelto"
    DEVUELTO_CON_OBSERVACION = "devuelto_con_observacion"
    DEVUELTO_CON_ARREGLO = "devuelto_con_arreglo"
    ANULADO = "anulado"


class EstadoFleteEntregaEnum(str, Enum):
    BUENO = "bueno"
    REGULAR = "regular"
    CON_OBSERVACION = "con_observacion"


class EstadoFleteDevolucionEnum(str, Enum):
    BUENO = "bueno"
    REGULAR = "regular"
    DANADO = "dañado"
    INCOMPLETO = "incompleto"


class EstadoComprobanteEnum(str, Enum):
    EMITIDO = "emitido"
    ANULADO = "anulado"


class PrioridadNotificacionEnum(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class TipoAccionAuditoriaEnum(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    CANCELACION = "cancelacion"
    ANULACION = "anulacion"
    CAMBIO_ESTADO = "cambio_estado"
    OTRO = "otro"


class TipoEgresoEnum(str, Enum):
    ALMUERZO = "almuerzo"
    MERIENDA = "merienda"
    ALQUILER = "alquiler"
    ALIMENTOS_EN_GENERAL = "alimentos_en_general"
    COSTURA = "costura"
    DECORADO = "decorado"
    DEVOLUCION = "devolucion"
    INVENTARIO_BOUTIQUE = "inventario_boutique"
    INVENTARIO_TALLER = "inventario_taller"
    MANTENIMIENTO = "mantenimiento"
    MARKETING = "marketing"
    SERVICIO_BASICO = "servicio_basico"
    SUELDO = "sueldo"
    TECNOLOGIA = "tecnologia"
    OTRO = "otro"


class EstadoEgresoEnum(str, Enum):
    REGISTRADO = "registrado"
    ANULADO = "anulado"


class EstadoCorteCajaEnum(str, Enum):
    ABIERTO = "abierto"
    CERRADO = "cerrado"
    CERRADO_OBSERVADO = "cerrado_observado"


class TipoBackupBdEnum(str, Enum):
    LOGICO_COMPLETO = "LOGICO_COMPLETO"
    SEMANAL = "SEMANAL"
    MANUAL = "MANUAL"


class EstadoBackupBdEnum(str, Enum):
    EN_PROCESO = "EN_PROCESO"
    EXITOSO = "EXITOSO"
    FALLIDO = "FALLIDO"


class TipoPedidoEnum(str, Enum):
    VESTIDO = "vestido"
    VELO = "velo"
    COLA = "cola"
    MANGA = "manga"
    BOUQUET = "bouquet"
    OTRO = "otro"


class MotivoDescuentoPedidoEnum(str, Enum):
    REBAJA = "rebaja"
    PROMOCION = "promocion"
    BONIFICACION = "bonificacion"
    ADMINISTRATIVO = "administrativo"


class EstadoPedidoGeneralEnum(str, Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"


class EstadoPagoPedidoEnum(str, Enum):
    REGISTRADO = "registrado"
    ANULADO = "anulado"


class PruebaEstadoPedidoEnum(str, Enum):
    LISTO = "listo"
    COSTURERO_TALLER = "costurero_taller"
    DECORACION = "decoracion"
    COSTURERO_EXTERNO = "costurero_externo"
    OTRO = "otro"
