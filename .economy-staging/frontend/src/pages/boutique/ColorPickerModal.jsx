/* eslint-disable react/prop-types */
import { Input, Modal, Tooltip, Typography } from 'antd'
import { useState } from 'react'

const { Search } = Input

const COLORS = [
  // Blancos y neutros cálidos
  { name: 'BLANCO', hex: '#FFFFFF' },
  { name: 'BLANCO NIEVE', hex: '#FFFAFA' },
  { name: 'BLANCO ÓPTICO', hex: '#F8F8FF' },
  { name: 'BLANCO NATURAL', hex: '#FDFBF7' },
  { name: 'BLANCO ROTO', hex: '#F5F5DC' },
  { name: 'BLANCO HUESO', hex: '#F9F6EE' },
  { name: 'BLANCO MARFIL', hex: '#FFFFF0' },
  { name: 'BLANCO PERLADO', hex: '#F8F6F0' },
  { name: 'MARFIL', hex: '#FFFFF0' },
  { name: 'MARFIL CLARO', hex: '#FAF0E6' },
  { name: 'MARFIL OSCURO', hex: '#EDE6D6' },
  { name: 'PERLA', hex: '#EAE0C8' },
  { name: 'PERLA CLARO', hex: '#F0EAD6' },
  { name: 'PERLA ROSADO', hex: '#E8D7C8' },
  { name: 'PERLA DORADO', hex: '#E6D8AD' },
  { name: 'CHAMPAGNE', hex: '#F7E7CE' },
  { name: 'CHAMPAGNE CLARO', hex: '#F3E5AB' },
  { name: 'CHAMPAGNE ROSADO', hex: '#F1DDCF' },
  { name: 'CHAMPAGNE DORADO', hex: '#ECD9A3' },
  { name: 'BEIGE', hex: '#F5F5DC' },
  { name: 'BEIGE CLARO', hex: '#F5EEDC' },
  { name: 'BEIGE ARENA', hex: '#D6C6A8' },
  { name: 'BEIGE ROSADO', hex: '#E8CFC1' },
  { name: 'NUDE', hex: '#E3BC9A' },
  { name: 'NUDE CLARO', hex: '#F2D6C2' },
  { name: 'NUDE ROSADO', hex: '#E6B8A2' },
  { name: 'NUDE OSCURO', hex: '#C79A7B' },
  { name: 'CREMA', hex: '#FFFDD0' },
  { name: 'CREMA CLARO', hex: '#FFF5E1' },
  { name: 'CREMA VAINILLA', hex: '#F3E5AB' },
  // Negros y grises
  { name: 'NEGRO', hex: '#000000' },
  { name: 'NEGRO MATE', hex: '#1C1C1C' },
  { name: 'NEGRO CARBÓN', hex: '#232323' },
  { name: 'NEGRO AZABACHE', hex: '#0A0A0A' },
  { name: 'NEGRO SATINADO', hex: '#111111' },
  { name: 'GRIS', hex: '#808080' },
  { name: 'GRIS CLARO', hex: '#D3D3D3' },
  { name: 'GRIS PLATA', hex: '#C0C0C0' },
  { name: 'GRIS PERLA', hex: '#BFC1C2' },
  { name: 'GRIS ACERO', hex: '#71797E' },
  { name: 'GRIS HUMO', hex: '#848884' },
  { name: 'GRIS OXFORD', hex: '#2F4F4F' },
  { name: 'PLATA', hex: '#C0C0C0' },
  { name: 'PLATEADO', hex: '#D8D8D8' },
  // Rojos
  { name: 'ROJO', hex: '#FF0000' },
  { name: 'ROJO INTENSO', hex: '#D00000' },
  { name: 'ROJO CEREZA', hex: '#DE3163' },
  { name: 'ROJO RUBÍ', hex: '#9B111E' },
  { name: 'ROJO VINO', hex: '#722F37' },
  { name: 'ROJO BURDEOS', hex: '#800020' },
  { name: 'ROJO GRANATE', hex: '#800000' },
  { name: 'ROJO ESCARLATA', hex: '#FF2400' },
  { name: 'ROJO CARMÍN', hex: '#960018' },
  { name: 'ROJO TOMATE', hex: '#FF6347' },
  { name: 'ROJO LADRILLO', hex: '#B22222' },
  { name: 'ROJO OSCURO', hex: '#8B0000' },
  // Rosados
  { name: 'ROSADO', hex: '#FFC0CB' },
  { name: 'ROSA', hex: '#FF69B4' },
  { name: 'ROSA CLARO', hex: '#FFB6C1' },
  { name: 'ROSA PASTEL', hex: '#FFD1DC' },
  { name: 'ROSA BEBÉ', hex: '#F4C2C2' },
  { name: 'ROSA PALO', hex: '#D8A7B1' },
  { name: 'ROSA VIEJO', hex: '#C08081' },
  { name: 'ROSA EMPOLVADO', hex: '#DCAE96' },
  { name: 'ROSA NUDE', hex: '#E6B7A9' },
  { name: 'ROSA CHICLE', hex: '#FF85C1' },
  { name: 'ROSA FUCSIA', hex: '#FF00FF' },
  { name: 'FUCSIA', hex: '#FF00FF' },
  { name: 'MAGENTA', hex: '#FF00FF' },
  { name: 'ROSA MEXICANO', hex: '#E4007C' },
  { name: 'ROSA CORAL', hex: '#F88379' },
  { name: 'ROSA SALMÓN', hex: '#FA8072' },
  // Dorados y amarillos
  { name: 'DORADO', hex: '#FFD700' },
  { name: 'ORO', hex: '#FFD700' },
  { name: 'ORO CLARO', hex: '#F9E076' },
  { name: 'ORO VIEJO', hex: '#CFB53B' },
  { name: 'ORO ROSA', hex: '#B76E79' },
  { name: 'DORADO METÁLICO', hex: '#D4AF37' },
  { name: 'DORADO CHAMPAGNE', hex: '#E6C875' },
  { name: 'DORADO OSCURO', hex: '#B8860B' },
  { name: 'MOSTAZA', hex: '#FFDB58' },
  { name: 'AMARILLO', hex: '#FFFF00' },
  { name: 'AMARILLO CLARO', hex: '#FFFFE0' },
  { name: 'AMARILLO PASTEL', hex: '#FDFD96' },
  { name: 'AMARILLO CANARIO', hex: '#FFEF00' },
  { name: 'AMARILLO MAÍZ', hex: '#FBEC5D' },
  { name: 'AMARILLO ORO', hex: '#FFBF00' },
  { name: 'AMARILLO MOSTAZA', hex: '#E1AD01' },
  { name: 'AMARILLO LIMÓN', hex: '#FFF44F' },
  // Naranjas
  { name: 'NARANJA', hex: '#FFA500' },
  { name: 'NARANJA CLARO', hex: '#FFB347' },
  { name: 'NARANJA PASTEL', hex: '#FFD1A4' },
  { name: 'NARANJA QUEMADO', hex: '#CC5500' },
  { name: 'NARANJA CORAL', hex: '#FF7F50' },
  { name: 'DURAZNO', hex: '#FFE5B4' },
  { name: 'DURAZNO CLARO', hex: '#FFDAB9' },
  { name: 'DURAZNO ROSADO', hex: '#FAD6BF' },
  { name: 'SALMÓN', hex: '#FA8072' },
  { name: 'SALMÓN CLARO', hex: '#FFA07A' },
  { name: 'COBRE', hex: '#B87333' },
  { name: 'COBRE ROSADO', hex: '#C47F6A' },
  { name: 'TERRACOTA', hex: '#E2725B' },
  { name: 'LADRILLO', hex: '#B22222' },
  // Azules
  { name: 'AZUL', hex: '#0000FF' },
  { name: 'AZUL MARINO', hex: '#000080' },
  { name: 'AZUL NOCHE', hex: '#191970' },
  { name: 'AZUL REY', hex: '#4169E1' },
  { name: 'AZUL FRANCIA', hex: '#318CE7' },
  { name: 'AZUL ELÉCTRICO', hex: '#007FFF' },
  { name: 'AZUL COBALTO', hex: '#0047AB' },
  { name: 'AZUL ZAFIRO', hex: '#0F52BA' },
  { name: 'AZUL CELESTE', hex: '#87CEEB' },
  { name: 'AZUL CIELO', hex: '#87CEFA' },
  { name: 'AZUL BEBÉ', hex: '#89CFF0' },
  { name: 'AZUL PASTEL', hex: '#AEC6CF' },
  { name: 'AZUL TURQUESA', hex: '#40E0D0' },
  { name: 'AZUL AGUA', hex: '#00FFFF' },
  { name: 'AZUL PETRÓLEO', hex: '#005F6A' },
  { name: 'AZUL ACERO', hex: '#4682B4' },
  { name: 'AZUL GRISÁCEO', hex: '#6699CC' },
  { name: 'AZUL LAVANDA', hex: '#CCCCFF' },
  // Verdes
  { name: 'VERDE', hex: '#008000' },
  { name: 'VERDE CLARO', hex: '#90EE90' },
  { name: 'VERDE PASTEL', hex: '#77DD77' },
  { name: 'VERDE MENTA', hex: '#98FF98' },
  { name: 'VERDE AGUA', hex: '#00FFCC' },
  { name: 'VERDE ESMERALDA', hex: '#50C878' },
  { name: 'VERDE BOTELLA', hex: '#006A4E' },
  { name: 'VERDE OLIVA', hex: '#808000' },
  { name: 'VERDE MILITAR', hex: '#4B5320' },
  { name: 'VERDE MUSGO', hex: '#8A9A5B' },
  { name: 'VERDE SALVIA', hex: '#9CAF88' },
  { name: 'VERDE JADE', hex: '#00A86B' },
  { name: 'VERDE TURQUESA', hex: '#30D5C8' },
  { name: 'VERDE BOSQUE', hex: '#228B22' },
  { name: 'VERDE OSCURO', hex: '#006400' },
  { name: 'VERDE LIMA', hex: '#32CD32' },
  // Morados y violetas
  { name: 'MORADO', hex: '#800080' },
  { name: 'PÚRPURA', hex: '#800080' },
  { name: 'VIOLETA', hex: '#8A2BE2' },
  { name: 'LILA', hex: '#C8A2C8' },
  { name: 'LILA CLARO', hex: '#DCD0FF' },
  { name: 'LILA PASTEL', hex: '#CBAACB' },
  { name: 'LAVANDA', hex: '#E6E6FA' },
  { name: 'LAVANDA CLARO', hex: '#F3E8FF' },
  { name: 'MALVA', hex: '#B784A7' },
  { name: 'MALVA CLARO', hex: '#D8BFD8' },
  { name: 'MORADO OSCURO', hex: '#4B0082' },
  { name: 'MORADO UVA', hex: '#6F2DA8' },
  { name: 'BERENJENA', hex: '#614051' },
  { name: 'AMATISTA', hex: '#9966CC' },
  // Cafés y marrones
  { name: 'CAFÉ', hex: '#6F4E37' },
  { name: 'MARRÓN', hex: '#8B4513' },
  { name: 'CHOCOLATE', hex: '#7B3F00' },
  { name: 'CAFÉ OSCURO', hex: '#4B2E2B' },
  { name: 'CAFÉ CLARO', hex: '#A67B5B' },
  { name: 'CAMEL', hex: '#C19A6B' },
  { name: 'CARAMELO', hex: '#C68E17' },
  { name: 'MIEL', hex: '#D8A031' },
  { name: 'CANELA', hex: '#D2691E' },
  { name: 'AVELLANA', hex: '#A0522D' },
  { name: 'TABACO', hex: '#71543E' },
  { name: 'BRONCE', hex: '#CD7F32' },
  // Corales y especiales
  { name: 'CORAL', hex: '#FF7F50' },
  { name: 'CORAL CLARO', hex: '#F88379' },
  { name: 'CORAL ROSADO', hex: '#F88379' },
  { name: 'CORAL INTENSO', hex: '#FF4040' },
  { name: 'MELÓN', hex: '#FDBCB4' },
  { name: 'SANDÍA', hex: '#FC6C85' },
  // Vinotintos y ciruelas
  { name: 'VINOTINTO', hex: '#722F37' },
  { name: 'BORGOÑA', hex: '#800020' },
  { name: 'MERLOT', hex: '#73343A' },
  { name: 'CIRUELA', hex: '#8E4585' },
  { name: 'FRAMBUESA', hex: '#E30B5D' },
  { name: 'CEREZA OSCURO', hex: '#990F02' },
  // Turquesas y aquas
  { name: 'TURQUESA', hex: '#40E0D0' },
  { name: 'AQUA', hex: '#00FFFF' },
  { name: 'AGUA MARINA', hex: '#7FFFD4' },
  { name: 'MENTA AGUA', hex: '#B2FFFF' },
  { name: 'CELESTE PASTEL', hex: '#B2FFFF' },
  { name: 'PETRÓLEO', hex: '#005F6A' },
  { name: 'TEAL', hex: '#008080' },
  // Metálicos
  { name: 'METÁLICO ORO', hex: '#D4AF37' },
  { name: 'METÁLICO PLATA', hex: '#C0C0C0' },
  { name: 'METÁLICO COBRE', hex: '#B87333' },
  { name: 'METÁLICO BRONCE', hex: '#CD7F32' },
  { name: 'METÁLICO ROSA', hex: '#B76E79' },
  { name: 'METÁLICO CHAMPAGNE', hex: '#E6C875' },
  // Especiales e iridiscentes
  { name: 'TRANSPARENTE', hex: '#F8FFFF' },
  { name: 'CRISTAL', hex: '#F8FFFF' },
  { name: 'ESCARCHA PLATA', hex: '#E5E4E2' },
  { name: 'ESCARCHA DORADA', hex: '#F5D76E' },
  { name: 'TORNASOL', hex: '#D6CADD' },
  { name: 'IRIDISCENTE', hex: '#E7DFF2' },
]

