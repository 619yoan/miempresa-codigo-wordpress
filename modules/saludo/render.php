<?php
defined('ABSPATH') || exit;

// Devuelve una función; no declares funciones globales ni clases aquí.
return static function (array $attributes, ?string $content = null): string {
    $name = isset($attributes['nombre']) ? (string) $attributes['nombre'] : 'Andrés';
    return '<section class="cegc-welcome">'
        . '<span class="cegc-welcome__eyebrow">CORTÉS Y ELIZALDE · GITHUB + WORDPRESS</span>'
        <h2>Hola desde GitHub, <?php echo esc_html($name); ?></h2>        
    . '<p>Este módulo se actualiza desde tu repositorio en GitHub.</p>'
        . '<button type="button" class="cegc-welcome__button">Probar interacción</button>'
        . '<p class="cegc-welcome__message" role="status" aria-live="polite"></p>'
        . '</section>';
};
