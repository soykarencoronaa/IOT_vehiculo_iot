# app/services/iot_service.py

from app.database import obtener_conexion


def ejecutar_sp(nombre, parametros=(), escritura=False):
    conexion = obtener_conexion()
    cursor = None

    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.callproc(nombre, parametros)

        resultados = []

        for conjunto in cursor.stored_results():
            resultados.extend(conjunto.fetchall())

        if escritura:
            conexion.commit()

        return resultados

    except Exception:
        if escritura:
            conexion.rollback()
        raise

    finally:
        if cursor is not None:
            cursor.close()
        conexion.close()


# VEHICULOS


def obtener_vehiculos():
    return ejecutar_sp("sp_obtener_vehiculos")


def obtener_vehiculo(id_vehiculo):
    filas = ejecutar_sp(
        "sp_obtener_vehiculo",
        (id_vehiculo,),
    )
    return filas[0] if filas else None


def crear_vehiculo(datos):
    filas = ejecutar_sp(
        "sp_crear_vehiculo",
        (
            datos.nombre,
            datos.modelo,
            datos.descripcion,
            datos.microcontrolador,
        ),
        escritura=True,
    )
    return filas[0] if filas else {}


def actualizar_vehiculo(id_vehiculo, datos):
    ejecutar_sp(
        "sp_actualizar_vehiculo",
        (
            id_vehiculo,
            datos.nombre,
            datos.modelo,
            datos.descripcion,
            datos.microcontrolador,
            datos.activo,
        ),
        escritura=True,
    )
    return {"id_vehiculo": id_vehiculo}


# COMANDOS


def obtener_comandos_vehiculo(id_vehiculo):
    return ejecutar_sp(
        "sp_obtener_comandos_vehiculo",
        (id_vehiculo,),
    )


def crear_comando(datos):
    filas = ejecutar_sp(
        "sp_crear_comando",
        (
            datos.id_vehiculo,
            datos.nombre,
            datos.codigo,
            datos.descripcion,
        ),
        escritura=True,
    )
    return filas[0] if filas else {}


def actualizar_comando(id_comando, datos):
    ejecutar_sp(
        "sp_actualizar_comando",
        (
            id_comando,
            datos.nombre,
            datos.codigo,
            datos.descripcion,
            datos.activo,
        ),
        escritura=True,
    )
    return {"id_comando": id_comando}


def eliminar_comando(id_comando):
    ejecutar_sp(
        "sp_eliminar_comando",
        (id_comando,),
        escritura=True,
    )
    return {"id_comando": id_comando}


# HISTORIAL


def obtener_historial(id_vehiculo):
    return ejecutar_sp(
        "sp_obtener_historial",
        (id_vehiculo,),
    )


def registrar_historial(datos):
    ejecutar_sp(
        "sp_registrar_historial",
        (
            datos.id_vehiculo,
            datos.id_comando,
            datos.origen,
        ),
        escritura=True,
    )

    return {
        "id_vehiculo": datos.id_vehiculo,
        "id_comando": datos.id_comando,
        "origen": datos.origen,
    }


# =========================
# DEMOS
# =========================


def crear_demo(datos):
    filas = ejecutar_sp(
        "sp_crear_demo",
        (datos.id_vehiculo, datos.nombre, datos.descripcion),
        escritura=True,
    )
    return filas[0] if filas else {}


def actualizar_demo(id_demo, datos):
    ejecutar_sp(
        "sp_actualizar_demo",
        (id_demo, datos.nombre, datos.descripcion, datos.activo),
        escritura=True,
    )
    return {"id_demo": id_demo}


def eliminar_demo(id_demo):
    ejecutar_sp("sp_eliminar_demo", (id_demo,), escritura=True)
    return {"id_demo": id_demo}


def obtener_demos(id_vehiculo):
    return ejecutar_sp("sp_obtener_demos", (id_vehiculo,))


# =========================
# MOVIMIENTOS DE DEMOS
# =========================


def agregar_movimiento_demo(id_demo, datos):
    ejecutar_sp(
        "sp_agregar_movimiento_demo",
        (id_demo, datos.id_comando, datos.orden, datos.duracion_ms, datos.pausa_ms),
        escritura=True,
    )
    return {"id_demo": id_demo}


def actualizar_movimiento_demo(id_demo_movimiento, datos):
    ejecutar_sp(
        "sp_actualizar_movimiento_demo",
        (
            id_demo_movimiento,
            datos.id_comando,
            datos.orden,
            datos.duracion_ms,
            datos.pausa_ms,
        ),
        escritura=True,
    )
    return {"id_demo_movimiento": id_demo_movimiento}


def eliminar_movimiento_demo(id_demo_movimiento):
    ejecutar_sp("sp_eliminar_movimiento_demo", (id_demo_movimiento,), escritura=True)
    return {"id_demo_movimiento": id_demo_movimiento}


def obtener_movimientos_demo(id_demo):
    return ejecutar_sp("sp_obtener_movimientos_demo", (id_demo,))


# =========================
# ESTADO DEL VEHÍCULO
# =========================


def obtener_estado(id_vehiculo):
    filas = ejecutar_sp("sp_obtener_estado", (id_vehiculo,))
    return filas[0] if filas else None


def actualizar_estado_bd(id_vehiculo, id_comando, conectado):
    ejecutar_sp(
        "sp_actualizar_estado", (id_vehiculo, id_comando, conectado), escritura=True
    )
    return {
        "id_vehiculo": id_vehiculo,
        "id_comando": id_comando,
        "conectado": conectado,
    }


# =========================
# ELIMINAR VEHÍCULO
# =========================


def eliminar_vehiculo(id_vehiculo):
    ejecutar_sp("sp_eliminar_vehiculo", (id_vehiculo,), escritura=True)
    return {"id_vehiculo": id_vehiculo}
