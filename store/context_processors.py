from store.models import Produto, Variacao


def carrinho_detalhado(request):
    carrinho_sessao = request.session.get('carrinho', {})
    itens_carrinho = []
    total_carrinho = 0


    # Mantendo sua lista automatizada de países
    paises = [
        "Afeganistão", "África do Sul", "Albânia", "Alemanha", "Andorra", "Angola",
        "Anguila", "Antártica", "Antígua e Barbuda", "Antilhas Holandesas",
        "Arábia Saudita", "Argélia", "Argentina", "Armênia", "Aruba", "Austrália",
        "Áustria", "Azerbaijão", "Bahamas", "Bahrein", "Bangladesh", "Barbados",
        "Belarus", "Bélgica", "Belize", "Benin", "Bermudas", "Bolívia", "Brasil",
        "Canadá", "Chile", "China", "Colômbia", "Coreia do Sul", "Costa Rica",
        "Croácia", "Cuba", "Dinamarca", "Egito", "Emirados Árabes Unidos",
        "Equador", "Espanha", "Estados Unidos", "França", "Grécia", "Guatemala",
        "Holanda", "Honduras", "Hungria", "Índia", "Indonésia", "Inglaterra",
        "Irlanda", "Islândia", "Israel", "Itália", "Jamaica", "Japão", "México",
        "Noruega", "Nova Zelândia", "Panamá", "Paraguai", "Peru", "Polônia",
        "Portugal", "Reino Unido", "República Checa", "República Dominicana",
        "Romênia", "Rússia", "Suécia", "Suíça", "Tailândia", "Turquia", "Ucrânia",
        "Uruguai", "Venezuela", "Vietnã"
    ]

    for item_key, quantidade in carrinho_sessao.items():
        try:
            # CORREÇÃO: Tratamento de chaves com hífens (ex: '11-2')
            parts = str(item_key).split('-')
            p_id = parts[0]
            v_id = parts[1] if len(parts) > 1 else None

            produto = Produto.objects.get(id=int(p_id))

            # Define nome e imagem padrão
            nome_exibicao = produto.nome
            v_obj = None

            # Busca variação se existir para pegar nome e foto específica
            if v_id:
                try:
                    v_obj = Variacao.objects.get(id=int(v_id))
                    nome_exibicao = f"{produto.nome} ({v_obj.valor})"
                except Variacao.DoesNotExist:
                    pass

            # Define a imagem (Variante > Produto)
            imagem_url = v_obj.imagem.url if v_obj and v_obj.imagem else (produto.imagem.url if produto.imagem else '')

            subtotal = float(produto.preco_venda) * quantidade
            total_carrinho += subtotal

            itens_carrinho.append({
                'id': item_key,  # Mantém a chave completa para os botões do JS
                'nome': nome_exibicao,
                'preco': float(produto.preco_venda),
                'imagem': imagem_url,
                'quantidade': quantidade,
                'subtotal': subtotal
            })
        except (Produto.DoesNotExist, ValueError):
            continue

            # DEFINIÇÃO DO FRETE (ESTRATÉGIA DROPSHIPPING)
    valor_frete = 0.00
    total_final = float(total_carrinho) + valor_frete

    return {
            'carrinho_lateral': itens_carrinho,
            'total_carrinho_lateral': round(total_carrinho, 2),
            'valor_frete': valor_frete,  # Adicionado para o template
            'total_com_frete': round(total_final, 2),  # Adicionado para o template
            'lista_paises': paises
            }