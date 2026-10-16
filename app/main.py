# app/main.py
from app.models.demo import (
    DemoCrear,
    DemoActualizar,
    MovimientoDemoCrear,
    MovimientoDemoActualizar,
)

from app.services.iot_service import (
    crear_demo,
    actualizar_demo,
    eliminar_demo,
    obtener_demos,
    agregar_movimiento_demo,
    actualizar_movimiento_demo,
    eliminar_movimiento_demo,
    obtener_movimientos_demo,
    obtener_estado,
    actualizar_estado_bd,
    eliminar_vehiculo,
)

import os
import logging
from datetime import datetime, timezone

import mysql.connector
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.models.vehiculo import (
    VehiculoCrear,
    VehiculoActualizar,
    ComandoCrear,
    ComandoActualizar,
    HistorialCrear,
    EstadoVehiculoActualizar,
)
from app.services import iot_service
from app.websocket.websocket_manager import manager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API Vehículos IoT",
    description=(
        "API REST para administrar vehículos IoT, comandos, historial, estado y demos. "
        "La comunicación en tiempo real está disponible mediante WebSocket en `/ws`."
    ),
    version="1.0.0",
    docs_url=None,
    openapi_tags=[
        {"name": "Vehículos", "description": "Consulta y administración de vehículos registrados."},
        {"name": "Comandos", "description": "Comandos disponibles para cada vehículo."},
        {"name": "Historial", "description": "Registro y consulta de acciones de los vehículos."},
        {"name": "Estado", "description": "Estado operativo y conectividad de los vehículos."},
        {"name": "Demos", "description": "Secuencias de demostración y sus movimientos."},
    ],
)

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


@app.get("/docs", include_in_schema=False)
async def documentacion_swagger():
    """Swagger UI con estilos personalizados; conserva el esquema OpenAPI original."""
    pagina = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} — Documentación",
        swagger_ui_parameters={"filter": True, "displayRequestDuration": True},
    )
    contenido = pagina.body.decode("utf-8").replace(
        "</head>",
        '<link rel="stylesheet" href="/static/swagger-custom.css"></head>',
    )
    return HTMLResponse(contenido)


async def notificar(tipo, accion, datos=None):
    """Publica una acción a todos los clientes WebSocket conectados."""
    await manager.enviar_a_todos(
        {
            "tipo": tipo,
            "accion": accion,
            "datos": datos or {},
            "fecha_hora": datetime.now(timezone.utc).isoformat(),
        }
    )


def ejecutar_operacion(funcion, *args):
    """Convierte errores de MySQL en respuestas HTTP controladas."""
    try:
        return funcion(*args)

    except mysql.connector.Error as error:
        logger.exception("Error de base de datos")

        if error.sqlstate == "45000":
            raise HTTPException(status_code=400, detail=str(error.msg))

        if error.errno in (1062, 1451, 1452):
            raise HTTPException(
                status_code=409,
                detail="Conflicto con un registro o una relación de la base de datos",
            )

        raise HTTPException(
            status_code=500,
            detail="Error al ejecutar la operación en MySQL",
        )


def validar_ids_positivos(**ids):
    """Rechaza identificadores inválidos antes de consultar la base de datos."""
    if any(valor <= 0 for valor in ids.values()):
        raise HTTPException(status_code=400, detail="ID inválido")


@app.get("/")
async def inicio(request: Request):
    """Página de bienvenida y acceso rápido a la API."""
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            {
                "mensaje": "API Vehículos IoT funcionando",
                "documentacion": "/docs",
                "websocket": "/ws",
            }
        )
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


# --------------------------------------------------
# VEHICULOS
# --------------------------------------------------


# CONSULTA TODOS LOS VEHICULOS
@app.get("/api/vehiculos", tags=["Vehículos"], summary="Listar vehículos", description="Devuelve los vehículos registrados y notifica la consulta a los clientes WebSocket conectados.")
async def listar_vehiculos():
    datos = ejecutar_operacion(iot_service.obtener_vehiculos)
    await notificar("vehiculos", "consultar_todos")
    return datos


