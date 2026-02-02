from django.shortcuts import render, get_object_or_404, redirect  # Adicionado redirect
from .models import Produto, Pedido, ItemPedido, Avaliacao, Variacao
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import requests
from django.shortcuts import render
from .utils import consultar_frete_adm
from django.contrib.admin.views.decorators import staff_member_required
from .context_processors import carrinho_detalhado
import uuid
import os
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from django.utils import timezone
from datetime import timedelta
import re

def home(request):
    produtos = Produto.objects.filter(ativo=True)
    # Lista de tuplas para o grid de ícones
    categorias = [
        ('brinquedos', 'Brinquedos'),
        ('alimentacao', 'Alimentação'),
        ('conforto', 'Conforto'),
        ('higiene', 'Higiene'),
    ]
    return render(request, 'home.html', {
        'produtos': produtos,
        'categories_list': categorias
    })

def produto_detalhe(request, pk):  # Mudado de id para pk
    produto = get_object_or_404(Produto, pk=pk)  # Mudado para buscar por pk
    avaliacoes = produto.avaliacoes.all().order_by('-data_criacao')

    if request.method == 'POST' and request.user.is_authenticated:
        nota = request.POST.get('nota')
        comentario = request.POST.get('comentario')

        if nota and comentario:
            Avaliacao.objects.create(
                produto=produto,
                usuario=request.user,
                nota=int(nota),
                comentario=comentario
            )
        return redirect('produto_detalhe', pk=pk)  # Redireciona usando pk

    return render(request, 'produto_detalhe.html', {
        'produto': produto,
        'avaliacoes': avaliacoes
    })


def adicionar_ao_carrinho(request, produto_id):
    # Captura a variação vinda da URL (ex: ?variacao_id=5)
    variacao_id = request.GET.get('variacao_id')
    carrinho = request.session.get('carrinho', {})

    # Criamos uma chave única para o item no carrinho
    # Ex: "10" (sem variação) ou "10-5" (produto 10, variação 5)
    item_key = f"{produto_id}-{variacao_id}" if variacao_id else str(produto_id)

    # Adiciona ou incrementa a quantidade
    carrinho[item_key] = carrinho.get(item_key, 0) + 1
    request.session['carrinho'] = carrinho
    request.session.modified = True

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        itens_completos = []
        total_valor = 0

        for key, qtd in carrinho.items():
            parts = key.split('-')
            p_id = parts[0]
            v_id = parts[1] if len(parts) > 1 else None

            p_obj = get_object_or_404(Produto, id=int(p_id))

            # 1. Definimos o nome padrão PRIMEIRO para evitar o erro de variável inexistente
            nome_exibicao = p_obj.nome
            v_obj = None

            if v_id:
                try:
                    v_obj = Variacao.objects.get(id=int(v_id))
                    nome_exibicao = f"{p_obj.nome} ({v_obj.valor})"
                except Variacao.DoesNotExist:
                    pass

            # 2. Definimos a imagem (se for variante e tiver foto, usa ela, senão a do produto)
            imagem_url = v_obj.imagem.url if v_obj and v_obj.imagem else (p_obj.imagem.url if p_obj.imagem else '')

            subtotal = float(p_obj.preco_venda) * qtd
            total_valor += subtotal

            itens_completos.append({
                'id': key,
                'nome': nome_exibicao,
                'preco': str(p_obj.preco_venda),
                'imagem': imagem_url,
                'quantidade': qtd
            })

        return JsonResponse({
            'status': 'sucesso',
            'itens_completos': itens_completos,
            'total_itens': sum(carrinho.values()),
            'total_carrinho': round(total_valor, 2)
        })

    return redirect('carrinho')

def ver_carrinho(request):
    carrinho_session = request.session.get('carrinho', {})
    itens_carrinho = []
    total = 0

    for item_key, quantidade in carrinho_session.items():
        # Pegamos apenas o ID do produto antes do hífen
        produto_id = item_key.split('-')[0]
        produto = get_object_or_404(Produto, id=int(produto_id))

        subtotal = produto.preco_venda * quantidade
        total += subtotal
        itens_carrinho.append({
            'produto': produto,
            'quantidade': quantidade,
            'subtotal': subtotal
        })

    return render(request, 'carrinho.html', {'itens': itens_carrinho, 'total': total})

def remover_do_carrinho(request, produto_id):
    carrinho = request.session.get('carrinho', {})
    # Convertemos para string para garantir o encaixe com a chave da sessão
    pid = str(produto_id)

    if pid in carrinho:
        del carrinho[pid]
        request.session['carrinho'] = carrinho
        request.session.modified = True  # Salva a alteração na sessão

    return JsonResponse({
        'status': 'sucesso',
        'total_itens': sum(carrinho.values()),
        'total_carrinho': calcular_total(carrinho)
    })

