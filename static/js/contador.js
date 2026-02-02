// loja_gatos/static/js/contador.js
document.addEventListener('DOMContentLoaded', function() {
    function criarContador(idCampo, limite) {
        const campo = document.getElementById('id_' + idCampo);
        if (!campo) return;

        const contador = document.createElement('div');
        contador.style.cssText = 'font-size:10px; font-weight:bold; margin-top:3px; color:#888;';
        campo.parentNode.appendChild(contador);

        function atualizar() {
            contador.textContent = `${campo.value.length} / ${limite} caracteres`;
            contador.style.color = campo.value.length > limite ? '#ba2121' : '#888';
        }

        campo.addEventListener('input', atualizar);
        atualizar();
    }

    criarContador('nome', 115);
    criarContador('descricao_curta', 650);
    criarContador('descricao_detalhada', 1200); // Adicionado
});