# CONSULTA UN VEHICULO POR SU ID
@app.get("/api/vehiculos/{id_vehiculo}", tags=["Vehículos"], summary="Consultar vehículo", description="Busca un vehículo por su identificador.")
async def consultar_vehiculo(id_vehiculo: int):
    validar_ids_positivos(id_vehiculo=id_vehiculo)

    datos = ejecutar_operacion(
        iot_service.obtener_vehiculo,
        id_vehiculo,
    )

    if datos is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    await notificar(
        "vehiculos",
        "consultar_uno",
        {"id_vehiculo": id_vehiculo},
    )
    return datos


# CREA UN VEHICULO
@app.post("/api/vehiculos", status_code=201, tags=["Vehículos"], summary="Crear vehículo")
async def crear_vehiculo(datos: VehiculoCrear):
    resultado = ejecutar_operacion(
        iot_service.crear_vehiculo,
        datos,
    )

    await notificar("vehiculos", "crear", resultado)
    return resultado


# ACTUALIZA LOS DATOS DE UN VEHICULO
@app.post("/api/vehiculos/{id_vehiculo}/actualizar", tags=["Vehículos"], summary="Actualizar vehículo")
async def actualizar_vehiculo(
    id_vehiculo: int,
    datos: VehiculoActualizar,
):
    validar_ids_positivos(id_vehiculo=id_vehiculo)

    # Comprueba si existe antes de intentar actualizarlo.
    actual = ejecutar_operacion(
        iot_service.obtener_vehiculo,
        id_vehiculo,
    )

    if actual is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    resultado = ejecutar_operacion(
        iot_service.actualizar_vehiculo,
        id_vehiculo,
        datos,
    )

    await notificar(
        "vehiculos",
        "actualizar",
        {**resultado, "activo": datos.activo},
    )
    return resultado


# --------------------------------------------------
# COMANDOS
# --------------------------------------------------


# CONSULTA LOS COMANDOS DE UN VEHICULO EN ESPECIFICO
@app.get("/api/vehiculos/{id_vehiculo}/comandos", tags=["Comandos"], summary="Listar comandos del vehículo")
async def listar_comandos(id_vehiculo: int):
    validar_ids_positivos(id_vehiculo=id_vehiculo)

    datos = ejecutar_operacion(
        iot_service.obtener_comandos_vehiculo,
        id_vehiculo,
    )

    await notificar(
        "comandos",
        "consultar",
        {"id_vehiculo": id_vehiculo},
    )
    return datos


# CREA UN COMANDO PARA UN VEHICULO EN ESPECIFICO
@app.post("/api/comandos", status_code=201, tags=["Comandos"], summary="Crear comando")
async def crear_comando(datos: ComandoCrear):
    # Comprueba que exista el vehículo al que pertenece el comando.
    vehiculo = ejecutar_operacion(
        iot_service.obtener_vehiculo,
        datos.id_vehiculo,
    )

    if vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    resultado = ejecutar_operacion(
        iot_service.crear_comando,
        datos,
    )

    await notificar(
        "comandos",
        "crear",
        {**resultado, "id_vehiculo": datos.id_vehiculo},
    )
    return resultado


# ACTUALIZA LA INFORMACIÓN DE UN COMANDO EN ESPECIFICO
@app.post("/api/comandos/{id_comando}/actualizar", tags=["Comandos"], summary="Actualizar comando")
async def actualizar_comando(
    id_comando: int,
    datos: ComandoActualizar,
):
    validar_ids_positivos(id_comando=id_comando)

    # El procedimiento no devuelve filas afectadas.
    # Buscamos el comando dentro de los vehículos para comprobar existencia.
    vehiculos = ejecutar_operacion(iot_service.obtener_vehiculos)

    comando_encontrado = None

    for vehiculo in vehiculos:
        comandos = ejecutar_operacion(
            iot_service.obtener_comandos_vehiculo,
            vehiculo["id_vehiculo"],
        )

        comando_encontrado = next(
            (c for c in comandos if c["id_comando"] == id_comando),
            None,
        )

        if comando_encontrado is not None:
            break

    if comando_encontrado is None:
        raise HTTPException(status_code=404, detail="Comando no encontrado")

    resultado = ejecutar_operacion(
        iot_service.actualizar_comando,
        id_comando,
        datos,
    )

    await notificar(
        "comandos",
        "actualizar",
        {**resultado, "activo": datos.activo},
    )
    return resultado


