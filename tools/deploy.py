#!/usr/bin/env python3
"""No third-party dependencies. Signs exactly the bytes sent to WordPress."""
import argparse
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GUARD = b"<?php\ndefined('ABSPATH') || exit;\n"
PATH = re.compile(r"modules/(?:[a-z0-9][a-z0-9_-]*/)*[a-z0-9][a-z0-9_.-]*\.(php|html|css|js|json)\Z")


def package(root, env):
    manifest = json.loads((root / 'codebridge.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 1:
        raise ValueError('codebridge.json debe declarar schema: 1')
    modules = manifest.get('modules')
    if not isinstance(modules, list) or not 1 <= len(modules) <= 30:
        raise ValueError('Se requieren entre 1 y 30 módulos')
    files = {}
    total = 0
    source = root / 'modules'
    if source.is_symlink() or not source.is_dir():
        raise ValueError('modules debe ser una carpeta real')
    for path in sorted(source.rglob('*')):
        if path.is_symlink():
            raise ValueError('No se permiten enlaces simbólicos')
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        if not PATH.fullmatch(name) or '..' in name:
            raise ValueError(f'Ruta no permitida: {name}')
        content = path.read_bytes()
        if len(content) > 262144 or b'\0' in content:
            raise ValueError(f'Archivo inválido o demasiado grande: {name}')
        if path.suffix == '.php' and not content.startswith(GUARD):
            raise ValueError(f'Falta la protección ABSPATH exacta en {name}; usa el ejemplo y saltos LF')
        total += len(content)
        files[name] = base64.b64encode(content).decode('ascii')
    if not 1 <= len(files) <= 100 or total > 1048576:
        raise ValueError('Máximo 100 archivos y 1 MiB de código')
    seen = set()
    for module in modules:
        if not isinstance(module, dict):
            raise ValueError('Módulo inválido')
        ident = module.get('id', '')
        entry = module.get('entry', '')
        if not isinstance(ident, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}', ident) or ident in seen:
            raise ValueError('ID inválido o duplicado')
        seen.add(ident)
        if not isinstance(module.get('name'), str) or len(module['name'].encode()) > 120:
            raise ValueError('Nombre inválido')
        if not isinstance(entry, str) or entry not in files or not entry.endswith(('.php', '.html')):
            raise ValueError('Entrada PHP/HTML ausente')
        for kind in ('css', 'js'):
            assets = module.get(kind, [])
            if not isinstance(assets, list) or len(assets) > 10:
                raise ValueError('Lista de recursos inválida')
            if any(not isinstance(asset, str) or asset not in files or not asset.endswith('.' + kind) for asset in assets):
                raise ValueError('Recurso ausente o de tipo incorrecto')
    repo, ref, commit = env['GITHUB_REPOSITORY'], env['GITHUB_REF'], env['GITHUB_SHA']
    sequence = int(env['GITHUB_RUN_NUMBER'])
    if not re.fullmatch(r'[a-f0-9]{40}', commit) or not ref.startswith('refs/heads/') or sequence < 1:
        raise ValueError('Metadatos de GitHub inválidos')
    body = json.dumps(dict(schema=1, repository=repo, ref=ref, commit=commit,
                           sequence=sequence, modules=modules, files=files),
                      ensure_ascii=True, separators=(',', ':'), sort_keys=True).encode('utf-8')
    if len(body) > 2097152:
        raise ValueError('Paquete mayor de 2 MiB')
    return body


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('El endpoint redirige. Configura su URL HTTPS final exacta.')


def deploy(body, url, secret):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('WP_DEPLOY_URL debe ser una URL HTTPS sin credenciales ni fragmentos')
    if len(secret) < 32:
        raise ValueError('WP_DEPLOY_SECRET no configurado o demasiado corto')
    opener = urllib.request.build_opener(NoRedirect())
    for attempt in range(3):
        timestamp = str(int(time.time()))
        signature = hmac.new(secret.encode(), timestamp.encode() + b'.' + body, hashlib.sha256).hexdigest()
        request = urllib.request.Request(url, data=body, method='POST', headers={
            'Content-Type': 'application/json', 'X-CEGC-Timestamp': timestamp,
            'X-CEGC-Signature': 'sha256=' + signature, 'User-Agent': 'CE-Git-Code/1.0'})
        try:
            with opener.open(request, timeout=45) as response:
                result = json.loads(response.read(65536))
            if result.get('status') not in ('deployed', 'already_received'):
                raise ValueError('Respuesta inesperada del plugin')
            if result.get('status') == 'already_received' and result.get('active_commit') != result.get('commit'):
                raise ValueError('La versión ya fue recibida pero se restauró otra. Inicia un nuevo workflow; no repitas el anterior.')
            print('WordPress:', result['status'], result['commit'])
            return result
        except urllib.error.HTTPError as error:
            detail = error.read(4096).decode('utf-8', errors='replace')
            # Do not print HTML, URLs or secret-bearing proxies' responses.
            try:
                detail = json.loads(detail).get('message', 'Error HTTP')
            except (ValueError, AttributeError):
                detail = 'Respuesta no JSON; revisa firewall, ruta y HTTPS'
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise ValueError(f'HTTP {error.code}: {detail}') from None
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise ValueError('No se pudo conectar con WordPress; revisa Actions y la conectividad del hosting') from None
        time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Validar y empaquetar sin enviar')
    args = parser.parse_args()
    body = package(Path(__file__).resolve().parents[1], os.environ)
    if args.check:
        print(f'Paquete válido: {len(body)} bytes. No se ha enviado.')
    else:
        deploy(body, os.environ['WP_DEPLOY_URL'], os.environ['WP_DEPLOY_SECRET'])


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError) as error:
        print(f'Despliegue detenido: {error}', file=sys.stderr)
        sys.exit(1)
