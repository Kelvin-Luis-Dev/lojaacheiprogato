from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

class Produto(models.Model):
    # Informações Básicas
    nome = models.CharField(max_length=255)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2)
    preco_fornecedor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estoque = models.PositiveIntegerField(default=0)
    imagem = models.ImageField(upload_to='produtos/', null=True, blank=True)
    link_fornecedor = models.URLField(max_length=500, null=True, blank=True)

    # Status e Filtros (Necessários para suas Views)
    ativo = models.BooleanField(default=True)
    promocao = models.BooleanField(default=False)
    mais_vendido = models.BooleanField(default=False)
    categoria = models.CharField(max_length=100, choices=[
        ('brinquedos', 'Brinquedos'),
        ('alimentacao', 'Alimentação'),
        ('conforto', 'Caminhas e Conforto'),
        ('higiene', 'Higiene'),
    ], default='brinquedos')

    # Descrições (Simples e Detalhada)
    descricao_curta = models.TextField(help_text="Lista de benefícios (Sobre este item)")
    descricao_detalhada = models.TextField(help_text="Descrição completa do produto")

    # Especificações Técnicas (Estilo Amazon)
    marca = models.CharField(max_length=100, default="Genérico")
    material = models.CharField(max_length=100, blank=True)
    dimensoes = models.CharField(max_length=100, blank=True, null=True)
    recomendacao_raca = models.CharField(max_length=100, default="Todas as raças")
    origem = models.CharField(max_length=100, default="Importado")
    garantia = models.CharField(max_length=100, default="3 meses")

    def obter_media_notas(self):
        from django.db.models import Avg
        media = self.avaliacoes.aggregate(Avg('nota'))['nota__avg']
        return round(media, 1) if media else 0

    def total_avaliacoes(self):
        return self.avaliacoes.count()

    @property
    def estoque_total(self):
        # Soma o estoque de todas as variações (se existirem)
        # ou retorna o estoque geral do produto
        if self.variacoes.exists():
            return sum(v.estoque_especifico for v in self.variacoes.all())
        return self.estoque

    def __str__(self):
        return self.nome

# Para aceitar várias fotos
class ProdutoImagem(models.Model):
    produto = models.ForeignKey(Produto, related_name='imagens', on_delete=models.CASCADE)
    imagem = models.ImageField(upload_to='produtos/')

# Para variações (Cores e Tamanhos)
class Variacao(models.Model):
    produto = models.ForeignKey(Produto, related_name='variacoes', on_delete=models.CASCADE)
    nome = models.CharField(max_length=50)  # Ex: "Cor" ou "Tamanho"
    valor = models.CharField(max_length=50)  # Ex: "Verde" ou "G"
    cor_codigo = models.CharField(max_length=20, help_text="Ex: #0000FF para azul", null=True, blank=True)
    imagem = models.ImageField(upload_to='produtos/variacoes/', null=True, blank=True)
    estoque_especifico = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.produto.nome} - {self.nome}: {self.valor}"

# Para Avaliações Reais
class Avaliacao(models.Model):
    STARS = (
        (1, '1'),
        (2, '2'),
        (3, '3'),
        (4, '4'),
        (5, '5'),
    )
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='avaliacoes')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nota = models.IntegerField(choices=STARS, default=5)
    comentario = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.produto.nome} ({self.nota} estrelas)"

class Pedido(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Aguardando Pagamento'),
        ('pago', 'Pago - Preparando Envio'),
        ('em_separacao', 'Em Separação (Compra na Fonte)'),
        ('enviado', 'Enviado / Em Transporte'),
        ('entregue', 'Entregue'),
        ('cancelado', 'Cancelado'),
    ]

    METODO_PAGAMENTO = [
        ('pix', 'PIX'),
        ('cartao', 'Cartão de Crédito'),
    ]

    # Dados do Cliente e Endereço detalhado
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    nome_cliente = models.CharField(max_length=200)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, null=True, blank=True)
    pais = models.CharField(max_length=100, default='Brasil')
    cep = models.CharField(max_length=20, null=True, blank=True)
    frete = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    endereco = models.TextField()
    bairro = models.CharField(max_length=100, null=True, blank=True)
    cidade = models.CharField(max_length=100, null=True, blank=True)
    estado = models.CharField(max_length=100, null=True, blank=True)
    cpf = models.CharField(max_length=14, null=True, blank=True)

    # Controle Financeiro
    total = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pagamento = models.CharField(max_length=20, choices=METODO_PAGAMENTO, default='pix')
    pago = models.BooleanField(default=False)

    # Status e Rastreio
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    criado_em = models.DateTimeField(auto_now_add=True)
    codigo_rastreio = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.pk:
            pedido_antigo = Pedido.objects.get(pk=self.pk)

            # REGRA: Envio de Rastreio
            if not pedido_antigo.codigo_rastreio and self.codigo_rastreio:
                self.status = 'enviado'
                try:
                    self.enviar_email_rastreio()
                except Exception as e:
                    print(f"Erro e-mail rastreio: {e}")

            # REGRA: Confirmação de Pagamento
            elif pedido_antigo.status == 'pendente' and self.status == 'pago':
                self.pago = True
                try:
                    self.enviar_email_confirmacao()
                except Exception as e:
                    print(f"Erro e-mail confirmação: {e}")

        super().save(*args, **kwargs)

    # Função base para enviar o HTML
    def enviar_email_template(self, assunto, mensagem, texto_botao=None, link_botao=None):
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags

        contexto = {
            'nome': self.nome_cliente,
            'mensagem_principal': mensagem,
            'pedido_id': self.id,
            'status_nome': self.get_status_display(),
            'codigo_rastreio': self.codigo_rastreio,
            'texto_botao': texto_botao,
            'link_botao': link_botao,
        }

        html_content = render_to_string('emails/corpo_email.html', contexto)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            assunto,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [self.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    def enviar_email_confirmacao(self):
        self.enviar_email_template(
            assunto=f"Pagamento Aprovado! Pedido #{self.id}",
            mensagem="Seu pagamento foi confirmado com sucesso. Já estamos preparando o envio dos mimos para o seu gatinho!",
            texto_botao="Ver meu Pedido",
            link_botao="http://127.0.0.1:8000/rastreio/"
        )

    def enviar_email_rastreio(self):
        self.enviar_email_template(
            assunto=f"Seu pedido está a caminho! #{self.id}",
            mensagem="Ótimas notícias! Seu pedido foi despachado. Como ele vem de um fornecedor internacional, o rastreio pode levar alguns dias para atualizar no sistema nacional.",
            texto_botao="Acompanhar Entrega",
            # Link do Ebanx Track (identifica quase todas as transportadoras do mundo)
            link_botao=f"https://www.ebanxtrack.com/tracking?code={self.codigo_rastreio}"
        )

    def __str__(self):
        return f'Pedido #{self.id} - {self.nome_cliente} ({self.get_status_display()})'

class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    # Adicionamos o campo de variação abaixo
    variacao = models.ForeignKey(Variacao, on_delete=models.SET_NULL, null=True, blank=True)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        nome = f"{self.produto.nome}"
        if self.variacao:
            nome += f" ({self.variacao.valor})" # Ex: Bolinha (Azul)
        return f'{nome} (x{self.quantidade})'