# ELIMINA UN COMANDO ESPECIFICO
@app.post("/api/comandos/{id_comando}/eliminar", tags=["Comandos"], summary="Eliminar comando")
async def eliminar_comando(id_comando: int):
    validar_ids_positivos(id_comando=id_comando)

    vehiculos = ejecutar_operacion(iot_service.obtener_vehiculos)

    comando_encontrado = None

    for vehiculo in vehiculos:
        comandos = ejecutar_operacion(
            iot_service.obtener_comandos_vehiculo,
            vehiculo["id_vehiculo"],
        )

        comando_encontrado = next(
            (c for c in comandos if c["id_comando"] == id_comando),
            None,
        )

        if comando_encontrado is not None:
            break

    if comando_encontrado is None:
        raise HTTPException(status_code=404, detail="Comando no encontrado")

    resultado = ejecutar_operacion(
        iot_service.eliminar_comando,
        id_comando,
    )

    await notificar("comandos", "eliminar", resultado)
    return resultado


# --------------------------------------------------
# HISTORIAL
# --------------------------------------------------


# OBTIENE EL HISTORIAL DE UN VEHICULO EN ESPECIFICO
@app.get("/api/vehiculos/{id_vehiculo}/historial", tags=["Historial"], summary="Consultar historial")
async def consultar_historial(id_vehiculo: int):
    validar_ids_positivos(id_vehiculo=id_vehiculo)

    datos = ejecutar_operacion(
        iot_service.obtener_historial,
        id_vehiculo,
    )

    await notificar(
        "historial",
        "consultar",
        {"id_vehiculo": id_vehiculo},
    )
    return datos


# AGREGA UN MOVIMIENTO AL HISTORIAL DE UN VEHICULO
@app.post("/api/historial", status_code=201, tags=["Historial"], summary="Registrar movimiento en historial")
async def crear_historial(datos: HistorialCrear):
    vehiculo = ejecutar_operacion(
        iot_service.obtener_vehiculo,
        datos.id_vehiculo,
    )

    if vehiculo is None:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    if datos.id_comando is not None:
        comandos = ejecutar_operacion(
            iot_service.obtener_comandos_vehiculo,
            datos.id_vehiculo,
        )

        if not any(c["id_comando"] == datos.id_comando for c in comandos):
            raise HTTPException(
                status_code=400,
                detail="El comando no pertenece al vehículo indicado",
            )

    resultado = ejecutar_operacion(
        iot_service.registrar_historial,
        datos,
    )

    await notificar("historial", "registrar", resultado)
    return resultado


# --------------------------------------------------
# ACTUALIZAR ESTADO OPERATIVO MEDIANTE UN COMANDO
# --------------------------------------------------


# ACTUALIZA EL ESTADO ACTUAL DE UN VEHICULO
@app.post("/api/vehiculos/{id_vehiculo}/estado", tags=["Estado"], summary="Actualizar estado del vehículo")
async def ruta_actualizar_estado(id_vehiculo: int, datos: EstadoVehiculoActualizar):
    validar_ids_positivos(id_vehiculo=id_vehiculo)
    # Verificar que el vehículo exista
    vehiculo = ejecutar_operacion(iot_service.obtener_vehiculo, id_vehiculo)

    if not vehiculo:
        raise HTTPException(status_code=404, detail="El vehículo no existe.")

    # Verificar que el comando pertenezca al vehículo y esté activo
    comando = None

    if datos.id_comando is not None:
        comandos = ejecutar_operacion(
            iot_service.obtener_comandos_vehiculo, id_vehiculo
        )

        comando = next(
            (c for c in comandos if c["id_comando"] == datos.id_comando), None
        )

        if not comando or not comando["activo"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    "El comando no existe, no pertenece " "al vehículo o está inactivo."
                ),
            )

    # Actualizar estado mediante el procedimiento almacenado
    resultado = ejecutar_operacion(
        actualizar_estado_bd, id_vehiculo, datos.id_comando, datos.conectado
    )

    # Registrar la acción en el historial
    historial = HistorialCrear(
        id_vehiculo=id_vehiculo, id_comando=datos.id_comando, origen=datos.origen
    )

    ejecutar_operacion(iot_service.registrar_historial, historial)

    # Notificar el cambio a los clientes WebSocket
    evento = {
        "tipo": "estado_vehiculo",
        "accion": "actualizar",
        "datos": {
            **resultado,
            "vehiculo": vehiculo["nombre"],
            "comando": comando["nombre"] if comando else None,
            "origen": datos.origen,
        },
    }

    await manager.enviar_a_todos(evento)

    return {"mensaje": "Estado actualizado e historial registrado.", **resultado}