export const COLOR_MAP = Object.fromEntries(COLORS.map((c) => [c.name, c.hex]))

export function ColorPickerModal({ open, onSelect, onCancel }) {
  const [search, setSearch] = useState('')

  const filtered = COLORS.filter((c) =>
    c.name.toUpperCase().includes(search.trim().toUpperCase())
  )

  return (
    <Modal
      title="Seleccionar Color"
      open={open}
      onCancel={() => {
        setSearch('')
        onCancel()
      }}
      footer={null}
      width={780}
      maskClosable={false}
      styles={{ body: { padding: '16px 20px' } }}
    >
      <Search
        placeholder="Buscar color... (ej. ROSA, AZUL MARINO)"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        allowClear
        style={{ marginBottom: 16 }}
      />

      {filtered.length === 0 ? (
        <Typography.Text type="secondary">No se encontró ningún color con ese nombre.</Typography.Text>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(80px, 1fr))',
            gap: 10,
            maxHeight: 480,
            overflowY: 'auto',
            paddingRight: 4,
          }}
        >
          {filtered.map((color) => (
            <Tooltip key={color.name} title={color.name} placement="top">
              <div
                onClick={() => {
                  setSearch('')
                  onSelect(color.name)
                }}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 5,
                  cursor: 'pointer',
                  padding: '8px 4px',
                  borderRadius: 10,
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(0,0,0,0.06)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <div
                  style={{
                    width: 52,
                    height: 52,
                    borderRadius: 10,
                    background: color.hex,
                    border: '2px solid rgba(0,0,0,0.12)',
                    boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
                    flexShrink: 0,
                  }}
                />
                <span
                  style={{
                    fontSize: 10,
                    lineHeight: 1.2,
                    textAlign: 'center',
                    color: '#444',
                    maxWidth: 76,
                    wordBreak: 'break-word',
                  }}
                >
                  {color.name}
                </span>
              </div>
            </Tooltip>
          ))}
        </div>
      )}
    </Modal>
  )
}
