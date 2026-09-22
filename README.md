# Módulos para CE Git Code

Coloca el contenido de esta carpeta en la raíz de tu repositorio de GitHub.
Requiere instalar y configurar el plugin CE Git Code 1.0.0 en WordPress.

1. Conecta `propietario/repositorio` y rama `main` en Herramientas → CE Git Code.
2. Copia desde ese panel los secrets `WP_DEPLOY_URL` y `WP_DEPLOY_SECRET` a GitHub → Settings → Secrets and variables → Actions.
3. Haz commit y push a `main`. Incluye la carpeta oculta `.github`.
4. Revisa el resultado del workflow en Actions.
5. Inserta `[ce_code module="saludo" nombre="Andrés"]` en un bloque Shortcode.

Edita `modules/` y registra cada módulo en `codebridge.json`. La entrada puede ser PHP que devuelve una función, o HTML estático. Cada PHP debe comenzar exactamente con:

```php
<?php
defined('ABSPATH') || exit;
```

Guarda archivos con saltos LF. No declares funciones globales en las entradas.
Los CSS/JS declarados se cargan en todas las páginas públicas mientras el módulo esté activo: usa selectores exclusivos.
No incluyas claves, credenciales ni archivos binarios. Las imágenes se gestionan en WordPress.

El workflow revisa PHP y JavaScript antes de enviar; el servidor vuelve a revisar PHP con su propia versión. No se ejecutan módulos durante la validación. Para validar solo el paquete localmente, define `GITHUB_REPOSITORY`, `GITHUB_REF`, `GITHUB_SHA` (40 caracteres hexadecimales) y `GITHUB_RUN_NUMBER`, y ejecuta `python3 tools/deploy.py --check`.

Usa una sola instancia de este workflow por sitio y rama. No lo renombres después de empezar, ya que la secuencia depende de su contador de GitHub. Para volver a desplegar tras un rollback, usa un nuevo push o **Run workflow**, no **Re-run jobs**.

La guía completa está en `GUIA-INSTALACION.md` dentro del plugin.