# OBTIENE EL ESTADO DE UN VEHICULO
@app.get("/api/vehiculos/{id_vehiculo}/estado", tags=["Estado"], summary="Consultar estado del vehículo")
async def ruta_obtener_estado(id_vehiculo: int):
    validar_ids_positivos(id_vehiculo=id_vehiculo)
    resultado = ejecutar_operacion(obtener_estado, id_vehiculo)

    if not resultado:
        raise HTTPException(
            status_code=404, detail="El vehículo todavía no tiene un estado registrado."
        )

    return resultado


# --------------------------------------------------
# WEBSOCKET
# --------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.conectar(websocket)

    try:
        await websocket.send_json(
            {
                "tipo": "conexion",
                "mensaje": "Conectado a la API de vehículos IoT",
            }
        )

        while True:
            mensaje = await websocket.receive_json()

            # Recibir un mensaje no ejecuta automáticamente un comando.
            # Las acciones de control se validan mediante la API HTTP.
            await websocket.send_json(
                {
                    "tipo": "mensaje_recibido",
                    "datos": mensaje,
                }
            )

    except WebSocketDisconnect:
        await manager.desconectar(websocket)

    except Exception:
        await manager.desconectar(websocket)
        logger.exception("Error en una conexión WebSocket")


# =========================
# DEMOS
# =========================


# CREA DEMOS
@app.post("/api/demos", tags=["Demos"], summary="Crear demo")
async def ruta_crear_demo(datos: DemoCrear):
    resultado = ejecutar_operacion(crear_demo, datos)
    await notificar("demo", "crear", resultado)
    return resultado


# ACTUALIZA UN DEMO
@app.post("/api/demos/{id_demo}/actualizar", tags=["Demos"], summary="Actualizar demo")
async def ruta_actualizar_demo(id_demo: int, datos: DemoActualizar):
    validar_ids_positivos(id_demo=id_demo)
    resultado = ejecutar_operacion(actualizar_demo, id_demo, datos)
    await notificar("demo", "actualizar", resultado)
    return resultado


# ELIMINA UN DEMO
@app.post("/api/demos/{id_demo}/eliminar", tags=["Demos"], summary="Eliminar demo")
async def ruta_eliminar_demo(id_demo: int):
    validar_ids_positivos(id_demo=id_demo)
    resultado = ejecutar_operacion(eliminar_demo, id_demo)
    await notificar("demo", "eliminar", resultado)
    return resultado


# CONSULTA LOS DEMOS DE UN VEHICULO
@app.get("/api/vehiculos/{id_vehiculo}/demos", tags=["Demos"], summary="Listar demos del vehículo")
async def ruta_obtener_demos(id_vehiculo: int):
    validar_ids_positivos(id_vehiculo=id_vehiculo)
    resultado = ejecutar_operacion(obtener_demos, id_vehiculo)
    await notificar(
        "demo", "consultar", {"id_vehiculo": id_vehiculo, "demos": resultado}
    )
    return resultado


# =========================
# MOVIMIENTOS DE DEMOS
# =========================


# AGREGA UN MOVIMIENTO A UN DEMO
@app.post("/api/demos/{id_demo}/movimientos", tags=["Demos"], summary="Agregar movimiento a demo")
async def ruta_agregar_movimiento_demo(id_demo: int, datos: MovimientoDemoCrear):
    validar_ids_positivos(id_demo=id_demo)
    resultado = ejecutar_operacion(agregar_movimiento_demo, id_demo, datos)
    await notificar("movimiento_demo", "agregar", resultado)
    return resultado


# ACTUALIZA EL MOVIMIENTO DE UN DEMO
@app.post("/api/movimientos-demo/{id_demo_movimiento}/actualizar", tags=["Demos"], summary="Actualizar movimiento de demo")
async def ruta_actualizar_movimiento_demo(
    id_demo_movimiento: int, datos: MovimientoDemoActualizar
):
    validar_ids_positivos(id_demo_movimiento=id_demo_movimiento)
    resultado = ejecutar_operacion(
        actualizar_movimiento_demo, id_demo_movimiento, datos
    )
    await notificar("movimiento_demo", "actualizar", resultado)
    return resultado


