from django.contrib import admin
from django.utils.html import format_html
from .models import Produto, ProdutoImagem, Variacao, Avaliacao, Pedido, ItemPedido
from django import forms
from django.core.exceptions import ValidationError

# --- INLINES ---

class ProdutoImagemInline(admin.TabularInline):
    model = ProdutoImagem
    extra = 1


class VariacaoInline(admin.TabularInline):
    model = Variacao
    extra = 1
    # Adicionamos 'imagem' para upload e 'mini_imagem' para visualização rápida
    fields = ('nome', 'valor', 'cor_codigo', 'imagem', 'mini_imagem', 'estoque_especifico')
    readonly_fields = ('mini_imagem',)

    def mini_imagem(self, obj):
        if obj.imagem:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: contain; border-radius: 8px; border: 1px solid #ddd;" />',
                obj.imagem.url)
        return "Sem foto"

    mini_imagem.short_description = 'Prévia'

class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ('produto', 'variacao', 'quantidade', 'preco_unitario', 'lucro_estimado_item')

    def lucro_estimado_item(self, obj):
        if obj.produto and obj.produto.preco_fornecedor:
            lucro_unitario = obj.preco_unitario - obj.produto.preco_fornecedor
            lucro_total = lucro_unitario * obj.quantidade
            return f"R$ {lucro_total:.2f}"
        return "N/A"

    lucro_estimado_item.short_description = 'Lucro neste Item'

# --- REGISTROS DO PAINEL ---


# formulário customizado para validar o tamanho do nome
class ProdutoAdminForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = '__all__'

    def clean_nome(self):
        nome = self.cleaned_data.get('nome')
        if len(nome) > 115:
            raise ValidationError(f"Nome muito longo ({len(nome)}). Limite: 115.")
        return nome

    def clean_descricao_curta(self):
        desc = self.cleaned_data.get('descricao_curta')
        if len(desc) > 650:
            raise ValidationError(f"Descrição curta muito longa ({len(desc)}). Limite: 650.")
        return desc

    # NOVO LIMITE PARA DESCRIÇÃO DETALHADA
    def clean_descricao_detalhada(self):
        desc = self.cleaned_data.get('descricao_detalhada')
        if len(desc) > 1200:
            raise ValidationError(f"Descrição detalhada muito longa ({len(desc)}). Limite: 1200.")
        return desc

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    form = ProdutoAdminForm
    # Adicionado categoria, ativo, promocao e mais_vendido na listagem
    list_display = ('nome', 'preco_venda', 'categoria', 'estoque', 'ativo', 'promocao', 'mais_vendido', 'margem_lucro')
    # Filtros laterais para facilitar a gestão
    list_filter = ('categoria', 'ativo', 'promocao', 'mais_vendido')
    search_fields = ('nome', 'marca')
    inlines = [ProdutoImagemInline, VariacaoInline]

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'preco_venda', 'preco_fornecedor', 'estoque', 'imagem', 'link_fornecedor', 'ativo')
        }),
        ('Marketing e Categorização', {
            'fields': ('categoria', 'promocao', 'mais_vendido'),
            'description': 'Marque "Promocao" para aparecer em Ofertas do Dia e "Mais Vendido" para a aba de Mais Vendidos.'
        }),
        ('Descrições', {
            'fields': ('descricao_curta', 'descricao_detalhada')
        }),
        ('Especificações Técnicas (Estilo Amazon)', {
            'fields': ('marca', 'material', 'dimensoes', 'recomendacao_raca', 'origem', 'garantia')
        }),
    )

    class Media:
        js = ('js/contador.js',)  # Caminho para o arquivo que vamos criar

    def margem_lucro(self, obj):
        if obj.preco_fornecedor:
            lucro = obj.preco_venda - obj.preco_fornecedor
            return f"R$ {lucro:.2f}"
        return "Sem custo"

    margem_lucro.short_description = 'Lucro/Unidade'

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome_cliente', 'status', 'total', 'lucro_total_pedido', 'criado_em')
    list_filter = ('status', 'criado_em')
    inlines = [ItemPedidoInline]

    def lucro_total_pedido(self, obj):
        lucro_total = 0
        for item in obj.itens.all():
            if item.produto and item.produto.preco_fornecedor:
                lucro_unitario = item.preco_unitario - item.produto.preco_fornecedor
                lucro_total += (lucro_unitario * item.quantidade)

        return format_html(
            '<span style="color: green; font-weight: bold;">R$ {}</span>',
            f"{lucro_total:.2f}"
        )

    lucro_total_pedido.short_description = 'Lucro Total'

@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'usuario', 'nota', 'data_criacao')
    list_filter = ('nota', 'data_criacao')