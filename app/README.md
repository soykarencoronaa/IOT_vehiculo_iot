## Conexión WebSocket

### Descripción
El proyecto utiliza WebSocket para establecer una comunicación bidireccional entre el servidor FastAPI y los clientes conectados. Esto permite enviar notificaciones en tiempo real cuando se realizan acciones mediante los endpoints de la API.

### Dirección de conexión

En un entorno local, la conexión se realiza mediante:

```text
ws://127.0.0.1:8000/ws
```

Si el servidor utiliza otro host o puerto, se debe ajustar la dirección. Para conexiones seguras mediante HTTPS, se debe utilizar `wss://` y configurar el servidor para admitir conexiones seguras.

### Ejemplo de conexión con JavaScript

```javascript
const socket = new WebSocket(
  "ws://127.0.0.1:8000/ws"
);

socket.onopen = () => {
  console.log("Conexión WebSocket establecida");
};

socket.onmessage = (event) => {
  const datos = JSON.parse(event.data);
  console.log("Notificación recibida:", datos);
};

socket.onerror = (error) => {
  console.error("Error en WebSocket:", error);
};

socket.onclose = () => {
  console.log("Conexión WebSocket cerrada");
};
```

### Funcionamiento

1. El cliente establece una conexión con `/ws`.
2. El servidor mantiene la conexión mientras esté activa.
3. Cuando un endpoint realiza una acción que genera una notificación, el administrador de conexiones (`websocket_manager.py`) puede distribuir el evento a los clientes conectados.
4. Los clientes reciben los mensajes y pueden actualizar su interfaz sin tener que consultar repetidamente la API.

**Nota:** El formato del mensaje JSON depende de los eventos definidos en el código del proyecto.

### Consideraciones

- Iniciar el servidor FastAPI antes de conectar el cliente.
- Mantener la conexión abierta mientras se necesiten notificaciones.
- Implementar reconexión en el cliente si se requiere tolerancia a desconexiones.
- En producción, utilizar `wss://` y configurar controles de seguridad adecuados.
