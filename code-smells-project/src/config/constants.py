APP_VERSION = "1.0.0"

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"

NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

STATUS_PEDIDO = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]
STATUS_PEDIDO_INICIAL = "pendente"

# (faturamento mínimo, exclusivo; percentual de desconto) — da maior faixa para a menor
FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))