def alterar_quantidade(request, produto_id, acao):
    carrinho = request.session.get('carrinho', {})
    pid = str(produto_id)  # Agora aceita "5" ou "5-2"

    if pid in carrinho:
        if acao == 'aumentar':
            carrinho[pid] += 1
        elif acao == 'diminuir' and carrinho[pid] > 1:
            carrinho[pid] -= 1

        request.session['carrinho'] = carrinho
        request.session.modified = True

    return JsonResponse({
        'status': 'sucesso',
        'nova_qtd': carrinho.get(pid, 0),
        'total_carrinho': calcular_total(carrinho),
        'total_itens': sum(carrinho.values())
    })


# Função auxiliar para não repetir código
def calcular_total(carrinho):
    total = 0
    for key, qtd in carrinho.items():
        # Separamos o ID do produto da variante (ex: de '11-2' pegamos apenas '11')
        produto_id = key.split('-')[0]
        produto = Produto.objects.get(id=int(produto_id))
        total += float(produto.preco_venda) * qtd
    return round(total, 2)


def lista_produtos(request):
    # 1. Busca inicial dos produtos ativos
    produtos = Produto.objects.filter(ativo=True)
    categorias_menu = [
        ('brinquedos', 'Brinquedos'),
        ('alimentacao', 'Alimentação'),
        ('conforto', 'Caminhas e Conforto'),
        ('higiene', 'Higiene'),
    ]

    # 2. Captura os filtros da URL (ex: ?categoria=brinquedos)
    categoria_filtrada = request.GET.get('categoria')
    ordem = request.GET.get('ordem')
    busca = request.GET.get('q')

    # Filtro de Busca (Nome ou Descrição)
    if busca:
        produtos = produtos.filter(nome__icontains=busca) | produtos.filter(descricao_curta__icontains=busca)

    # 3. Aplica o filtro de categoria se existir
    if categoria_filtrada:
        produtos = produtos.filter(categoria=categoria_filtrada)

    # 4. Aplica a ordenação/destaque (Mais Vendidos ou Promoções)
    if ordem == 'mais_vendidos':
        produtos = produtos.filter(mais_vendido=True)
    elif ordem == 'promocoes':
        produtos = produtos.filter(promocao=True)

    # 5. Renderiza a página com a lista final
    return render(request, 'lista_produtos.html', {'produtos': produtos, 'categories_list': categorias_menu})

# View para Login
def login_usuario(request):
    if request.method == 'POST':
        # 1. Salva o carrinho da sessão atual (visitante) antes de logar
        carrinho_temporario = request.session.get('carrinho', {})

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)

            # 2. Restaura o carrinho para a nova sessão do usuário logado
            request.session['carrinho'] = carrinho_temporario
            request.session.modified = True

            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

# View para Cadastro (Criar conta)
def cadastro_usuario(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario) # Loga automaticamente após cadastrar
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'cadastro.html', {'form': form})

# View para Logout (Sair)
def logout_usuario(request):
    # 1. Salva o carrinho antes de encerrar a sessão
    carrinho_antes = request.session.get('carrinho', {})

    logout(request)

    # 2. Devolve o carrinho para a sessão de visitante
    request.session['carrinho'] = carrinho_antes
    request.session.modified = True
    return redirect('home')

def politica_devolucao(request):
    return render(request, 'institucional/devolucao.html')

def politica_entrega(request):
    return render(request, 'institucional/entrega.html')

# loja_gatos/store/views.py

def rastreio_pedido(request):
    pedido = None
    erro = None

    if request.method == 'POST':
        pedido_id = request.POST.get('pedido_id')
        identificador = request.POST.get('identificador')

        if pedido_id and identificador:
            try:
                # 1. Tenta buscar pelo E-mail primeiro
                pedido = Pedido.objects.filter(id=pedido_id, email=identificador).first()

                # 2. Se não achou, tenta buscar pelo CPF
                if not pedido:
                    pedido = Pedido.objects.filter(id=pedido_id, cpf=identificador).first()

                # 3. Se após as duas buscas ainda não existir, define o erro
                if not pedido:
                    erro = "Pedido não encontrado. Verifique se o número e o e-mail/CPF estão corretos."

            except Exception as e:
                print(f"Erro na busca de rastreio: {e}")
                erro = "Ocorreu um erro ao buscar seu pedido. Tente novamente em instantes."
        else:
            erro = "Por favor, preencha todos os campos para localizar seu pedido."

    return render(request, 'institucional/rastreio.html', {
        'pedido': pedido,
        'erro': erro
    })

