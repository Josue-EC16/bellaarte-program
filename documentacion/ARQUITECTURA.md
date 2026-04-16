# 🏛️ ESPECIFICACIÓN DE ARQUITECTURA DE SOFTWARE: bellaarte-program

**Versión:** 1.0 (Abril 2026)  
**Autor:** Marcelo Josue Escobar Chipana [cite: 2]  
**Proyecto:** Sistema de Gestión Integral para BellaArte Boutique [cite: 1]

---

## 1. VISIÓN GENERAL

El sistema está diseñado para digitalizar y optimizar el flujo de trabajo de alta costura personalizada[cite: 1]. Su objetivo primordial es transitar de un modelo de gestión basado en Excel y registros manuales hacia una plataforma centralizada que integra **Ciencia de Datos** para la toma de decisiones estratégicas[cite: 3, 4].

## 2. PATRÓN ARQUITECTÓNICO: CLIENTE-SERVIDOR DESACOPLADO

Se ha implementado una arquitectura de **desacoplamiento total**, separando la interfaz de usuario de la lógica de negocio[cite: 1].

- **Frontend (Single Page Application - SPA):** Construido con **React 19** y **Vite 6** para garantizar una experiencia de usuario fluida y reactiva en la boutique[cite: 1, 2].
- **Backend (RESTful API):** Construido con **FastAPI** y **Python 3.14**, aprovechando la programación asíncrona para manejar procesos concurrentes de taller y ventas[cite: 1, 2].
- **Comunicación:** Intercambio de datos mediante **JSON Web Tokens (JWT)** para asegurar sesiones persistentes y seguras entre ambas capas[cite: 1].

---

## 3. STACK TECNOLÓGICO Y JUSTIFICACIÓN

| Capa             | Tecnología        | Justificación de Ingeniería                                                                                         |
| :--------------- | :---------------- | :------------------------------------------------------------------------------------------------------------------ |
| **Interfaz**     | React 19 + Vite 6 | Alto rendimiento y facilidad para crear componentes complejos como la ficha de medidas.     |
| **Cerebro**      | FastAPI (Python)  | Nativo para integrar modelos de **Machine Learning** y validación estricta con Pydantic. |
| **Persistencia** | PostgreSQL 17     | Manejo robusto de relaciones complejas entre clientas, pedidos y las 5 fases de pruebas.    |
| **ORM**          | SQLAlchemy 2.0    | Abstracción de base de datos con tipado fuerte, facilitando la mantenibilidad a largo plazo.   |
| **Seguridad**    | Casbin + Bcrypt   | Implementación de **RBAC** para separar funciones de Boutique, Taller y Administración.     |

---

## 4. MODELO DE DATOS (PERSISTENCIA)

La base de datos se organiza en bloques lógicos para garantizar la integridad referencial y facilitar la auditoría:

- **Seguridad:** Gestión de roles y cuentas.
- **Comercial:** Registro de clientas, pedidos personalizados y seguimiento de las **4 pruebas obligatorias**.
- **Inventario Dual:** Separación entre productos terminados (Boutique) e insumos (Taller - Telas, Guipures, Pedrería).
- **Finanzas:** Centralización de ingresos y egresos para cálculo de rentabilidad real.

---

## 5. CAPACIDADES ANALÍTICAS (MÓDULOS DE IA/ML)

A diferencia de un CRUD tradicional, esta arquitectura soporta tres pilares de inteligencia de negocios[cite: 4]:

1.  **Índice de Complejidad Comercial:** Modelo predictivo que estima el precio sugerido y tiempo de confección basándose en las características del diseño (telas, pedrería, corte)[cite: 4].
2.  **Predicción de Saturación de Agenda:** Algoritmo analítico que evalúa la capacidad máxima del taller frente a la demanda de pruebas programadas[cite: 4].
3.  **Automatización por Eventos:** Motor de reglas que dispara acciones (notificaciones, alertas de stock mínimo) basadas en cambios de estado del sistema[cite: 4].

---

## 6. SEGURIDAD Y CONTROL DE ACCESO

El sistema implementa una arquitectura **Zero-Trust** y auditoría completa[cite: 1]:

- **Auditoría (Logs):** Cada acción sobre registros críticos (pedidos, pagos, stock) se registra en una bitácora detallada indicando quién, cuándo y qué cambió[cite: 3].
- **RBAC:** El personal de taller solo visualiza fichas técnicas, mientras que el personal de ventas gestiona cobros y medidas[cite: 1, 3].
- **Normalización:** Todas las entradas críticas se procesan en **MAYÚSCULAS** para evitar inconsistencias en las búsquedas[cite: 1, 3].

---

## 7. ESTRATEGIA DE DESPLIEGUE Y ESCALABILIDAD

Diseñado para una vida útil mínima de 6 años, el sistema permite[cite: 1]:

- **Contenerización:** Estructura modular lista para ser desplegada mediante **Docker**, asegurando portabilidad absoluta entre entornos de desarrollo y producción[cite: 1, 2].
- **Despliegue Independiente:** Posibilidad de alojar el frontend en servicios como Vercel y el backend en servidores dedicados para optimizar costos[cite: 1].

**Nota de Mantenimiento:** La base de datos se evoluciona únicamente mediante migraciones Alembic. 
Cualquier cambio en `backend/app/models/` debe acompañarse de su migración correspondiente y aplicarse con `alembic upgrade head`.
----------------