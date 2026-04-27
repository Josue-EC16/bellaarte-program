export const FORM_VALIDATE_MESSAGES = {
  default: '${label} no es válido.',
  required: 'Debe completar ${label}.',
  enum: '${label} no es válido.',
  whitespace: '${label} no puede estar vacío.',
  types: {
    email: 'Debe ingresar un correo electrónico válido en ${label}.',
    number: 'Debe ingresar un número válido en ${label}.',
    integer: 'Debe ingresar un número entero válido en ${label}.',
    boolean: '${label} no es válido.',
    array: '${label} no es válido.',
    object: '${label} no es válido.',
  },
  string: {
    len: '${label} debe tener exactamente ${len} caracteres.',
    min: '${label} debe tener al menos ${min} caracteres.',
    max: '${label} no puede superar ${max} caracteres.',
    range: '${label} debe tener entre ${min} y ${max} caracteres.',
  },
  number: {
    len: '${label} no es válido.',
    min: '${label} debe ser mayor o igual a ${min}.',
    max: '${label} debe ser menor o igual a ${max}.',
    range: '${label} debe estar entre ${min} y ${max}.',
  },
  array: {
    len: '${label} no es válido.',
    min: 'Debe seleccionar al menos ${min} opciones en ${label}.',
    max: 'Debe seleccionar como máximo ${max} opciones en ${label}.',
    range: 'Debe seleccionar entre ${min} y ${max} opciones en ${label}.',
  },
  pattern: {
    mismatch: '${label} no tiene un formato válido.',
  },
  date: {
    format: '${label} no tiene un formato de fecha válido.',
    parse: '${label} no tiene un formato de fecha válido.',
    invalid: '${label} no es una fecha válida.',
  },
}

export const FORM_COMMON_PROPS = {
  layout: 'vertical',
  scrollToFirstError: { behavior: 'smooth', block: 'center' },
  validateTrigger: ['onBlur', 'onSubmit'],
}

export const FORM_SUBMIT_PROPS = {
  type: 'primary',
  htmlType: 'submit',
  size: 'large',
}

export const FORM_DRAWER_SUBMIT_PROPS = {
  ...FORM_SUBMIT_PROPS,
  block: true,
}
