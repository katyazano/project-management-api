# Historias de Usuario

## Épica 1: Registro y Autenticación

### Historia 1.1: Registro de Usuario

**Como** usuario nuevo,
**quiero** registrarme con mis credenciales,
**para** crear una cuenta en la plataforma.

**Criterios de Aceptación:**
- El sistema debe recibir las credenciales vía `POST /auth` y validar el formato del correo con Pydantic (`EmailStr`).
- La contraseña debe cumplir requisitos mínimos de seguridad: al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.
- Las contraseñas no deben guardarse en texto plano (deben ser hasheadas con Bcrypt).
- Si el nombre de usuario ya existe, el sistema debe devolver un error `400 Bad Request`.
- Al registrarse correctamente, el sistema debe devolver el usuario creado (id y username) con un código `201 Created`.

### Historia 1.2: Inicio de Sesión

**Como** usuario registrado,
**quiero** autenticarme con mis credenciales,
**para** obtener un token de acceso y poder usar el resto de la API.

**Criterios de Aceptación:**
- El sistema debe recibir las credenciales vía `POST /login` (form-encoded: `username`, `password`).
- Al autenticarse correctamente, el sistema debe devolver un token JWT válido por 1 hora.
- Si las credenciales son incorrectas, debe devolver un error `401 Unauthorized`.

---

## Épica 2: Gestión de Proyectos

### Historia 2.1: Creación de Proyectos

**Como** usuario autenticado,
**quiero** crear un nuevo proyecto en la plataforma,
**para** tener un espacio centralizado donde mi equipo pueda organizar el trabajo.

**Criterios de Aceptación:**
- Solo los usuarios con un token JWT válido pueden consumir el endpoint de creación.
- El usuario que crea el proyecto se asigna automáticamente como `OWNER` en la base de datos.
- El endpoint debe devolver el proyecto recién creado, incluyendo su ID, con un código `201 Created`.

---

## Épica 3: Invitaciones y Acceso Compartido

### Historia 3.1: Invitación por Correo (AWS SES)

**Como** dueño de un proyecto,
**quiero** generar un enlace de invitación seguro y enviarlo por correo electrónico,
**para** que otros colegas puedan unirse a mi proyecto.

**Criterios de Aceptación:**
- Solo el `OWNER` del proyecto puede disparar este endpoint (`GET /project/{id}/share?with={email}`); cualquier otro rol recibe `403 Forbidden`.
- El sistema debe generar un token temporal firmado que incluya el ID del proyecto y el correo del invitado, con una expiración definida (48 horas).
- El sistema debe enviar un correo electrónico al invitado a través de Amazon SES con el enlace de acceso (`/join?token=...`).
- El endpoint debe devolver el enlace generado en la respuesta, incluso si el envío del correo falla.

### Historia 3.2: Aceptación de Invitación

**Como** usuario invitado,
**quiero** hacer clic en el enlace que recibí por correo,
**para** ser agregado automáticamente al proyecto como editor.

**Criterios de Aceptación:**
- El usuario debe estar autenticado (token JWT válido) para consumir el endpoint `GET /join`.
- El endpoint debe validar que el token de la URL no haya expirado; de lo contrario, devuelve `400 Bad Request`.
- El sistema debe verificar que el correo del usuario logueado coincide exactamente con el correo al que se le emitió el token; de lo contrario, devuelve `403 Forbidden`.
- Al unirse, el usuario recibe el rol de `EDITOR` en la base de datos.
- Si el usuario ya es miembro del proyecto, el endpoint debe responder de forma idempotente (sin error) en lugar de fallar.

### Historia 3.3: Invitación Directa y Cambio de Rol

**Como** dueño de un proyecto,
**quiero** invitar directamente a un usuario registrado por su nombre de usuario y elegir su rol,
**para** darle acceso inmediato sin pasar por correo electrónico.

**Criterios de Aceptación:**
- Solo el `OWNER` del proyecto puede consumir este endpoint (`POST /project/{id}/invite?user={login}&role={role}`).
- El rol asignable debe limitarse a `EDITOR` o `VIEWER`; no debe ser posible asignar `OWNER` por esta vía.
- Si el usuario indicado no existe, el sistema debe devolver `404 Not Found`.
- Si el usuario ya es miembro del proyecto, el sistema debe actualizar su rol en lugar de devolver un error.

---

## Épica 4: Gestión de Documentos

### Historia 4.1: Subida de Documentos (AWS S3)

**Como** owner o editor de un proyecto,
**quiero** subir archivos a la plataforma,
**para** compartir recursos y documentos con mi equipo.

**Criterios de Aceptación:**
- Solo se permiten archivos con extensión `.pdf` o `.docx`; cualquier otro tipo devuelve `400 Bad Request`.
- El archivo debe enviarse a un bucket de almacenamiento seguro (AWS S3), usando una clave única por archivo.
- La base de datos debe guardar una referencia al documento (nombre, tamaño, y la llave del bucket).
- La subida debe respetar el límite de almacenamiento acumulado del proyecto; si se excede, el sistema debe devolver `400 Bad Request` sin subir ningún archivo.
- Los usuarios con rol `VIEWER` no pueden subir archivos (`403 Forbidden`).
- El entorno de pruebas debe poder simular la subida a S3 usando Moto, sin generar llamadas reales a AWS ni incurrir en costos.

### Historia 4.2: Descarga de Documentos

**Como** miembro de un proyecto,
**quiero** descargar un documento subido al proyecto,
**para** acceder a su contenido.

**Criterios de Aceptación:**
- Cualquier miembro del proyecto (owner, editor o viewer) puede descargar un documento.
- El sistema debe generar una URL prefirmada de S3 con tiempo de expiración y redirigir al usuario a ella (`307 Temporary Redirect`), en lugar de transmitir el archivo a través de la API.
- Si el documento no existe, el sistema debe devolver `404 Not Found`.

### Historia 4.3: Actualización y Eliminación de Documentos

**Como** owner o editor de un proyecto,
**quiero** reemplazar o eliminar un documento existente,
**para** mantener actualizados los recursos compartidos del proyecto.

**Criterios de Aceptación:**
- Solo owners y editores pueden actualizar (`PUT /document/{id}`) o eliminar (`DELETE /document/{id}`) un documento; los viewers reciben `403 Forbidden`.
- Al actualizar, el archivo en S3 se sobrescribe (misma clave) y el tamaño registrado en la base de datos se actualiza, respetando el límite de almacenamiento del proyecto.
- Al eliminar, el archivo correspondiente debe eliminarse tanto de S3 como de la base de datos.
- Al eliminar un proyecto completo, todos sus documentos deben eliminarse en cascada, tanto de la base de datos como de S3.