def calcular_frete_api(cep_destino, itens_carrinho):
    url = "https://sandbox.melhorenvio.com.br/api/v2/me/shipment/calculate" # Use a URL de produção depois
    headers = {
        'Accept': 'application/json',
        'Authorization': f"Bearer {os.getenv('MELHOR_ENVIO_TOKEN')}"
    }
    # Payload com as dimensões dos produtos (você pode usar valores médios por enquanto)
    payload = {
        "from": {"postal_code": "SEU_CEP_ORIGEM"},
        "to": {"postal_code": cep_destino},
        "products": [
            {"id": str(item['id']), "quantity": item['quantidade']}
            for item in itens_carrinho
        ]
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def calcular_frete_view(request):
    dados_carrinho = carrinho_detalhado(request)
    subtotal = dados_carrinho['total_carrinho_lateral']

    # Forçando frete grátis independente do valor
    valor_frete = 0.00
    total_com_frete = float(subtotal) + valor_frete

    return JsonResponse({
        'status': 'sucesso',
        'valor_frete': "0,00",
        'total_com_frete': f"{total_com_frete:.2f}".replace('.', ',')
    })

def politica_privacidade(request):
    return render(request, 'institucional/privacidade.html')

@staff_member_required  # Só você logado como admin consegue ver
def painel_custo_frete(request):
    # Exemplo: simulando custo para o CEP que o cliente digitou no último pedido
    cep_teste = "01001000"
    resultado = consultar_frete_adm(cep_teste)

    return render(request, 'admin/painel_frete.html', {'opcoes': resultado})

@staff_member_required
def painel_frete(request):
    cep = request.GET.get('cep')
    opcoes = None

    if cep:
        # Limpa o CEP para a API
        cep_limpo = cep.replace('-', '').replace(' ', '')
        opcoes = consultar_frete_adm(cep_limpo)

    return render(request, 'admin/painel_frete.html', {'opcoes': opcoes})


def exibir_checkout(request):
    dados_carrinho = carrinho_detalhado(request)
    if not dados_carrinho['carrinho_lateral']:
        return redirect('home')

    return render(request, 'checkout.html', {
        'itens': dados_carrinho['carrinho_lateral'],
        'total_carrinho_lateral': dados_carrinho['total_carrinho_lateral']
    })

# loja_gatos/store/views.py
def finalizar_pedido(request):
    if request.method == 'POST':
        dados_carrinho = carrinho_detalhado(request)

        # 1. SEGURANÇA: Verifica se o carrinho não está vazio antes de processar
        if not dados_carrinho['carrinho_lateral']:
            return redirect('checkout')

        email_cliente = request.POST.get('email')
        total_final = float(dados_carrinho['total_com_frete'])
        metodo_escolhido = request.POST.get('pagamento')

        # Verifica se existe um pedido pendente para este email com o mesmo valor nos últimos 10 minutos
        tempo_limite = timezone.now() - timedelta(minutes=10)
        pedido_duplicado = Pedido.objects.filter(
            email=email_cliente,
            total=round(total_final, 2),
            status='pendente',
            criado_em__gte=tempo_limite
        ).first()

        if pedido_duplicado:
            # Se ele já clicou e o pedido existe, apenas redireciona para o PagBank novamente
            # ou avisa o usuário. Aqui vamos avisar no checkout:
            return render(request, 'checkout.html', {
                'itens': dados_carrinho['carrinho_lateral'],
                'total': dados_carrinho['total_com_frete'],
                'aviso': 'Você já tem um pedido aguardando pagamento. Verifique seu e-mail ou finalize o pagamento anterior.'
            })

        # 2. Lógica de Métodos de Pagamento e Descontos
        metodos_pagbank = []
        if metodo_escolhido == 'pix':
            metodos_pagbank = [{"type": "PIX"}]
            total_final = total_final * 0.95  # Aplica 5% de desconto
        elif metodo_escolhido == 'cartao':
            metodos_pagbank = [{"type": "CREDIT_CARD"}]
        elif metodo_escolhido == 'debito':
            metodos_pagbank = [{"type": "DEBIT_CARD"}]
        else:
            metodos_pagbank = [{"type": "CREDIT_CARD"}, {"type": "PIX"}]

        # 3. Criar o Pedido no Banco de Dados
        pedido = Pedido.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            nome_cliente=request.POST.get('nome'),
            email=request.POST.get('email'),
            telefone=request.POST.get('telefone'),
            pais=request.POST.get('pais', 'Brasil'),
            cep=request.POST.get('cep'),
            endereco=request.POST.get('endereco'),
            bairro=request.POST.get('bairro'),
            cidade=request.POST.get('cidade'),
            estado=request.POST.get('estado'),
            total=round(total_final, 2),
            status='pendente'
        )

        # 4. Tratamento do Telefone

        tel_bruto = request.POST.get('telefone', '')
        tel_limpo = re.sub(r'\D', '', tel_bruto)
        ddd = tel_limpo[:2] if len(tel_limpo) >= 2 else "11"
        numero = tel_limpo[2:] if len(tel_limpo) > 2 else "999999999"

        # 5. Criar os itens do pedido e preparar lista para PagBank
        itens_pagbank = []
        for item in dados_carrinho['carrinho_lateral']:
            p_id = item['id'].split('-')[0]
            produto = Produto.objects.get(id=int(p_id))

            ItemPedido.objects.create(
                pedido=pedido,
                produto=produto,
                quantidade=item['quantidade'],
                preco_unitario=item['preco']
            )

            unit_amount = float(item['preco'])
            if metodo_escolhido == 'pix':
                unit_amount = unit_amount * 0.95

            itens_pagbank.append({
                "reference_id": str(item['id']),
                "name": item['nome'][:60],
                "quantity": item['quantidade'],
                "unit_amount": int(round(unit_amount * 100))
            })

        # 6. Configuração da API e Payload
        url_pagbank = "https://sandbox.api.pagseguro.com/checkouts"
        headers = {
            "Authorization": f"Bearer {os.getenv('PAGBANK_TOKEN')}",
            "Content-Type": "application/json"
        }
        tax_id = request.POST.get('cpf', '').replace('.', '').replace('-', '')

        payload = {
            "reference_id": str(pedido.id),
            "customer": {
                "name": pedido.nome_cliente,
                "email": pedido.email,
                "tax_id": tax_id,
                "phones": [{"area_code": ddd, "number": numero, "type": "MOBILE"}]
            },
            "items": itens_pagbank,
            "payment_methods": metodos_pagbank,
            "notification_urls": ["https://seusite.com/webhook/pagbank/"],
            "redirect_url": "https://www.google.com.br",  # URL de retorno após pagar
        }

        # 7. Chamada à API e Redirecionamento
        try:
            response = requests.post(url_pagbank, json=payload, headers=headers)
            data = response.json()

            if response.status_code == 201:
                # SALVA O ID para a página de sucesso, mas NÃO limpa o carrinho ainda
                request.session['ultimo_pedido_id'] = pedido.id

                # O redirecionamento DEVE estar dentro deste IF
                for link in data['links']:
                    if link['rel'] == 'PAY':
                        return redirect(link['href'])

            # Se não caiu no 201 (sucesso), cai aqui no erro
            print(f"--- ERRO PAGBANK --- Status: {response.status_code} Detalhes: {data}")
            return render(request, 'checkout.html', {
                'itens': dados_carrinho['carrinho_lateral'],
                'total': dados_carrinho['total_com_frete'],
                'erro': 'Erro ao processar pagamento. Verifique seus dados e tente novamente.'
            })

        except Exception as e:
            print(f"Erro de conexão: {e}")

    return redirect('checkout')

