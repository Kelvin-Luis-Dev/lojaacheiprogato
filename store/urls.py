from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('produto/<int:pk>/', views.produto_detalhe, name='produto_detalhe'),
    path('produtos/', views.lista_produtos, name='lista_produtos'),
    path('carrinho/', views.ver_carrinho, name='carrinho'),
    path('login/', views.login_usuario, name='login_usuario'),
    path('cadastro/', views.cadastro_usuario, name='cadastro_usuario'),

    # Alterado para str para suportar chaves de variantes (ex: '11-2')
    path('carrinho/add/<str:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/remover/<str:produto_id>/', views.remover_do_carrinho, name='remover_do_carrinho'),
    path('carrinho/alterar/<str:produto_id>/<str:acao>/', views.alterar_quantidade, name='alterar_quantidade'),

    path('checkout/', views.checkout, name='checkout'),
    path('finalizar-pedido/', views.finalizar_pedido, name='finalizar_pedido'),
    path('carrinho/calcular-frete/', views.calcular_frete_view, name='calcular_frete'),
    path('sucesso/', views.pagina_sucesso, name='pagina_sucesso'),
    path('politica-devolucao/', views.politica_devolucao, name='politica_devolucao'),
    path('politica-entrega/', views.politica_entrega, name='politica_entrega'),
    path('politica-privacidade/', views.politica_privacidade, name='politica_privacidade'),
    path('rastreio/', views.rastreio_pedido, name='rastreio_pedido'),
    path('admin-painel/frete/', views.painel_frete, name='painel_frete'),
    path('webhook/pagbank/', views.webhook_pagbank, name='webhook_pagbank'),
    path('excluir-avaliacao/<int:avaliacao_id>/', views.excluir_avaliacao, name='excluir_avaliacao'),
]