@app.post("/api/movimientos-demo/{id_demo_movimiento}/eliminar", tags=["Demos"], summary="Eliminar movimiento de demo")
async def ruta_eliminar_movimiento_demo(id_demo_movimiento: int):
    validar_ids_positivos(id_demo_movimiento=id_demo_movimiento)
    resultado = ejecutar_operacion(eliminar_movimiento_demo, id_demo_movimiento)
    await notificar("movimiento_demo", "eliminar", resultado)
    return resultado


# OBTIENE LOS MOVIMIENTOS DE UN DEMO
@app.get("/api/demos/{id_demo}/movimientos", tags=["Demos"], summary="Listar movimientos de demo")
async def ruta_obtener_movimientos_demo(id_demo: int):
    validar_ids_positivos(id_demo=id_demo)
    resultado = ejecutar_operacion(obtener_movimientos_demo, id_demo)
    await notificar(
        "movimiento_demo", "consultar", {"id_demo": id_demo, "movimientos": resultado}
    )
    return resultado


@app.post("/api/vehiculos/{id_vehiculo}/eliminar", tags=["Vehículos"], summary="Eliminar vehículo")
async def ruta_eliminar_vehiculo(id_vehiculo: int):
    validar_ids_positivos(id_vehiculo=id_vehiculo)
    resultado = ejecutar_operacion(eliminar_vehiculo, id_vehiculo)
    await notificar("vehiculo", "eliminar", resultado)
    return resultado


# -- EJECUCION DE LA DEMO


@app.post("/api/vehiculos/{id_vehiculo}/demos/{id_demo}/ejecutar", tags=["Demos"], summary="Ejecutar demo", description="Envía cada movimiento a los clientes WebSocket conectados, espera la duración y pausa indicadas, y actualiza el estado final del vehículo.")
async def ruta_ejecutar_demo(id_vehiculo: int, id_demo: int):
    validar_ids_positivos(id_vehiculo=id_vehiculo, id_demo=id_demo)
    # 1. Verificar que la DEMO pertenezca al vehículo
    demos = ejecutar_operacion(obtener_demos, id_vehiculo)

    demo = next(
        (d for d in demos if d["id_demo"] == id_demo and d["activo"]),
        None,
    )

    if demo is None:
        raise HTTPException(
            status_code=404,
            detail="La DEMO no existe, no pertenece al vehículo o está inactiva.",
        )

    # 2. Consultar los movimientos de la DEMO
    movimientos = ejecutar_operacion(
        obtener_movimientos_demo,
        id_demo,
    )

    if not movimientos:
        raise HTTPException(
            status_code=400,
            detail="La DEMO no contiene movimientos.",
        )

    # 3. Ejecutar los movimientos en el orden indicado
    movimientos = sorted(
        movimientos,
        key=lambda movimiento: movimiento["orden"],
    )

    ultimo_id_comando = None

    for movimiento in movimientos:
        ultimo_id_comando = movimiento["id_comando"]

        evento = {
            "tipo": "demo",
            "accion": "ejecutar_movimiento",
            "datos": {
                "id_vehiculo": id_vehiculo,
                "id_demo": id_demo,
                "id_comando": movimiento["id_comando"],
                "orden": movimiento["orden"],
                "duracion_ms": movimiento["duracion_ms"],
                "pausa_ms": movimiento["pausa_ms"],
            },
        }

        # Enviar el movimiento a los clientes conectados por WebSocket
        await manager.enviar_a_todos(evento)

        # Respetar duración y pausa configuradas, en milisegundos
        await asyncio.sleep(movimiento["duracion_ms"] / 1000)
        await asyncio.sleep(movimiento["pausa_ms"] / 1000)

    # 4. Actualizar el estado final usando sp_actualizar_estado
    resultado_estado = ejecutar_operacion(
        actualizar_estado_bd,
        id_vehiculo,
        ultimo_id_comando,
        True,
    )

    # 5. Notificar que terminó la DEMO
    resultado = {
        "mensaje": "DEMO ejecutada correctamente.",
        "id_vehiculo": id_vehiculo,
        "id_demo": id_demo,
        "movimientos_ejecutados": len(movimientos),
        "estado_final": resultado_estado,
    }

    await notificar("demo", "finalizada", resultado)

    return resultado


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "8000")),
    )