def pagina_sucesso(request):
    pedido_id = request.session.get('ultimo_pedido_id')

    if pedido_id:
        # CLIENTE FINALIZOU: Limpamos o carrinho agora
        request.session['carrinho'] = {}
        request.session.modified = True
        pedido = get_object_or_404(Pedido, id=pedido_id)
    else:
        if request.user.is_authenticated:
            pedido = Pedido.objects.filter(usuario=request.user).order_by('-criado_em').first()
        else:
            pedido = None

    return render(request, 'sucesso.html', {'pedido': pedido})

@csrf_exempt  # Necessário porque o PagBank não envia o token CSRF do Django
def webhook_pagbank(request):
    if request.method == 'POST':
        try:
            # O PagBank envia os dados no corpo da requisição (JSON)
            data = json.loads(request.body)

            # Pegamos o ID do pedido que enviamos na 'reference_id'
            referencia = data.get('reference_id')
            status_pagamento = data.get('status')  # Ex: 'PAID'

            if referencia and status_pagamento == 'PAID':
                # Busca o pedido no seu banco
                pedido = Pedido.objects.get(id=int(referencia))

                # Se o pedido ainda não estiver pago, atualizamos
                if pedido.status != 'pago':
                    pedido.status = 'pago'
                    pedido.pago = True
                    pedido.save()  # Isso já dispara o e-mail automático que configuramos no Model!

            return HttpResponse(status=200)  # Avisa o PagBank que recebemos a info
        except Exception as e:
            print(f"Erro no Webhook: {e}")
            return HttpResponse(status=400)

    return HttpResponse(status=200)

@login_required
def excluir_avaliacao(request, avaliacao_id):
    avaliacao = get_object_or_404(Avaliacao, id=avaliacao_id, usuario=request.user)
    produto_id = avaliacao.produto.id
    avaliacao.delete()
    return redirect('produto_detalhe', pk=produto_id)
