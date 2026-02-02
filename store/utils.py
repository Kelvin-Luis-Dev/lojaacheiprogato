import requests
import os


def consultar_frete_adm(cep_destino, peso=0.5):
    # Pega o Token e o CEP de origem do seu cofre (.env)
    token = os.getenv('MELHOR_ENVIO_TOKEN')
    cep_origem = os.getenv('CEP_ORIGEM')

    url = "https://sandbox.melhorenvio.com.br/api/v2/me/shipment/calculate"

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    # Dados básicos para uma simulação rápida
    payload = {
        "from": {"postal_code": cep_origem},
        "to": {"postal_code": cep_destino},
        "package": {
            "height": 10,
            "width": 15,
            "length": 20,
            "weight": peso
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()  # Retorna a lista de preços reais no Brasil
        return None
    except:
        return None