(() => {
  document.addEventListener('click', (event) => {
    const button = event.target.closest('.cegc-welcome__button');
    if (!button) return;
    const card = button.closest('.cegc-welcome');
    card.querySelector('.cegc-welcome__message').textContent = 'PHP, CSS y JavaScript conectados correctamente.';
  });
})();
