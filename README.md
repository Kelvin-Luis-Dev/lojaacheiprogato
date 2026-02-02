# 🐱 Achei pro Gato - E-commerce

O **Achei pro Gato** é uma plataforma de e-commerce completa, desenvolvida para o nicho de produtos para felinos. O projeto foca em uma experiência de usuário fluida, desde a navegação em categorias até a finalização do pedido com cálculo de frete em tempo real.

## 🚀 Tecnologias Utilizadas

* **Backend:** Python 3 e Django Framework.
* **Base de Dados:** SQLite (Desenvolvimento) e PostgreSQL (Produção via `dj-database-url`).
* **Integrações de API:**
    * **Melhor Envio:** Cálculo de frete e logística.
    * **Mercado Pago / PagBank:** Processamento de pagamentos seguros.
* **Armazenamento de Media:** Cloudinary (Imagens de produtos hospedadas na nuvem).
* **Frontend:** HTML5, CSS3, JavaScript e Bootstrap.
* **Deploy & Estáticos:** WhiteNoise para servir arquivos estáticos de forma eficiente.

## ⚙️ Funcionalidades Principais

* **Gestão de Produtos:** Suporte para variações de produtos (cores, tamanhos) e controle de estoque.
* **Carrinho Dinâmico:** Processamento de itens via `context_processors` para persistência em todas as páginas.
* **Sistema de Frete:** Integração direta com o Melhor Envio utilizando o CEP de origem `89058240`.
* **Área do Cliente:** Cadastro, login e acompanhamento de pedidos com CPF e código de rastreio.
* **Painel Administrativo:** Customizado para gestão de fretes e pedidos.

## 🛠️ Como Executar o Projeto

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/Kelvin-Luis-Dev/lojaacheiprogato.git](https://github.com/Kelvin-Luis-Dev/lojaacheiprogato.git)
